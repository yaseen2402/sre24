from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from sre_agent.db.session import get_db
from sre_agent.db.models import TenantConfig

router = APIRouter(prefix="/api/tenant", tags=["Tenant Management"])

class TenantCreateResponse(BaseModel):
    tenant_id: str
    message: str

from typing import Optional

class TenantUpdateRequest(BaseModel):
    name: str
    dt_environment: Optional[str] = None
    dt_platform_token: Optional[str] = None
    github_token: Optional[str] = None
    github_repo: Optional[str] = None
    gcp_project: Optional[str] = None
    gcp_region: Optional[str] = None

@router.post("/", response_model=TenantCreateResponse)
def create_tenant(db: Session = Depends(get_db)):
    """Create a new workspace (Tenant). 
    Returns the unique tenant_id which acts as the 'password' to access it.
    """
    from sre_agent.db.models import User
    
    # For hackathon "fast auth", ensure the dummy owner exists in the DB
    dummy_user_id = "anonymous_hackathon_user"
    user = db.query(User).filter(User.id == dummy_user_id).first()
    if not user:
        user = User(id=dummy_user_id, email="anonymous@sre24.com")
        db.add(user)
        try:
            db.commit()
        except Exception:
            db.rollback()

    new_tenant = TenantConfig(
        owner_id=dummy_user_id, 
        name="New SRE Workspace"
    )
    db.add(new_tenant)
    db.commit()
    db.refresh(new_tenant)
    
    return {
        "tenant_id": new_tenant.id,
        "message": "Workspace created! Save this ID to access your dashboard."
    }

@router.get("/{tenant_id}")
def get_tenant(tenant_id: str, db: Session = Depends(get_db)):
    """Fetch the configuration for a specific tenant."""
    tenant = db.query(TenantConfig).filter(TenantConfig.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    return {
        "id": tenant.id,
        "name": tenant.name,
        "dt_environment": tenant.dt_environment,
        # Don't return the full token for security, just an indicator if it exists
        "has_dt_token": bool(tenant.dt_platform_token),
        "has_github_token": bool(tenant.github_token),
        "github_repo": tenant.github_repo,
        "gcp_project": tenant.gcp_project,
        "gcp_region": tenant.gcp_region,
    }

@router.put("/{tenant_id}")
def update_tenant(tenant_id: str, config: TenantUpdateRequest, db: Session = Depends(get_db)):
    """Update the credentials and configuration for a tenant."""
    tenant = db.query(TenantConfig).filter(TenantConfig.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    tenant.name = config.name
    tenant.dt_environment = config.dt_environment
    tenant.github_repo = config.github_repo
    tenant.gcp_project = config.gcp_project
    tenant.gcp_region = config.gcp_region
    
    # Only update tokens if new ones are provided
    if config.dt_platform_token:
        tenant.dt_platform_token = config.dt_platform_token
    if config.github_token:
        tenant.github_token = config.github_token
        
    db.commit()
    return {"message": "Configuration saved successfully"}

@router.get("/{tenant_id}/incidents")
def get_tenant_incidents(tenant_id: str, db: Session = Depends(get_db)):
    """Fetch the history of incidents processed for this workspace."""
    from sre_agent.db.models import IncidentLog
    
    tenant = db.query(TenantConfig).filter(TenantConfig.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    incidents = db.query(IncidentLog).filter(
        IncidentLog.tenant_id == tenant_id
    ).order_by(IncidentLog.created_at.desc()).all()
    
    return [
        {
            "id": inc.id,
            "dynatrace_problem_id": inc.dynatrace_problem_id,
            "status": inc.status,
            "pr_url": inc.pr_url,
            "agent_logs": inc.agent_logs,
            "created_at": inc.created_at
        }
        for inc in incidents
    ]
