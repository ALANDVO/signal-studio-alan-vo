import json
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_role, AuthenticatedUser
from app.models.entities import ToolServer, UserToolConfig, AuditLog
from app.models.schemas import (
    ToolServerCreate,
    ToolServerResponse,
    UserToolConfigUpdate,
    UserToolConfigResponse,
    ToolExecuteRequest,
    ToolExecuteResponse,
)
from app.services.tool_proxy import resolve_headers, redact_headers, execute_tool_request

router = APIRouter(prefix="/api/tools", tags=["Tool & MCP Servers"])


@router.get("/servers", response_model=List[ToolServerResponse])
def list_servers(
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    servers = db.query(ToolServer).filter(ToolServer.is_active == True).all()  # noqa: E712
    return [
        ToolServerResponse(
            id=s.id,
            name=s.name,
            base_url=s.base_url,
            description=s.description,
            global_headers_redacted=redact_headers(json.loads(s.global_headers_json or "{}")),
            is_active=s.is_active,
            created_at=s.created_at,
        )
        for s in servers
    ]


@router.post("/servers", response_model=ToolServerResponse, status_code=status.HTTP_201_CREATED)
def create_server(
    req: ToolServerCreate,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_role(["operator", "admin"])),
):
    existing = db.query(ToolServer).filter(ToolServer.name == req.name).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Tool server '{req.name}' already exists.")

    server = ToolServer(
        id=str(uuid.uuid4()),
        name=req.name,
        base_url=req.base_url,
        description=req.description,
        global_headers_json=json.dumps(req.global_headers or {}),
        is_active=req.is_active,
    )
    db.add(server)
    audit = AuditLog(
        action="CREATE_TOOL_SERVER",
        user_id=user.id,
        user_role=user.role,
        resource_type="tool_server",
        resource_id=server.id,
        details_json=json.dumps({"name": server.name}),
    )
    db.add(audit)
    db.commit()
    db.refresh(server)

    return ToolServerResponse(
        id=server.id,
        name=server.name,
        base_url=server.base_url,
        description=server.description,
        global_headers_redacted=redact_headers(json.loads(server.global_headers_json or "{}")),
        is_active=server.is_active,
        created_at=server.created_at,
    )


@router.get("/servers/{server_id}/config", response_model=UserToolConfigResponse)
def get_user_tool_config(
    server_id: str,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    config = db.query(UserToolConfig).filter(
        UserToolConfig.server_id == server_id,
        UserToolConfig.user_id == user.id,
    ).first()

    headers = json.loads(config.user_headers_json) if config else {}
    return UserToolConfigResponse(
        server_id=server_id,
        user_headers_redacted=redact_headers(headers),
        updated_at=config.updated_at if config else ToolServer.created_at.default.arg(),
    )


@router.put("/servers/{server_id}/config", response_model=UserToolConfigResponse)
def update_user_tool_config(
    server_id: str,
    req: UserToolConfigUpdate,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    server = db.query(ToolServer).filter(ToolServer.id == server_id).first()
    if not server:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool server not found")

    config = db.query(UserToolConfig).filter(
        UserToolConfig.server_id == server_id,
        UserToolConfig.user_id == user.id,
    ).first()

    if not config:
        config = UserToolConfig(
            id=str(uuid.uuid4()),
            user_id=user.id,
            server_id=server_id,
            user_headers_json=json.dumps(req.user_headers),
        )
        db.add(config)
    else:
        config.user_headers_json = json.dumps(req.user_headers)

    audit = AuditLog(
        action="UPDATE_USER_TOOL_CONFIG",
        user_id=user.id,
        user_role=user.role,
        resource_type="user_tool_config",
        resource_id=server_id,
        details_json=json.dumps({"headers_keys": list(req.user_headers.keys())}),
    )
    db.add(audit)
    db.commit()
    db.refresh(config)

    return UserToolConfigResponse(
        server_id=server_id,
        user_headers_redacted=redact_headers(req.user_headers),
        updated_at=config.updated_at,
    )


@router.post("/execute", response_model=ToolExecuteResponse)
async def execute_tool(
    req: ToolExecuteRequest,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_role(["operator", "admin"])),
):
    server = db.query(ToolServer).filter(ToolServer.id == req.server_id).first()
    if not server:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool server not found")

    global_headers = json.loads(server.global_headers_json or "{}")

    # Fetch user overrides
    user_config = db.query(UserToolConfig).filter(
        UserToolConfig.server_id == req.server_id,
        UserToolConfig.user_id == user.id,
    ).first()
    user_headers = json.loads(user_config.user_headers_json) if user_config else {}

    resolved = resolve_headers(global_headers, user_headers)

    status_code, data = await execute_tool_request(
        base_url=server.base_url,
        path=req.path,
        method=req.method,
        resolved_headers=resolved,
        payload=req.payload,
    )

    return ToolExecuteResponse(
        server_name=server.name,
        status_code=status_code,
        resolved_headers_redacted=redact_headers(resolved),
        data=data,
    )
