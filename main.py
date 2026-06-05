"""Entry point for the Autonomous SRE Agent.

Starts the FastAPI/Uvicorn webhook server that listens for
Dynatrace Problem Notifications and triggers the ADK agent.
"""

import logging
import os
import sys

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from sre_agent.config import get_settings
from sre_agent.webhook.server import app


def setup_logging() -> None:
    """Configure structured logging."""
    settings = get_settings()
    
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def main() -> None:
    """Start the webhook server."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    settings = get_settings()
    
    # Initialize database tables
    from sre_agent.db.session import init_db
    init_db()
    
    # Log startup info
    logger.info("🤖 Autonomous SRE Agent v1.0.0")
    logger.info(f"   Model: {settings.gemini_model}")
    logger.info(f"   Dynatrace: {settings.dt_environment}")
    logger.info(f"   GitHub: {settings.github_repo}")
    logger.info(f"   GCP Project: {settings.gcp_project_id or 'Not configured'}")
    logger.info(f"   Port: {settings.port}")
    
    # Log warnings for missing configuration
    warnings = settings.validate_required_for_production()
    for warning in warnings:
        logger.warning(f"⚠️  {warning}")
    
    # Start the server
    import uvicorn
    uvicorn.run(
        "sre_agent.webhook.server:app",
        host="0.0.0.0",
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=False,
    )


if __name__ == "__main__":
    main()
