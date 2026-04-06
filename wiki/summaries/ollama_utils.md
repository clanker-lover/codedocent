# ollama_utils.py

**Source**: `codedocent/ollama_utils.py`
**Type**: Utility module
**Lines**: 32

## What It Does

Shared utility functions for checking Ollama availability and fetching available models. Used by both the CLI wizard and the GUI launcher.

## Facts

- `check_ollama()` hits `http://localhost:11434` with a 3-second timeout (source: ollama_utils.py:10-18)
- `fetch_ollama_models()` hits `http://localhost:11434/api/tags` with a 5-second timeout (source: ollama_utils.py:21-31)
- Both functions use `urllib.request` directly (no external HTTP library) (source: ollama_utils.py:6-7)
- Both catch `OSError` and `URLError`, returning safe defaults on failure (source: ollama_utils.py:17-18, 30-31)

## Public API

- `check_ollama() -> bool` -- returns True if Ollama is reachable
- `fetch_ollama_models() -> list[str]` -- returns model names from Ollama API

## Dependencies

- stdlib only: `json`, `urllib.request`

## Architecture Role

Shared utility. Imported by [CLI](cli.md) and [GUI](gui.md) to avoid duplicating Ollama connectivity checks.

See also: [Ollama](../entities/ollama.md), [AI backend routing](../concepts/ai-backend-routing.md)
