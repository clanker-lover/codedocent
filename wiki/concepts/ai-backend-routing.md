# AI Backend Routing

**Cross-cutting concept appearing in**: [analyzer.py](../summaries/analyzer.md), [cloud_ai.py](../summaries/cloud_ai.md), [ollama_utils.py](../summaries/ollama_utils.md), [cli.py](../summaries/cli.md), [gui.py](../summaries/gui.md)

## Facts

Codedocent supports three AI backends, selected at startup:

### 1. Local AI via Ollama (default)
- Uses the `ollama` Python package (source: analyzer.py:24-25)
- Default model: `qwen3:14b` (source: cli.py:169, 254)
- Availability checked via HTTP to `localhost:11434` (source: ollama_utils.py:10-18)
- Model list fetched from Ollama's `/api/tags` endpoint (source: ollama_utils.py:21-31)
- AI calls go through `ollama.chat()` (source: analyzer.py:231-256)

### 2. Cloud AI via OpenAI-compatible APIs
- Four provider presets: OpenAI, OpenRouter, Groq, Custom (source: cloud_ai.py:12-52)
- API keys from environment variables (source: cloud_ai.py:12-52)
- Requests via `urllib.request` -- no external HTTP library (source: cloud_ai.py:139-148)
- Validated before use: test request with "Say hello in one word" (source: cloud_ai.py:195-207)
- AI calls go through `cloud_chat()` (source: analyzer.py:185-216)

### 3. No AI (`--no-ai`)
- Quality scoring and structure only (source: analyzer.py:652-676)
- Summaries show placeholders like "AI summary pending..." in HTML (source: test_renderer.py:86-91)

### Routing Logic
- `ai_config` dict with `backend: "cloud"` triggers cloud path (source: analyzer.py:227-228)
- `ai_config` is None triggers Ollama path (source: analyzer.py:227-228)
- `--no-ai` flag bypasses both (source: cli.py:423-424)

### Cache Model ID
- Ollama: model name as-is, e.g., `qwen3:14b` (source: analyzer.py:259-263)
- Cloud: composite key, e.g., `cloud:openai:gpt-4.1-nano` (source: analyzer.py:259-263)
- Different backends invalidate each other's caches

## Inferences

The routing is clean: a single `ai_config` dict (or None) flows from CLI through analyzer to the appropriate backend. The cloud implementation deliberately avoids external HTTP libraries (`requests`, `httpx`) -- using only stdlib `urllib` -- keeping the dependency footprint small.

See also: [Ollama](../entities/ollama.md), [caching strategy](caching-strategy.md)
