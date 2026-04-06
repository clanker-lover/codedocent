# gui.py

**Source**: `codedocent/gui.py`
**Type**: Entry point (alternative)
**Lines**: 298

## What It Does

Tkinter-based graphical launcher for codedocent. Provides a GUI with folder picker, AI backend toggle (cloud/local), model selection, provider dropdown, and mode selector. Launches the CLI as a subprocess.

## Facts

- Registered as `codedocent-gui` console script (source: pyproject.toml:29)
- Gracefully handles missing tkinter: prints install instructions and exits (source: gui.py:287-292)
- Cloud UI shows/hides dynamically based on backend radio button selection (source: gui.py:236-246)
- Cloud provider dropdown updates model list and API key status when changed (source: gui.py:248-270)
- Local model list fetched from Ollama in a background thread to avoid blocking the GUI (source: gui.py:111-126)
- Falls back to "No AI" if no Ollama models found (source: gui.py:117-118)
- Launches analysis as a subprocess via `subprocess.Popen` and closes the GUI window (source: gui.py:197-198)
- `_PROVIDER_KEYS` maps provider display names back to config keys (source: gui.py:147)

## Public API

- `main()` -- GUI entry point

## Dependencies

- `tkinter` (stdlib, optional) -- GUI framework
- [cloud_ai](cloud_ai.md) -- `CLOUD_PROVIDERS`
- [ollama_utils](ollama_utils.md) -- `check_ollama`, `fetch_ollama_models`

## Architecture Role

Alternative entry point. Provides a graphical interface for users who prefer clicking over typing. Delegates actual analysis to the CLI via subprocess.

See also: [execution modes](../concepts/execution-modes.md)
