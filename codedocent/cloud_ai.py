"""Cloud AI support for OpenAI-compatible chat completion APIs."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

CLOUD_PROVIDERS: dict[str, dict] = {
    "openai": {
        "name": "OpenAI",
        "endpoint": "https://api.openai.com/v1/chat/completions",
        "env_var": "OPENAI_API_KEY",
        "models": [
            "gpt-4.1-nano",
            "gpt-4.1-mini",
            "gpt-4.1",
            "gpt-4o-mini",
            "gpt-4o",
        ],
    },
    "openrouter": {
        "name": "OpenRouter",
        "endpoint": "https://openrouter.ai/api/v1/chat/completions",
        "env_var": "OPENROUTER_API_KEY",
        "models": [
            "openai/gpt-4.1-nano",
            "google/gemini-2.5-flash",
            "anthropic/claude-sonnet-4",
            "meta-llama/llama-4-scout",
        ],
    },
    "groq": {
        "name": "Groq",
        "endpoint": "https://api.groq.com/openai/v1/chat/completions",
        "env_var": "GROQ_API_KEY",
        "models": [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "gemma2-9b-it",
        ],
    },
    "custom": {
        "name": "Custom",
        "endpoint": "",
        "env_var": "CUSTOM_AI_API_KEY",
        "models": [],
    },
}

_USER_AGENT = "Codedocent/0.5.0"
_TIMEOUT = 60


def _validate_endpoint(endpoint: str) -> str:
    """Validate and return the endpoint URL.

    Raises ``ValueError`` for invalid URLs or non-HTTPS endpoints
    (except localhost/127.0.0.1).
    """
    parsed = urllib.parse.urlparse(endpoint)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(
            f"Invalid URL scheme '{parsed.scheme}': must be http or https"
        )
    if not parsed.hostname:
        raise ValueError("Invalid URL: missing hostname")
    if parsed.scheme == "http":
        host = parsed.hostname.lower()
        if host not in ("localhost", "127.0.0.1"):
            raise ValueError(
                "HTTP endpoints are only allowed for localhost. "
                "Use HTTPS for remote endpoints."
            )
    return endpoint


def cloud_chat(
    prompt: str, endpoint: str, api_key: str, model: str,
) -> str:
    """Send a chat completion request to an OpenAI-compatible API.

    Returns the assistant's response content on success.
    Raises ``RuntimeError`` with a user-friendly message on failure.
    """
    endpoint = _validate_endpoint(endpoint)

    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 1024,
    }).encode("utf-8")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": _USER_AGENT,
    }

    req = urllib.request.Request(
        endpoint, data=body, headers=headers, method="POST",
    )

    # Derive a provider label from the endpoint for error messages
    provider = urllib.parse.urlparse(endpoint).hostname or "provider"

    try:
        with urllib.request.urlopen(  # nosec B310
            req, timeout=_TIMEOUT,
        ) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code == 401:  # noqa: PLR2004
            raise RuntimeError(
                "Unauthorized — check your API key"
            ) from None
        if e.code == 429:  # noqa: PLR2004
            raise RuntimeError(
                f"Rate limited by {provider}. Wait and try again."
            ) from None
        if e.code >= 500:  # noqa: PLR2004
            raise RuntimeError(
                f"Server error from {provider} (HTTP {e.code})"
            ) from None
        raise RuntimeError(
            f"HTTP {e.code} from {provider}"
        ) from None
    except (urllib.error.URLError, OSError):
        raise RuntimeError("Connection failed") from None

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise RuntimeError("Invalid response from API") from None

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError("Unexpected response format") from None

    return content


def validate_cloud_config(
    _provider: str, endpoint: str, api_key: str, model: str,
) -> tuple[bool, str]:
    """Test a cloud configuration with a lightweight request.

    Returns ``(True, "")`` on success, ``(False, error_message)`` on failure.
    """
    try:
        cloud_chat("Say hello in one word.", endpoint, api_key, model)
        return (True, "")
    except (RuntimeError, ValueError) as e:
        return (False, str(e))
