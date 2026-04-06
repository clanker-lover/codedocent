# cli.py

**Source**: `codedocent/cli.py`
**Type**: Entry point
**Lines**: 439

## What It Does

Main CLI entry point for codedocent. Provides argument parsing, an interactive setup wizard, and dispatches to the appropriate mode: text tree, no-AI HTML, full analysis HTML, interactive server, or architecture mode.

## Facts

- Entry point registered as `codedocent` console script (source: pyproject.toml:28)
- Setup wizard runs when no path argument is provided (source: cli.py:413-414)
- Wizard offers three backend choices: Cloud AI, Local AI (Ollama), No AI (source: cli.py:173-198)
- Wizard offers four mode choices: Interactive, Full export, Text tree, Architecture (source: cli.py:201-211)
- Default model is `qwen3:14b` (source: cli.py:169, 254)
- Default output file is `codedocent_output.html` (source: cli.py:249)
- Cloud provider setup validates the connection with a test request before proceeding (source: cli.py:146-151)
- `_build_ai_config` constructs cloud config from CLI args; validates endpoint, resolves API key from env vars (source: cli.py:295-340)
- `print_tree` renders a text representation of the CodeNode tree with indentation (source: cli.py:31-54)
- Deferred imports are used throughout to speed up initial load and avoid circular imports (source: cli.py:344-399)

## Public API

- `main()` -- CLI entry point
- `print_tree(node, indent)` -- text tree renderer

## Key Internal Functions

- `_run_wizard() -> Namespace` -- interactive setup flow
- `_build_arg_parser() -> ArgumentParser` -- CLI arg definitions
- `_build_ai_config(args) -> dict | None` -- cloud config builder
- `_run_text_mode`, `_run_no_ai_mode`, `_run_full_mode`, `_run_interactive_mode`, `_run_architecture_mode` -- mode dispatchers

## Dependencies

- [scanner](scanner.md) -- `scan_directory`
- [parser](parser.md) -- `parse_directory`, `CodeNode`
- [analyzer](analyzer.md) -- `analyze`, `analyze_no_ai`, `assign_node_ids`
- [renderer](renderer.md) -- `render`
- [server](server.md) -- `start_server`
- [cloud_ai](cloud_ai.md) -- `CLOUD_PROVIDERS`, `validate_cloud_config`, `_MaskedSecret`
- [ollama_utils](ollama_utils.md) -- `check_ollama`, `fetch_ollama_models`
- [gui](gui.md) -- `main` (deferred)

## Architecture Role

Orchestrator. The top-level entry point that wires together scanning, parsing, analysis, and rendering.

See also: [five execution modes](../concepts/execution-modes.md)
