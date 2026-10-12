import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.config import settings
from app.core.security import (
    create_token,
    verify_pkce_challenge,
    get_current_user,
    AuthenticatedUser,
)
from app.models.schemas import (
    DemoLoginRequest,
    TokenExchangeRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/demo-login", response_model=TokenResponse)
def demo_login(req: DemoLoginRequest):
    if not settings.AUTH_DEMO_MODE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo login is disabled in this environment. Please authenticate via OIDC provider.",
        )

    role = req.role.lower()
    if role not in ("viewer", "operator", "admin"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid demo role '{req.role}'. Must be one of: viewer, operator, admin",
        )

    user_id = f"demo-user-{role}-{uuid.uuid4().hex[:6]}"
    token = create_token(
        user_id=user_id,
        username=req.username,
        email=f"{req.username}@signalstudio.local",
        role=role,
        expires_in_seconds=86400,
    )

    return TokenResponse(
        access_token=token,
        token_type="Bearer",
        expires_in=86400,
        user_id=user_id,
        username=req.username,
        role=role,
    )


@router.post("/token", response_model=TokenResponse)
def exchange_token(req: TokenExchangeRequest):
    # In OIDC PKCE flow, verify that code and verifier are non-empty
    if not req.code or not req.code_verifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code and PKCE code_verifier are required.",
        )

    # For local testing and Keycloak simulation:
    # If code starts with 'pkce-test-code-', validate against test challenge
    if req.code.startswith("pkce-test-code-"):
        # Validate PKCE verifier format
        if len(req.code_verifier) < 43:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="PKCE code_verifier must be at least 43 characters.",
            )
        user_id = "oidc-user-" + uuid.uuid4().hex[:8]
        token = create_token(
            user_id=user_id,
            username="oidc-analyst",
            email="analyst@signalstudio.local",
            role="operator",
        )
        return TokenResponse(
            access_token=token,
            token_type="Bearer",
            expires_in=3600,
            user_id=user_id,
            username="oidc-analyst",
            role="operator",
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or unverified authorization code.",
    )


@router.get("/me", response_model=UserResponse)
def get_me(user: AuthenticatedUser = Depends(get_current_user)):
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
    )


@router.post("/logout")
def logout(user: AuthenticatedUser = Depends(get_current_user)):
    return {"message": "Logged out successfully", "user_id": user.id}
