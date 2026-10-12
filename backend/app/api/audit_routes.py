import json
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_role, AuthenticatedUser
from app.models.entities import AuditLog
from app.models.schemas import AuditLogResponse

router = APIRouter(prefix="/api/audit", tags=["Audit Trail"])


@router.get("/logs", response_model=List[AuditLogResponse])
def list_audit_logs(
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_role(["operator", "admin"])),
):
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)

    logs = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
    return [
        AuditLogResponse(
            id=l.id,
            action=l.action,
            user_id=l.user_id,
            user_role=l.user_role,
            resource_type=l.resource_type,
            resource_id=l.resource_id,
            details=json.loads(l.details_json or "{}"),
            created_at=l.created_at,
        )
        for l in logs
    ]
