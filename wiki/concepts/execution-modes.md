# Five Execution Modes

**Cross-cutting concept appearing in**: [cli.py](../summaries/cli.md), [gui.py](../summaries/gui.md), [server.py](../summaries/server.md), [renderer.py](../summaries/renderer.md)

## Facts

Codedocent supports five distinct execution modes (source: cli.py:402-434):

### 1. Interactive Mode (default)
- Triggered by: no mode flags, or wizard choice 1
- Behavior: starts localhost HTTP server, opens browser, analyzes nodes on-demand when clicked
- Entry: `_run_interactive_mode` -> `start_server` (source: cli.py:374-385)
- Uses [server.py](../summaries/server.md) for the HTTP interface

### 2. Full Export Mode (`--full`)
- Triggered by: `--full` flag, or wizard choice 2
- Behavior: analyzes all nodes upfront, writes self-contained static HTML
- Entry: `_run_full_mode` -> `analyze` + `render` (source: cli.py:361-372)
- Supports parallel workers (`--workers N`)

### 3. Text Tree Mode (`--text`)
- Triggered by: `--text` flag, or wizard choice 3
- Behavior: quality scoring only, prints text tree to terminal
- Entry: `_run_text_mode` -> `analyze_no_ai` + `print_tree` (source: cli.py:343-348)
- No AI calls, no HTML output

### 4. Architecture Mode (`--arch`)
- Triggered by: `--arch` flag, or wizard choice 4
- Behavior: starts server and opens `/arch` path showing dependency graph
- Entry: `_run_architecture_mode` -> `start_server(open_path="/arch")` (source: cli.py:388-399)
- Uses D3.js force-directed graph visualization

### 5. No-AI HTML Mode (`--no-ai`)
- Triggered by: `--no-ai` flag
- Behavior: quality scoring only, writes static HTML with placeholder summaries
- Entry: `_run_no_ai_mode` -> `analyze_no_ai` + `render` (source: cli.py:351-358)

### GUI Launcher (`--gui`)
- Not a mode per se, but launches [gui.py](../summaries/gui.md) which then starts any of the above modes via subprocess

## Inferences

The interactive mode is the primary use case -- it's the default and the one the README emphasizes. Full mode exists for sharing (produces a standalone HTML file). Text mode is minimal and likely used for CI or quick checks. Architecture mode was added in v1.0.0 as a major feature.

The wizard design (no-args launches wizard) is deliberately low-friction: a new user just types `codedocent` and gets guided through setup.
