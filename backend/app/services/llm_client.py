import re
from typing import List, Dict, Any, Optional
import httpx
from pydantic import BaseModel
from app.core.config import settings


class LLMResult(BaseModel):
    provider: str
    model: str
    content: str
    reasoning: Optional[str] = None
    is_offline_fallback: bool = False
    usage: Dict[str, int] = {}


def sanitize_error_message(error_str: str) -> str:
    # Redact any credential-like patterns
    redacted = re.sub(r"(Bearer\s+)[A-Za-z0-9_\-\.]{8,}", r"\1[REDACTED]", error_str, flags=re.IGNORECASE)
    redacted = re.sub(r"(key[=:\s]+)[A-Za-z0-9_\-\.]{8,}", r"\1[REDACTED]", redacted, flags=re.IGNORECASE)
    return redacted


async def dispatch_llm_request(
    messages: List[Dict[str, Any]],
    provider: Optional[str] = None,
    model: Optional[str] = None,
    system_prompt: Optional[str] = None,
) -> LLMResult:
    active_provider = (provider or settings.LLM_PROVIDER or "openai-compatible").lower()
    active_model = model or settings.LLM_MODEL or "gpt-4o-mini"
    api_key = settings.LLM_API_KEY

    # Check for offline deterministic execution
    if not api_key and active_provider != "ollama":
        last_user_message = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user_message = m.get("content", "")
                break

        deterministic_summary = (
            f"[Offline Advisory Mode] Grounded response for: '{last_user_message[:60]}...'. "
            "No upstream LLM_API_KEY was provided. Operating in deterministic offline verification mode."
        )
        return LLMResult(
            provider="offline-deterministic",
            model="deterministic-rule-engine",
            content=deterministic_summary,
            reasoning="Deterministic offline analysis completed without external network credentials.",
            is_offline_fallback=True,
            usage={"prompt_tokens": len(last_user_message.split()), "completion_tokens": len(deterministic_summary.split())},
        )

    # Provider request formatting
    async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
        try:
            if active_provider in ("openai-compatible", "openai"):
                base_url = (settings.LLM_BASE_URL or "https://api.openai.com/v1").rstrip("/")
                endpoint = f"{base_url}/chat/completions"
                headers = {
                    "Authorization": f"Bearer {api_key or ''}",
                    "Content-Type": "application/json",
                }
                formatted_msgs = list(messages)
                if system_prompt:
                    formatted_msgs.insert(0, {"role": "system", "content": system_prompt})

                resp = await client.post(
                    endpoint,
                    headers=headers,
                    json={
                        "model": active_model,
                        "messages": formatted_msgs,
                        "temperature": 0.2,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                choice = data["choices"][0]["message"]
                usage = data.get("usage", {})
                return LLMResult(
                    provider=active_provider,
                    model=active_model,
                    content=choice.get("content", ""),
                    reasoning=choice.get("reasoning_content"),
                    is_offline_fallback=False,
                    usage=usage,
                )

            elif active_provider == "anthropic":
                base_url = (settings.LLM_BASE_URL or "https://api.anthropic.com").rstrip("/")
                endpoint = f"{base_url}/v1/messages"
                headers = {
                    "x-api-key": api_key or "",
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                }
                user_assistant_msgs = [m for m in messages if m.get("role") in ("user", "assistant")]
                payload: Dict[str, Any] = {
                    "model": active_model,
                    "messages": user_assistant_msgs,
                    "max_tokens": 1024,
                }
                if system_prompt:
                    payload["system"] = system_prompt

                resp = await client.post(endpoint, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                content_blocks = data.get("content", [])
                text_out = "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")
                usage = data.get("usage", {})
                return LLMResult(
                    provider=active_provider,
                    model=active_model,
                    content=text_out,
                    reasoning=None,
                    is_offline_fallback=False,
                    usage=usage,
                )

            elif active_provider == "gemini":
                base_url = (settings.LLM_BASE_URL or "https://generativelanguage.googleapis.com").rstrip("/")
                endpoint = f"{base_url}/v1beta/models/{active_model}:generateContent"
                headers = {
                    "x-goog-api-key": api_key or "",
                    "Content-Type": "application/json",
                }
                contents = []
                for m in messages:
                    role = "user" if m.get("role") == "user" else "model"
                    contents.append({"role": role, "parts": [{"text": m.get("content", "")}]})

                resp = await client.post(endpoint, headers=headers, json={"contents": contents})
                resp.raise_for_status()
                data = resp.json()
                candidate = data["candidates"][0]["content"]["parts"][0]["text"]
                return LLMResult(
                    provider=active_provider,
                    model=active_model,
                    content=candidate,
                    reasoning=None,
                    is_offline_fallback=False,
                    usage={},
                )

            elif active_provider == "ollama":
                base_url = (settings.LLM_BASE_URL or "http://127.0.0.1:11434").rstrip("/")
                endpoint = f"{base_url}/api/chat"
                headers = {"Content-Type": "application/json"}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"

                resp = await client.post(
                    endpoint,
                    headers=headers,
                    json={
                        "model": active_model,
                        "messages": messages,
                        "stream": False,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                msg = data.get("message", {})
                return LLMResult(
                    provider="ollama",
                    model=active_model,
                    content=msg.get("content", ""),
                    reasoning=None,
                    is_offline_fallback=False,
                    usage={},
                )

            else:
                raise ValueError(f"Unsupported LLM provider: {active_provider}")

        except httpx.HTTPStatusError as exc:
            msg = sanitize_error_message(f"Provider HTTP error {exc.response.status_code}: {exc.response.text}")
            raise RuntimeError(msg) from exc
        except httpx.RequestError as exc:
            msg = sanitize_error_message(f"Provider connection error: {str(exc)}")
            raise RuntimeError(msg) from exc
