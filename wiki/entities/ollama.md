# Ollama

**Type**: External dependency / service
**Referenced in**: [analyzer.py](../summaries/analyzer.md), [ollama_utils.py](../summaries/ollama_utils.md), [cli.py](../summaries/cli.md), [gui.py](../summaries/gui.md), [benchmark.py](../summaries/benchmark.md), [pyproject.toml](../summaries/pyproject.md)

## Facts

- Python package: `ollama>=0.4` (source: pyproject.toml:18)
- Local AI inference service running at `http://localhost:11434` (source: ollama_utils.py:13)
- Used via `ollama.chat(model=..., messages=[...])` (source: analyzer.py:233-235)
- Response structure: `response.message.content` contains the text output (source: analyzer.py:244-247)
- Import is optional: guarded by `try/except ImportError` (source: analyzer.py:24-25)
- Default model: `qwen3:14b` (source: cli.py:169)
- Availability checked before use; fallback to no-AI if unreachable (source: cli.py:188-198)
- Model list fetched from `/api/tags` endpoint (source: ollama_utils.py:24)

## Role in Codedocent

Default AI backend. Ollama runs locally, so code never leaves the user's machine. This is the privacy-first option compared to [cloud AI](../summaries/cloud_ai.md).

The benchmark tool tests three Ollama models: `gemma3:4b`, `qwen3:8b`, `gemma3:12b` (source: benchmark.py:16-19).

## Open Questions

- The `ollama` package is a hard dependency in pyproject.toml but imported with try/except in analyzer.py -- this suggests it was previously optional
