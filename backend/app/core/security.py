import base64
import hashlib
import time
from typing import Optional, List
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, JWTError
from pydantic import BaseModel
from app.core.config import settings

security_bearer = HTTPBearer(auto_error=False)

ALGORITHM = "HS256"


class AuthenticatedUser(BaseModel):
    id: str
    username: str
    email: str
    role: str  # viewer, operator, or admin


def verify_pkce_challenge(code_verifier: str, code_challenge: str, method: str = "S256") -> bool:
    if not code_verifier or not code_challenge:
        return False
    if method == "S256":
        digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
        computed = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
        return computed == code_challenge
    elif method == "plain":
        return code_verifier == code_challenge
    return False


def create_token(user_id: str, username: str, email: str, role: str, expires_in_seconds: int = 3600) -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "preferred_username": username,
        "email": email,
        "role": role,
        "roles": [role],
        "iss": settings.OIDC_ISSUER_URL if not settings.AUTH_DEMO_MODE else "signal-studio-demo-issuer",
        "aud": settings.OIDC_AUDIENCE,
        "iat": now,
        "exp": now + expires_in_seconds,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_and_validate_token(token: str) -> dict:
    try:
        # Never log token contents or print secrets
        expected_issuer = "signal-studio-demo-issuer" if settings.AUTH_DEMO_MODE else settings.OIDC_ISSUER_URL
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM],
            audience=settings.OIDC_AUDIENCE,
            issuer=expected_issuer,
            options={"verify_signature": True, "verify_aud": True, "verify_iss": True},
        )
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is invalid or expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
) -> AuthenticatedUser:
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header with Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_and_validate_token(token)

    user_id = payload.get("sub")
    username = payload.get("preferred_username", payload.get("sub", "unknown"))
    email = payload.get("email", "user@signalstudio.local")
    role = payload.get("role") or (payload.get("roles", ["viewer"])[0] if payload.get("roles") else "viewer")

    if not user_id or not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload is missing required identity claims",
        )

    if role not in ("viewer", "operator", "admin"):
        role = "viewer"

    return AuthenticatedUser(id=user_id, username=username, email=email, role=role)


def require_role(allowed_roles: List[str]):
    def role_dependency(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: role '{user.role}' lacks permission. Required one of: {allowed_roles}",
            )
        return user
    return role_dependency
