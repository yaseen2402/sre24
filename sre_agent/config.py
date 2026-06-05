"""Centralized configuration for the Autonomous SRE Agent.

Loads environment variables from .env file and validates required settings.
"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Google Gemini
    google_api_key: str = Field(
        default="",
        description="Google API key for Gemini models"
    )
    gemini_model: str = Field(
        default="gemini-2.5-flash",
        description="Gemini model to use for the agent"
    )

    # Dynatrace
    dt_environment: str = Field(
        default="https://placeholder.apps.dynatrace.com",
        description="Dynatrace environment URL"
    )
    dt_platform_token: str = Field(
        default="",
        description="Dynatrace Platform Token"
    )
    dt_event_token: str = Field(
        default="",
        description="Dynatrace token for Events API"
    )

    # GitHub
    github_token: str = Field(
        default="",
        description="GitHub Personal Access Token"
    )
    github_repo: str = Field(
        default="owner/repo-name",
        description="Target GitHub repository (owner/repo)"
    )

    # Google Cloud
    gcp_project_id: str = Field(
        default="",
        description="Google Cloud project ID"
    )
    gcp_region: str = Field(
        default="us-central1",
        description="Google Cloud region"
    )

    # Notifications
    slack_webhook_url: str = Field(
        default="",
        description="Slack webhook URL for notifications"
    )

    # Server
    port: int = Field(
        default=8080,
        description="Server port"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }

    @classmethod
    def settings_customise_sources(cls, settings_cls, **kwargs):
        """Make .env file take priority over OS environment variables."""
        return (
            kwargs.get("init_settings"),
            kwargs.get("dotenv_settings"),   # .env first
            kwargs.get("env_settings"),       # OS env second
            kwargs.get("file_secret_settings"),
        )

    def validate_required_for_production(self) -> list[str]:
        """Check which required settings are missing for production use."""
        warnings = []
        if not self.google_api_key:
            warnings.append("GOOGLE_API_KEY is not set - Gemini API calls will fail")
        if not self.dt_platform_token:
            warnings.append("DT_PLATFORM_TOKEN is not set - Dynatrace MCP will fail")
        if not self.github_token:
            warnings.append("GITHUB_TOKEN is not set - PR creation will fail")
        if not self.gcp_project_id:
            warnings.append("GCP_PROJECT_ID is not set - Cloud Run scaling will fail")
        return warnings


from contextvars import ContextVar

# A thread-safe context variable to hold the current tenant's config overrides
tenant_context: ContextVar[dict] = ContextVar("tenant_context", default={})

@lru_cache()
def _get_base_settings() -> Settings:
    """Get cached base settings from environment variables."""
    return Settings()

def get_settings() -> Settings:
    """Get application settings, merging base env vars with current tenant config."""
    base_settings = _get_base_settings()
    overrides = tenant_context.get()
    
    if overrides:
        # Create a new Settings object with the overrides applied
        # This keeps the base settings immutable and safe across concurrent requests
        return base_settings.model_copy(update=overrides)
        
    return base_settings
