import base64
import hashlib
from fastapi.testclient import TestClient


def test_full_oidc_pkce_exchange_and_authorized_api_workflow(client: TestClient):
    # 1. Generate PKCE code verifier and code challenge
    code_verifier = "a" * 45  # valid length >= 43
    digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")

    # 2. Reject invalid PKCE code verifier (too short or missing)
    reject_resp = client.post(
        "/api/auth/token",
        json={"code": "pkce-test-code-12345", "code_verifier": "short"},
    )
    assert reject_resp.status_code == 400

    # 3. Successful token exchange with valid PKCE verifier
    token_resp = client.post(
        "/api/auth/token",
        json={"code": "pkce-test-code-12345", "code_verifier": code_verifier},
    )
    assert token_resp.status_code == 200
    token_data = token_resp.json()
    access_token = token_data["access_token"]
    assert token_data["token_type"] == "Bearer"

    # 4. Propagate token into authorized API request: /api/auth/me
    headers = {"Authorization": f"Bearer {access_token}"}
    me_resp = client.get("/api/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["role"] == "operator"

    # 5. Core Create/Read conversation workflow across real HTTP boundary
    create_chat_resp = client.post(
        "/api/chats",
        headers=headers,
        json={"title": "Integration Test Chat", "metadata": {"test": True}},
    )
    assert create_chat_resp.status_code == 201
    chat_id = create_chat_resp.json()["id"]

    # 6. Post a message with reasoning tags
    msg_resp = client.post(
        f"/api/chats/{chat_id}/messages",
        headers=headers,
        json={
            "role": "assistant",
            "content": "<think>Step 1 verify</think>Completed task verification.",
        },
    )
    assert msg_resp.status_code == 201
    msg_data = msg_resp.json()
    assert msg_data["content"] == "Completed task verification."
    assert "Step 1 verify" in (msg_data["reasoning"] or "")

    # 7. Get conversation details and assert message count
    get_chat_resp = client.get(f"/api/chats/{chat_id}", headers=headers)
    assert get_chat_resp.status_code == 200
    assert get_chat_resp.json()["message_count"] == 1

    # 8. Note workflow: create note, export as markdown, import markdown
    note_resp = client.post(
        "/api/notes",
        headers=headers,
        json={"title": "Test Research Note", "content": "Evidence and findings.", "tags": "research,eval"},
    )
    assert note_resp.status_code == 201
    note_id = note_resp.json()["id"]

    export_resp = client.get(f"/api/notes/{note_id}/export", headers=headers)
    assert export_resp.status_code == 200
    assert "text/markdown" in export_resp.headers["content-type"]
    assert "# Test Research Note" in export_resp.text

    # 9. Ingest knowledge document and search chunks
    doc_resp = client.post(
        "/api/knowledge/documents",
        headers=headers,
        json={
            "name": "Integration Doc",
            "content": "# Section Alpha\n\nDetailed content for Alpha.\n\n# Section Beta\n\nDetailed content for Beta.",
            "strategy": "structured_markdown",
        },
    )
    assert doc_resp.status_code == 201
    assert doc_resp.json()["chunk_count"] >= 2

    search_resp = client.post(
        "/api/knowledge/search",
        headers=headers,
        json={"query": "Detailed content for Alpha", "limit": 2},
    )
    assert search_resp.status_code == 200
    assert len(search_resp.json()["matches"]) > 0

    # 10. Verify audit log entry was created for mutation
    audit_resp = client.get("/api/audit/logs", headers=headers)
    assert audit_resp.status_code == 200
    actions = [log["action"] for log in audit_resp.json()]
    assert "CREATE_CONVERSATION" in actions
    assert "INGEST_DOCUMENT" in actions
