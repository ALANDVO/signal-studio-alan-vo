import base64
import hashlib
import pytest
from fastapi import HTTPException
from app.core.config import Settings, verify_startup_safety
from app.core.security import verify_pkce_challenge, create_token, decode_and_validate_token


def test_pkce_challenge_verification_s256():
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")

    assert verify_pkce_challenge(verifier, challenge, method="S256") is True
    assert verify_pkce_challenge("wrong-verifier", challenge, method="S256") is False


def test_token_creation_and_decoding():
    token = create_token("user-test-01", "tester", "tester@test.com", "operator")
    claims = decode_and_validate_token(token)
    assert claims["sub"] == "user-test-01"
    assert claims["role"] == "operator"
    assert "signal-studio" in claims["iss"]


def test_invalid_token_rejected():
    with pytest.raises(HTTPException) as exc_info:
        decode_and_validate_token("invalid.token.payload")
    assert exc_info.value.status_code == 401


def test_startup_safety_refuses_demo_mode_in_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(ValueError) as exc_info:
        Settings(ENVIRONMENT="production", AUTH_DEMO_MODE=True)
    assert "SECURITY VIOLATION" in str(exc_info.value)


def test_unauthenticated_request_rejected(client):
    response = client.get("/api/chats")
    assert response.status_code == 401


def test_role_denial_for_viewer_calling_operator_endpoint(client, viewer_token):
    # Viewer tries to call an endpoint requiring operator/admin role
    response = client.post(
        "/api/eval/run",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={"benchmark_name": "signal-reasoning-tree-v1"},
    )
    assert response.status_code == 403
    assert "Forbidden" in response.json()["detail"]


def test_demo_login_endpoint(client):
    response = client.post(
        "/api/auth/demo-login",
        json={"role": "operator", "username": "analyst-demo"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["role"] == "operator"
    assert data["username"] == "analyst-demo"
