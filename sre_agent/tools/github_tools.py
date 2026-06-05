"""GitHub PR creation tools — The 'Dev Hand' of the SRE Agent.

Provides tools for autonomously creating Pull Requests with code fixes
identified by the Gemini model from Dynatrace trace analysis.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from github import Auth, Github, GithubException

from sre_agent.config import get_settings

logger = logging.getLogger(__name__)


def read_github_file(file_path: str) -> str:
    """Read the contents of a file from the configured GitHub repository.
    
    Use this tool to read the source code of a file before attempting to write a fix for it.
    This ensures you have the exact, current code to base your modifications on.
    
    Args:
        file_path: The path to the file in the repository (e.g., 'app.py' or 'src/main.py').
        
    Returns:
        The text content of the file, or an error message if it cannot be found.
    """
    settings = get_settings()
    if not settings.github_token:
        return "Error: GITHUB_TOKEN environment variable is not set."
    
    if not settings.github_repo:
        return "Error: GITHUB_REPO environment variable is not set."

    try:
        auth = Auth.Token(settings.github_token)
        g = Github(auth=auth)
        repo = g.get_repo(settings.github_repo)
        
        logger.info(f"📖 Reading file {file_path} from {settings.github_repo}")
        file_content = repo.get_contents(file_path)
        
        if isinstance(file_content, list):
            return f"Error: {file_path} is a directory, not a file."
            
        return file_content.decoded_content.decode("utf-8")
        
    except GithubException as e:
        logger.error(f"❌ GitHub API error: {e.status} - {e.data}")
        return f"Error accessing GitHub API: {e.status} - {e.data.get('message', 'Unknown error')}"
    except Exception as e:
        logger.error(f"❌ Failed to read file from GitHub: {str(e)}")
        return f"Error reading file: {str(e)}"

def _fuzzy_find_and_replace(content: str, original_code: str, fixed_code: str) -> tuple[str, bool]:
    """Find and replace code using fuzzy matching.
    
    Strategy:
    1. Try exact match first (fastest)
    2. Try normalized whitespace match (handles indentation differences)
    3. Try line-by-line fuzzy matching with difflib (handles minor LLM hallucinations)
    
    Returns (new_content, success).
    """
    import difflib

    # --- Strategy 1: Exact match ---
    if original_code in content:
        return content.replace(original_code, fixed_code, 1), True

    # --- Strategy 2: Normalized whitespace match ---
    # Collapse all whitespace runs to single spaces for comparison
    def normalize(s):
        return " ".join(s.split())

    norm_original = normalize(original_code)
    
    # Slide a window across the content lines to find the best match
    content_lines = content.splitlines(keepends=True)
    original_lines = original_code.splitlines()
    window_size = len(original_lines)

    if window_size == 0:
        return content, False

    best_ratio = 0.0
    best_start = -1

    for i in range(len(content_lines) - window_size + 1):
        candidate_lines = content_lines[i : i + window_size]
        candidate_text = "".join(candidate_lines)

        # Quick normalized check
        if normalize(candidate_text) == norm_original:
            new_content = (
                "".join(content_lines[:i])
                + fixed_code + "\n"
                + "".join(content_lines[i + window_size :])
            )
            return new_content, True

        # --- Strategy 3: Fuzzy ratio ---
        ratio = difflib.SequenceMatcher(
            None, normalize(candidate_text), norm_original
        ).ratio()

        if ratio > best_ratio:
            best_ratio = ratio
            best_start = i

    # Accept fuzzy match if similarity is >= 80%
    if best_ratio >= 0.80 and best_start >= 0:
        logger.info(
            f"🔍 Fuzzy match found at line {best_start + 1} "
            f"(similarity: {best_ratio:.0%})"
        )
        new_content = (
            "".join(content_lines[:best_start])
            + fixed_code + "\n"
            + "".join(content_lines[best_start + window_size :])
        )
        return new_content, True

    return content, False


def create_fix_pull_request(
    file_path: str,
    original_code: str,
    fixed_code: str,
    fix_description: str,
    trace_summary: str,
    problem_id: str = "unknown",
) -> dict:
    """Create a GitHub Pull Request with an automated code fix.

    Use this tool after analyzing a Dynatrace distributed trace and identifying
    problematic code (e.g., unoptimized SQL queries, memory leaks, missing indexes).
    The tool creates a new branch, applies the fix, and opens a PR with full context.

    The tool fetches the actual file content from GitHub before applying the fix,
    and uses fuzzy matching to locate the correct code block even if the provided
    original_code snippet is not a character-perfect match.

    Args:
        file_path: Path to the file in the repository to patch (e.g., 'src/db/queries.py').
        original_code: The original problematic code snippet that was identified in the trace.
        fixed_code: The optimized or fixed code to replace the original.
        fix_description: A human-readable description of what was fixed and why.
        trace_summary: A markdown-formatted summary of the Dynatrace trace analysis
                       that led to this fix.
        problem_id: The Dynatrace Problem ID (e.g., 'P-12345') for traceability.

    Returns:
        A dictionary containing:
        - success (bool): Whether the PR was created successfully
        - pr_url (str): URL of the created Pull Request
        - pr_number (int): PR number
        - branch_name (str): Name of the created branch
        - message (str): Human-readable status message
    """
    settings = get_settings()

    if not settings.github_token:
        return {
            "success": False,
            "message": "GITHUB_TOKEN is not configured. Cannot create PR.",
        }

    if not settings.github_repo:
        return {
            "success": False,
            "message": "GITHUB_REPO is not configured. Cannot create PR.",
        }

    try:
        # Authenticate with GitHub
        auth = Auth.Token(settings.github_token)
        g = Github(auth=auth)
        repo = g.get_repo(settings.github_repo)

        # Generate branch name with timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        branch_name = f"fix/auto-sre-{problem_id.lower()}-{timestamp}"

        # Get the SHA of the default branch
        default_branch_name = repo.default_branch
        base_branch = repo.get_branch(default_branch_name)
        base_sha = base_branch.commit.sha

        # Create the new branch
        repo.create_git_ref(
            ref=f"refs/heads/{branch_name}",
            sha=base_sha,
        )
        logger.info(f"🌿 Created branch: {branch_name}")

        # Get the target file from GitHub (the real source of truth)
        try:
            file_contents = repo.get_contents(file_path, ref=default_branch_name)
            current_content = file_contents.decoded_content.decode("utf-8")
            logger.info(f"📄 Fetched {file_path} from GitHub ({len(current_content)} bytes)")

            # Apply the fix using fuzzy matching
            new_content, match_found = _fuzzy_find_and_replace(
                current_content, original_code, fixed_code
            )

            if match_found:
                logger.info(f"✅ Code block matched and replaced in {file_path}")
            else:
                logger.warning(
                    f"⚠️ Could not match original code in {file_path}. "
                    f"Replacing entire file content with fix."
                )
                new_content = fixed_code

            # Commit the change
            repo.update_file(
                path=file_path,
                message=f"fix: Auto-SRE patch for {problem_id}\n\n{fix_description}",
                content=new_content,
                sha=file_contents.sha,
                branch=branch_name,
            )
        except GithubException as e:
            if e.status == 404:
                # File doesn't exist, create it
                repo.create_file(
                    path=file_path,
                    message=f"fix: Auto-SRE patch for {problem_id}\n\n{fix_description}",
                    content=fixed_code,
                    branch=branch_name,
                )
            else:
                raise

        logger.info(f"📝 Committed fix to {file_path} on {branch_name}")

        # Create the Pull Request with rich description
        pr_body = _build_pr_description(
            problem_id=problem_id,
            fix_description=fix_description,
            trace_summary=trace_summary,
            file_path=file_path,
            original_code=original_code,
            fixed_code=fixed_code,
        )

        pr = repo.create_pull(
            title=f"🤖 Auto-SRE Fix: {fix_description[:80]}",
            body=pr_body,
            head=branch_name,
            base=default_branch_name,
        )

        message = f"PR #{pr.number} created: {pr.html_url}"
        logger.info(f"🐙 {message}")

        g.close()

        return {
            "success": True,
            "pr_url": pr.html_url,
            "pr_number": pr.number,
            "branch_name": branch_name,
            "message": message,
        }

    except GithubException as e:
        error_msg = f"GitHub API error: {e.status} - {e.data}"
        logger.error(f"❌ {error_msg}")
        return {
            "success": False,
            "message": error_msg,
        }
    except Exception as e:
        error_msg = f"Failed to create PR: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return {
            "success": False,
            "message": error_msg,
        }


def _build_pr_description(
    problem_id: str,
    fix_description: str,
    trace_summary: str,
    file_path: str,
    original_code: str,
    fixed_code: str,
) -> str:
    """Build a rich markdown PR description."""
    return f"""## 🤖 Autonomous SRE Agent — Automated Fix

**Dynatrace Problem ID:** `{problem_id}`  
**Generated at:** {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}

---

### 📊 Trace Analysis Summary

{trace_summary}

---

### 🔧 Fix Description

{fix_description}

---

### 📝 Code Changes

**File:** `{file_path}`

<details>
<summary>Original Code (problematic)</summary>

```
{original_code}
```

</details>

<details>
<summary>Fixed Code (optimized)</summary>

```
{fixed_code}
```

</details>

---

### ⚠️ Review Notes

- This PR was **automatically generated** by the Autonomous SRE Agent
- The fix was derived from Dynatrace distributed trace analysis
- Please review the code changes carefully before merging
- The agent has also executed infrastructure mitigation (if applicable)

---

*Powered by Google ADK + Gemini + Dynatrace MCP*
"""
