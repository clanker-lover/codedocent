# cloud_ai.py

**Source**: `codedocent/cloud_ai.py`
**Type**: Integration module
**Lines**: 208

## What It Does

Provides cloud AI support via OpenAI-compatible chat completion APIs. Handles request formatting, endpoint validation, error handling, and secret masking for API keys.

## Facts

- Four provider presets: OpenAI, OpenRouter, Groq, Custom (source: cloud_ai.py:12-52)
- Each provider preset defines: `name`, `endpoint`, `env_var`, `models` list (source: cloud_ai.py:12-52)
- API keys read from environment variables: `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `GROQ_API_KEY`, `CODEDOCENT_API_KEY` (source: cloud_ai.py:12-52)
- `_MaskedSecret` class wraps API keys so `repr()` and `str()` never reveal them (source: cloud_ai.py:59-81)
- Endpoint validation enforces HTTPS except for loopback addresses (source: cloud_ai.py:83-112)
- HTTP request uses `urllib.request` (no external HTTP library) with 60-second timeout (source: cloud_ai.py:55-56)
- Max response size is 10 MB (source: cloud_ai.py:56)
- Temperature is fixed at 0.3, max_tokens at 1024 (source: cloud_ai.py:128-129)
- User-Agent is `Codedocent/0.5.0` (source: cloud_ai.py:54)
- Error handling maps HTTP status codes to user-friendly messages: 401 -> "Unauthorized", 429 -> "Rate limited", 500+ -> "Server error" (source: cloud_ai.py:156-173)
- API keys are never included in error messages (verified by tests) (source: test_cloud_ai.py:236-253)

## Public API

- `CLOUD_PROVIDERS` -- dict of provider presets
- `cloud_chat(prompt, endpoint, api_key, model) -> str` -- sends a chat request, returns response
- `validate_cloud_config(provider, endpoint, api_key, model) -> (bool, str)` -- tests a configuration
- `_MaskedSecret` -- API key wrapper class
- `_validate_endpoint(endpoint) -> str` -- validates URL scheme and hostname

## Dependencies

- stdlib only: `urllib.request`, `json`, `socket`, `ipaddress`

## Architecture Role

Integration layer. Called by [analyzer](analyzer.md) when `ai_config["backend"] == "cloud"`. Alternative to [Ollama](../entities/ollama.md) for AI inference.

See also: [AI backend routing](../concepts/ai-backend-routing.md), [security model](../concepts/security-model.md)
