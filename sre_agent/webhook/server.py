"""FastAPI webhook server for receiving Dynatrace Problem Notifications.

This server exposes a /webhook endpoint that receives Dynatrace alerts
and triggers the ADK agent for autonomous incident response.
"""

import asyncio
import logging
import os
import time
import traceback
import uuid
import dotenv
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from sre_agent.config import get_settings
from sre_agent.webhook.models import (
    DynatraceWebhookPayload,
    ProblemStateEnum,
    WebhookResponse,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    settings = get_settings()
    
    # Log startup warnings for missing config
    warnings = settings.validate_required_for_production()
    for warning in warnings:
        logger.warning(f"⚠️  {warning}")
    
    logger.info("🚀 Autonomous SRE Agent webhook server starting...")
    logger.info(f"   Gemini Model: {settings.gemini_model}")
    logger.info(f"   Dynatrace: {settings.dt_environment}")
    logger.info(f"   GitHub Repo: {settings.github_repo}")
    logger.info(f"   GCP Project: {settings.gcp_project_id}")
    
    yield
    
    logger.info("🛑 Autonomous SRE Agent webhook server shutting down...")


app = FastAPI(
    title="Autonomous SRE Agent",
    description="Event-driven AI agent for autonomous incident response. "
                "Intercepts Dynatrace anomaly alerts, mitigates infrastructure issues, "
                "and drafts code fixes.",
    version="1.0.0",
    lifespan=lifespan,
)

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for hackathon development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from sre_agent.api.routes import router as tenant_router
app.include_router(tenant_router)

# ---------------------------------------------------------------------------
# In-memory incident store for the dashboard
# ---------------------------------------------------------------------------
_incidents: list[dict] = []
_activity_log: list[dict] = []


def _add_incident(problem_id: str, title: str, severity: str, details: str = "") -> dict:
    """Add a new incident to the store."""
    incident = {
        "id": str(uuid.uuid4()),
        "problem_id": problem_id,
        "title": title,
        "severity": severity,
        "status": "processing",
        "details": details,
        "actions": [],
        "timestamp": time.time(),
    }
    _incidents.insert(0, incident)  # Newest first
    return incident


def _add_activity(message: str) -> None:
    """Add an activity log entry."""
    entry = {
        "timestamp": time.time(),
        "message": message,
    }
    _activity_log.append(entry)
    # Keep only last 100 entries
    if len(_activity_log) > 100:
        _activity_log.pop(0)


def _update_incident(problem_id: str, status: str = None, action: str = None) -> None:
    """Update an existing incident."""
    for incident in _incidents:
        if incident["problem_id"] == problem_id:
            if status:
                incident["status"] = status
            if action:
                incident["actions"].append(action)
            break


async def _process_problem(payload: DynatraceWebhookPayload, tenant_id: str = None) -> None:
    """Process a Dynatrace problem notification through the ADK agent.
    
    This runs as a background task so the webhook returns quickly.
    """
    from sre_agent.agent import run_agent_for_problem
    from sre_agent.db.session import SessionLocal
    from sre_agent.db.models import TenantConfig, IncidentLog
    from sre_agent.config import tenant_context
    
    db = SessionLocal()
    incident_id = None
    
    try:
        # Create an IncidentLog in the DB
        if tenant_id:
            incident = IncidentLog(
                tenant_id=tenant_id,
                dynatrace_problem_id=payload.PID,
                status="PROCESSING"
            )
            db.add(incident)
            db.commit()
            incident_id = incident.id
            logger.info(f"💾 Logged incident {payload.PID} to database for tenant {tenant_id}")
            
        # Fetch tenant configuration from DB if provided
        overrides = {}
        if tenant_id:
            tenant = db.query(TenantConfig).filter(TenantConfig.id == tenant_id).first()
            if tenant:
                overrides = {
                    "dt_environment": tenant.dt_environment or "",
                    "dt_platform_token": tenant.dt_platform_token or "",
                    "github_token": tenant.github_token or "",
                    "github_repo": tenant.github_repo or "",
                    "gcp_project_id": tenant.gcp_project or "",
                    "gcp_region": tenant.gcp_region or "",
                }
                # Remove empty strings to fallback to .env if needed
                overrides = {k: v for k, v in overrides.items() if v}
                logger.info(f"🏢 Using custom configuration for tenant: {tenant.name}")
            else:
                logger.warning(f"⚠️ Tenant {tenant_id} not found in database. Using default environment variables.")

        # Set the thread-local context for this background task
        token = tenant_context.set(overrides)
        
        logger.info(f"🔍 Processing problem {payload.PID}: {payload.ProblemTitle}")
        result = await run_agent_for_problem(payload)
        logger.info(f"✅ Problem {payload.PID} processed successfully: {result}")
        
        # Update incident status to RESOLVED
        if incident_id:
            import re
            incident = db.query(IncidentLog).filter(IncidentLog.id == incident_id).first()
            if incident:
                incident.status = "RESOLVED"
                
                # Extract PR URL from agent output if it exists
                pr_matches = re.findall(r"https://github\.com/[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+/pull/\d+", str(result))
                if pr_matches:
                    incident.pr_url = pr_matches[0]
                
                # Generate a concise summary of the action using Gemini
                try:
                    from google import genai
                    from sre_agent.config import get_settings
                    client = genai.Client(api_key=get_settings().google_api_key)
                    summary_res = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=f"Summarize this AI agent's resolution logs in 1 concise, professional sentence explaining exactly what the agent found and how it fixed the incident. Do not use markdown. Keep it very short. Logs: {result}"
                    )
                    incident.agent_logs = summary_res.text.strip()
                except Exception as e:
                    logger.error(f"Failed to generate summary: {e}")
                    incident.agent_logs = str(result)
                    
                db.commit()
        
    except Exception as e:
        logger.error(f"❌ Error processing problem {payload.PID}: {e}")
        logger.error(traceback.format_exc())
        # Update incident status to FAILED
        if incident_id:
            incident = db.query(IncidentLog).filter(IncidentLog.id == incident_id).first()
            if incident:
                incident.status = "FAILED"
                incident.agent_logs = str(e)
                db.commit()
    finally:
        # Clean up context
        if 'token' in locals():
            tenant_context.reset(token)
        db.close()


@app.post("/webhook", response_model=WebhookResponse)
@app.post("/webhook/{tenant_id}", response_model=WebhookResponse)
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    tenant_id: str = None,
) -> WebhookResponse:
    """Receive a Dynatrace Problem Notification webhook.
    
    This endpoint:
    1. Validates the incoming payload
    2. Extracts the ProblemID and impacted entities
    3. Triggers the ADK agent as a background task
    4. Returns immediately with an acknowledgment
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    try:
        payload = DynatraceWebhookPayload.model_validate(body)
    except Exception as e:
        logger.error(f"Payload validation failed: {e}")
        raise HTTPException(
            status_code=422,
            detail=f"Invalid Dynatrace payload: {str(e)}"
        )
    
    # Only process OPEN problems (ignore RESOLVED/MERGED)
    if payload.State != ProblemStateEnum.OPEN:
        logger.info(f"Ignoring problem {payload.PID} with state: {payload.State}")
        return WebhookResponse(
            status="ignored",
            problem_id=payload.PID,
            message=f"Problem state is {payload.State.value}, no action needed",
        )
    
    # Log the incoming problem
    impacted_names = [e.name for e in payload.ImpactedEntities]
    logger.info(
        f"🚨 Received problem alert: {payload.PID} - {payload.ProblemTitle} | "
        f"Impacted: {', '.join(impacted_names) or 'N/A'} | "
        f"Severity: {payload.ProblemSeverity} | Tenant: {tenant_id or 'default'}"
    )
    
    # Process the problem in the background
    background_tasks.add_task(_process_problem, payload, tenant_id)
    
    return WebhookResponse(
        status="processing",
        problem_id=payload.PID,
        message=f"Problem {payload.PID} received and agent triggered",
    )


@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run."""
    settings = get_settings()
    warnings = settings.validate_required_for_production()
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": settings.gemini_model,
        "config_warnings": warnings,
    }


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Serve the SRE Agent dashboard."""
    dashboard_path = Path(__file__).parent.parent / "dashboard" / "index.html"
    if dashboard_path.exists():
        return HTMLResponse(content=dashboard_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Dashboard not found</h1>", status_code=404)


@app.get("/api/incidents")
async def get_incidents():
    """Get all incidents for the dashboard."""
    return {
        "incidents": _incidents,
        "stats": {
            "problems_detected": len(_incidents),
            "threats_blocked": sum(
                1 for i in _incidents
                if any("block" in a.lower() for a in i["actions"])
            ),
            "services_scaled": sum(
                1 for i in _incidents
                if any("scale" in a.lower() for a in i["actions"])
            ),
            "prs_created": sum(
                1 for i in _incidents
                if any("pr" in a.lower() for a in i["actions"])
            ),
        },
        "activity_log": _activity_log[-50:],  # Last 50 entries
    }


# --- Config API ---

class ConfigUpdateModel(BaseModel):
    dt_environment: str | None = None
    dt_platform_token: str | None = None
    github_token: str | None = None
    github_repo: str | None = None
    gcp_project_id: str | None = None
    gcp_region: str | None = None

@app.get("/api/config")
async def get_config():
    """Get the current configuration settings."""
    settings = get_settings()
    return {
        "dt_environment": settings.dt_environment,
        "dt_platform_token_set": bool(settings.dt_platform_token),
        "github_repo": settings.github_repo,
        "github_token_set": bool(settings.github_token),
        "gcp_project_id": settings.gcp_project_id,
        "gcp_region": settings.gcp_region
    }

@app.post("/api/config")
async def update_config(config: ConfigUpdateModel):
    """Update configuration and write to .env file."""
    env_file = ".env"
    
    # Load existing env vars to preserve ones we aren't changing
    existing_vars = {}
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.strip().split("=", 1)
                    existing_vars[k.strip()] = v.strip()
    
    # Update with new values
    updates = config.model_dump(exclude_unset=True)
    for key, value in updates.items():
        if value is not None and value != "":
            existing_vars[key.upper()] = value
            os.environ[key.upper()] = value # Also update current process
            
    # Write back to .env
    with open(env_file, "w", encoding="utf-8") as f:
        for k, v in existing_vars.items():
            f.write(f"{k}={v}\n")
            
    # Clear settings cache so they reload
    get_settings.cache_clear()
    
    return {"status": "success", "message": "Configuration updated successfully."}


# --- Simulation API (For Hackathon Demo) ---
@app.post("/api/simulate")
async def simulate_attack(background_tasks: BackgroundTasks):
    """Simulate a database performance bottleneck by triggering the REAL agent workflow."""
    import time
    
    payload = DynatraceWebhookPayload(
        State=ProblemStateEnum.OPEN,
        ProblemID=str(int(time.time())),
        PID=f"P-SIM-{int(time.time())}",
        ProblemTitle="Response Time Degradation - Database Bottleneck",
        ProblemSeverity="PERFORMANCE",
        ProblemURL="https://dynatrace.com",
        ProblemDetailsText="Massive response time degradation detected on /api/reports/user-orders. Database execution time has increased to 98% of total response time. Trace analysis reveals 1,000+ sequential SQL queries (N+1 query pattern).",
        ImpactedEntities=[]
    )
    
    # Trigger the real agent webhook handler in the background
    background_tasks.add_task(_process_problem, payload)
    
    return {"status": "success", "message": "Real agent simulation triggered"}


@app.get("/")
async def root():
    """Redirect to dashboard."""
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/dashboard")
