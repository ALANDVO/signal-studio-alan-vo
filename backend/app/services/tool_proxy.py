import httpx
from typing import Dict, Any, Tuple


SENSITIVE_HEADER_KEYS = {
    "authorization",
    "x-api-key",
    "api-key",
    "token",
    "x-auth-token",
    "bearer",
    "cookie",
    "proxy-authorization",
}

DISALLOWED_OVERRIDE_HEADERS = {
    "host",
    "content-length",
    "connection",
    "upgrade",
}


def redact_header_value(header_name: str, value: str) -> str:
    if not value:
        return ""
    if header_name.lower() in SENSITIVE_HEADER_KEYS or "key" in header_name.lower() or "secret" in header_name.lower():
        if len(value) <= 6:
            return "****"
        return f"****{value[-4:]}"
    return value


def redact_headers(headers: Dict[str, str]) -> Dict[str, str]:
    return {k: redact_header_value(k, str(v)) for k, v in headers.items()}


def resolve_headers(global_headers: Dict[str, str], user_headers: Dict[str, str]) -> Dict[str, str]:
    resolved: Dict[str, str] = {}
    
    # Apply global headers
    for k, v in global_headers.items():
        if k.lower() not in DISALLOWED_OVERRIDE_HEADERS:
            resolved[k] = str(v)

    # Apply user-scoped headers, overriding globals if permitted
    for k, v in user_headers.items():
        if k.lower() not in DISALLOWED_OVERRIDE_HEADERS:
            resolved[k] = str(v)

    return resolved


async def execute_tool_request(
    base_url: str,
    path: str,
    method: str,
    resolved_headers: Dict[str, str],
    payload: Any = None,
    timeout: float = 10.0,
) -> Tuple[int, Any]:
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            if method.upper() == "GET":
                response = await client.get(url, headers=resolved_headers, params=payload)
            elif method.upper() == "POST":
                response = await client.post(url, headers=resolved_headers, json=payload)
            elif method.upper() == "PUT":
                response = await client.put(url, headers=resolved_headers, json=payload)
            elif method.upper() == "DELETE":
                response = await client.delete(url, headers=resolved_headers)
            else:
                return 400, {"error": f"Unsupported HTTP method: {method}"}

            try:
                data = response.json()
            except Exception:
                data = response.text

            return response.status_code, data
        except httpx.RequestError as exc:
            return 502, {"error": f"Tool proxy gateway error connecting to {url}: {str(exc)}"}
