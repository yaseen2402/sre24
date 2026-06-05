"""Pydantic models for Dynatrace Problem Notification webhook payloads.

Reference: https://docs.dynatrace.com/docs/observe-and-explore/problems/notifications/webhook-integration
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ProblemStateEnum(str, Enum):
    """Dynatrace problem states."""
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    MERGED = "MERGED"


class ProblemSeverityEnum(str, Enum):
    """Dynatrace problem severity levels."""
    AVAILABILITY = "AVAILABILITY"
    ERROR = "ERROR"
    PERFORMANCE = "PERFORMANCE"
    RESOURCE_CONTENTION = "RESOURCE_CONTENTION"
    CUSTOM_ALERT = "CUSTOM_ALERT"


class ImpactedEntity(BaseModel):
    """An entity impacted by a Dynatrace problem."""
    type: str = Field(..., description="Entity type (e.g., SERVICE, HOST, PROCESS_GROUP)")
    name: str = Field(..., description="Entity display name")
    entity: str = Field(..., description="Dynatrace entity ID")


class RootCauseEntityModel(BaseModel):
    """The root cause entity identified by Dynatrace Davis AI."""
    type: str = Field(..., description="Entity type")
    name: str = Field(..., description="Entity display name")
    entity: str = Field(..., description="Dynatrace entity ID")


class DynatraceWebhookPayload(BaseModel):
    """Top-level Dynatrace Problem Notification webhook payload.
    
    This model captures the essential fields from a Dynatrace problem notification.
    Fields are made optional where possible for flexibility.
    """
    PID: str = Field(..., alias="PID", description="Dynatrace Problem ID (e.g., P-12345)")
    ProblemID: str = Field(default="", description="Numeric problem ID")
    State: ProblemStateEnum = Field(default=ProblemStateEnum.OPEN, description="Problem state")
    ProblemTitle: str = Field(default="", description="Problem title/summary")
    ProblemSeverity: Optional[ProblemSeverityEnum] = Field(default=None, description="Severity level")
    ProblemURL: str = Field(default="", description="URL to the problem in Dynatrace UI")
    ImpactedEntities: list[ImpactedEntity] = Field(default_factory=list, description="Entities affected")
    RootCauseEntity: Optional[RootCauseEntityModel] = Field(default=None, description="Root cause entity")
    ProblemDetailsText: str = Field(default="", description="Detailed problem description from Davis AI")
    Tags: list[str] = Field(default_factory=list, description="Tags associated with the problem")
    
    model_config = {
        "populate_by_name": True,
        "extra": "allow",  # Allow extra fields from Dynatrace
    }


class AgentActionResult(BaseModel):
    """Result of an action taken by the SRE agent."""
    action: str = Field(..., description="Action type (e.g., 'scaled_infrastructure', 'created_pr')")
    success: bool = Field(..., description="Whether the action succeeded")
    details: str = Field(default="", description="Human-readable details")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")


class WebhookResponse(BaseModel):
    """Response returned by the webhook endpoint."""
    status: str = Field(..., description="Processing status")
    problem_id: str = Field(..., description="Dynatrace Problem ID")
    message: str = Field(default="", description="Status message")
    actions_taken: list[AgentActionResult] = Field(default_factory=list, description="Actions taken by the agent")
