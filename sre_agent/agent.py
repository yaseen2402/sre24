"""Core ADK Agent for the Autonomous SRE Agent.

Defines the main Gemini-powered agent that orchestrates incident response:
1. Connects to Dynatrace MCP Server for trace analysis
2. Uses GCP tools for infrastructure mitigation (Ops Hand)
3. Uses GitHub tools for code patching (Dev Hand)
4. Sends notifications about actions taken
"""

import asyncio
import logging
import os
from typing import Any, Optional

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from sre_agent.config import get_settings
from sre_agent.tools.gcp_tools import scale_cloud_run_service
from sre_agent.tools.github_tools import create_fix_pull_request, read_github_file
from sre_agent.tools.notification_tools import send_notification

logger = logging.getLogger(__name__)

# Agent instruction prompt — guides Gemini through the SRE workflow
AGENT_INSTRUCTION = """
You are an Autonomous SRE (Site Reliability Engineering) Agent. Your mission is to
automatically respond to production incidents detected by Dynatrace.

When you receive a Dynatrace Problem ID and context, follow this exact workflow:

## Step 1: Investigate the Problem (Perceive & Reason)
- Use the Dynatrace MCP tools to understand the problem:
  - Call `list_problems` to get details about active problems
  - Call `execute_dql` with DQL queries to fetch distributed traces
  - Example DQL: `fetch spans | filter dt.entity.service == "<entity_id>" | sort timestamp desc | limit 50`
  - Or use `generate_dql_from_natural_language` to build queries
- Identify the root cause: Is it resource exhaustion? A code issue? Both?
- IMPORTANT: If DQL queries return 0 records or authorization errors, proceed with
  the problem context already provided in the alert. Do NOT loop endlessly on queries.

## Step 2: Ops Hand — Immediate Infrastructure Mitigation
- If the trace shows resource exhaustion (CPU > 90%, memory pressure, traffic overload):
  - Use `scale_cloud_run_service` to increase the max instance count
  - Choose an appropriate max_instances value based on the severity
  - Document what you scaled and why

## Step 3: Dev Hand — Root Cause Code Fix
- If the problem involves a code-level issue (e.g., slow SQL queries, memory leaks, algorithmic inefficiencies):
  1. Use the `read_github_file` tool to fetch the relevant source code files from the repository.
     - Try to identify the likely file path based on the Dynatrace alert context (e.g., endpoint names, service names).
  2. Analyze the code you just read to locate the exact problematic lines causing the issue.
  3. Write an optimized version of the code that fixes the problem.
  4. Use `create_fix_pull_request` to create a PR with:
     - The exact original code from the file you read
     - Your fixed code
     - A clear description of the fix
     - A summary of the trace analysis

## Step 4: Notify
- After completing all actions, use `send_notification` to report:
  - What problem was detected
  - What infrastructure actions were taken (if any)
  - Whether a code fix PR was created (if any)
  - The PR URL for the team to review

## Important Guidelines:
- Be thorough but fast — the entire flow should complete in under 60 seconds
- Always explain your reasoning for each action
- If you cannot determine a code fix, still perform infrastructure mitigation
- If Dynatrace MCP tools are unavailable, work with the problem context provided
- Never make destructive changes — only scale UP, not down
- Do NOT loop more than 2 times on DQL queries if they return empty results
"""


def _create_dynatrace_mcp_toolset():
    """Create the Dynatrace MCP toolset for connecting to Dynatrace.
    
    Uses stdio transport via npx to launch the Dynatrace MCP server.
    Returns None if MCP dependencies are not available.
    """
    settings = get_settings()
    
    try:
        from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
        from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
        from mcp import StdioServerParameters
        
        mcp_toolset = MCPToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="cmd",
                    args=["/c", "npx", "-y", "@dynatrace-oss/dynatrace-mcp-server@latest"],
                    env={
                        **os.environ,
                        "DT_ENVIRONMENT": settings.dt_environment,
                        "DT_PLATFORM_TOKEN": settings.dt_platform_token,
                        "DT_MCP_DISABLE_TELEMETRY": "true",
                    },
                ),
                timeout=60,
            )
        )
        logger.info("📊 Dynatrace MCP toolset initialized")
        return mcp_toolset
    except ImportError as e:
        logger.warning(f"MCP dependencies not available: {e}. Agent will work without Dynatrace MCP tools.")
        return None
    except Exception as e:
        logger.warning(f"Failed to initialize Dynatrace MCP: {e}. Agent will work without Dynatrace MCP tools.")
        return None


def create_sre_agent() -> Agent:
    """Create and configure the Autonomous SRE Agent."""
    settings = get_settings()
    
    # Build the tools list
    tools = [
        scale_cloud_run_service,
        read_github_file,
        create_fix_pull_request,
        send_notification,
    ]
    
    # Try to add Dynatrace MCP tools
    mcp_toolset = _create_dynatrace_mcp_toolset()
    if mcp_toolset:
        tools.append(mcp_toolset)
    
    agent = Agent(
        model=settings.gemini_model,
        name="autonomous_sre_agent",
        description=(
            "An autonomous SRE agent that responds to Dynatrace anomaly alerts "
            "by analyzing distributed traces, mitigating infrastructure issues, "
            "and drafting code fixes."
        ),
        instruction=AGENT_INSTRUCTION,
        tools=tools,
    )
    
    logger.info(f"🧠 SRE Agent created with model: {settings.gemini_model}")
    return agent


# Global agent instance and session service
_agent: Optional[Agent] = None
_session_service: Optional[InMemorySessionService] = None
_runner: Optional[Runner] = None


def _get_runner() -> Runner:
    """Get or create the global Runner instance."""
    global _agent, _session_service, _runner
    
    if _runner is None:
        _agent = create_sre_agent()
        _session_service = InMemorySessionService()
        _runner = Runner(
            agent=_agent,
            session_service=_session_service,
            app_name="autonomous_sre_agent",
        )
        logger.info("🏃 Agent Runner initialized")
    
    return _runner


async def run_agent_for_problem(payload) -> dict:
    """Run the SRE agent for a specific Dynatrace problem.
    
    Args:
        payload: DynatraceWebhookPayload instance with problem details.
        
    Returns:
        Dictionary with the agent's response and actions taken.
    """
    runner = _get_runner()
    
    # Create a new session for this problem
    session = await _session_service.create_session(
        state={"problem_id": payload.PID},
        app_name="autonomous_sre_agent",
        user_id="dynatrace_webhook",
    )
    
    # Build the problem context message for the agent
    impacted_entities_text = "\n".join(
        f"  - {e.name} (type: {e.type}, id: {e.entity})"
        for e in payload.ImpactedEntities
    ) or "  - No specific entities listed"
    
    root_cause_text = (
        f"  Entity: {payload.RootCauseEntity.name} "
        f"(type: {payload.RootCauseEntity.type}, id: {payload.RootCauseEntity.entity})"
        if payload.RootCauseEntity
        else "  Not yet determined by Davis AI"
    )
    
    user_message = f"""A Dynatrace anomaly alert has been triggered. Investigate and respond:

**Problem ID:** {payload.PID}
**Title:** {payload.ProblemTitle}
**Severity:** {payload.ProblemSeverity or 'Unknown'}
**State:** {payload.State.value}
**Problem URL:** {payload.ProblemURL}

**Impacted Entities:**
{impacted_entities_text}

**Root Cause:**
{root_cause_text}

**Problem Details:**
{payload.ProblemDetailsText or 'No additional details available.'}

Please execute the full SRE response workflow:
1. Investigate the distributed trace via Dynatrace MCP tools
2. Apply infrastructure mitigation if needed (Ops Hand)
3. Draft a code fix PR if a code-level root cause is found (Dev Hand)
4. Send a notification summarizing all actions taken
"""
    
    logger.info(f"🧠 Sending problem {payload.PID} to agent for analysis...")
    
    # Run the agent synchronously to bypass the aiohttp ClientConnectorDNSError bug on Windows
    final_response = ""
    try:
        for event in runner.run(
            session_id=session.id,
            user_id="dynatrace_webhook",
            new_message=types.Content(
                role="user",
                parts=[types.Part(text=user_message)],
            ),
        ):
            if event.is_final_response():
                for part in event.content.parts:
                    if part.text:
                        final_response += part.text
    except Exception as e:
        logger.error(f"Agent execution error: {e}")
        final_response = f"Agent encountered an error: {str(e)}"
    
    logger.info(f"🧠 Agent completed processing for {payload.PID}")
    
    return {
        "problem_id": payload.PID,
        "agent_response": final_response,
        "session_id": session.id,
    }


# Export the root agent for ADK CLI compatibility (adk web, adk api_server)
root_agent = create_sre_agent()
