from app.services.tool_proxy import resolve_headers, redact_headers, redact_header_value


def test_resolve_headers_merges_global_and_user_headers():
    global_headers = {"X-Tenant-Id": "global-tenant", "X-Global-Flag": "true"}
    user_headers = {"Authorization": "Bearer synthetic_token", "X-Tenant-Id": "user-custom-tenant"}

    resolved = resolve_headers(global_headers, user_headers)
    assert resolved["X-Global-Flag"] == "true"
    # User override takes precedence
    assert resolved["X-Tenant-Id"] == "user-custom-tenant"
    assert resolved["Authorization"] == "Bearer synthetic_token"


def test_disallowed_headers_cannot_be_overridden():
    global_headers = {"Host": "original-host.com"}
    user_headers = {"Host": "malicious-host.com", "Content-Length": "999"}

    resolved = resolve_headers(global_headers, user_headers)
    assert "Host" not in resolved
    assert "Content-Length" not in resolved


def test_redact_sensitive_headers():
    synthetic_key = "synthetic_key_" + ("0" * 12)
    headers = {
        "Authorization": f"Bearer {synthetic_key}",
        "X-API-Key": synthetic_key,
        "Accept": "application/json",
    }
    redacted = redact_headers(headers)
    assert redacted["Accept"] == "application/json"
    assert "****" in redacted["Authorization"]
    assert synthetic_key not in redacted["Authorization"]
    assert "****" in redacted["X-API-Key"]
    assert synthetic_key not in redacted["X-API-Key"]
