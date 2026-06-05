import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class User(Base):
    """A registered user of the SaaS platform."""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    # Note: In a real app using Supabase Auth, this table might just sync with auth.users
    # or we might store extra profile data here.
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    tenants = relationship("TenantConfig", back_populates="owner")


class TenantConfig(Base):
    """The configuration for a specific tenant (user's workspace).
    
    Stores the encrypted integration tokens needed to run the SRE Agent.
    """
    __tablename__ = "tenant_configs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    
    # Dynatrace Integration
    dt_environment = Column(String, nullable=True)  # e.g., 'abc12345'
    dt_platform_token = Column(String, nullable=True)
    
    # GitHub Integration
    github_token = Column(String, nullable=True)
    github_repo = Column(String, nullable=True)  # e.g., 'username/repo'
    
    # GCP Integration
    gcp_project = Column(String, nullable=True)
    gcp_region = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner = relationship("User", back_populates="tenants")
    incidents = relationship("IncidentLog", back_populates="tenant")


class IncidentLog(Base):
    """A record of an incident processed by the agent."""
    __tablename__ = "incident_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenant_configs.id"), nullable=False)
    
    dynatrace_problem_id = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="PROCESSING")  # PROCESSING, RESOLVED, FAILED
    
    # What the agent did
    pr_url = Column(String, nullable=True)
    scaled_service = Column(String, nullable=True)
    agent_logs = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    tenant = relationship("TenantConfig", back_populates="incidents")
