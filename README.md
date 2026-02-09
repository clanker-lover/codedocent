# codedocent

**Code visualization for non-programmers.**

A docent is a guide who explains things to people who aren't experts. Codedocent does that for code.

> Google Translate for code → human understanding.

---

## What it does

Codedocent takes any codebase and turns it into a visual, navigable map that anyone can read — no programming knowledge required.

Every piece of code becomes a **block** that shows:
- A **plain English explanation** of what it does
- A **pseudocode translation** (simplified logic, not real syntax)
- **Collapsible imports** with a count label (e.g., `IMPORTS (14)`) — click to expand
- **Quality warnings** with explanatory text (complexity, line count, parameter count)
- The **actual source code** (hidden by default, expandable)

Blocks are **nested** — directories contain files, files contain classes, classes contain functions. Click to drill down. Breadcrumbs to navigate back up. Color-coded by language.

### Code actions

Every block gets a toolbar with one-click actions (no AI analysis needed):

| Button | What it does |
|--------|-------------|
| **Show Code** | Expand/collapse the source code inline |
| **Export Code** | Copy raw source to clipboard |
| **Copy for AI** | Copy source wrapped in a markdown code fence with context (block name, file path) — ready to paste into an AI assistant |
| **Replace Code** | Open an editor to paste modified code back into the source file |

**Replace Code** (available on functions, methods, and classes) lets you paste fixed or improved code — from an AI assistant, a code review, or your own edits — directly back into the original file. A `.bak` backup is created automatically before any write. The UI shows a confirmation step with success/error feedback, and all cached analysis is cleared so the block can be re-analyzed with the new code.

## Who it's for

You understand systems. You can read a schematic. You just can't read Python.

Codedocent is for project managers, founders, designers, analysts, auditors — anyone who needs to understand what a codebase does without learning to code.

## Quick start

### Requirements

- Python 3.10+
- [Ollama](https://ollama.com) installed and running
- A model pulled (e.g., `ollama pull gemma3:4b`)

### Install
```bash
git clone https://github.com/clanker-lover/codedocent.git
cd codedocent
pip install -e .
```

### Run

**Setup wizard** — just run `codedocent` with no arguments:
```bash
codedocent
```
The wizard walks you through picking a folder, detecting Ollama, choosing a model, and selecting a mode. No flags to memorize.

**Interactive mode** (recommended) — instant load, AI analyzes each block on click:
```bash
codedocent /path/to/any/codebase
```

Your browser opens automatically. Click any block to drill down and trigger AI analysis.

**Full analysis mode** — analyzes everything upfront, outputs a static HTML file:
```bash
codedocent /path/to/any/codebase --full
```

**Text mode** — quick tree overview, no AI:
```bash
codedocent /path/to/any/codebase --text
```

**GUI launcher** — a graphical window with folder picker, model dropdown, and mode selector:
```bash
codedocent --gui
# or use the standalone entry point:
codedocent-gui
```
Requires tkinter (usually included with Python; on Ubuntu: `sudo apt install python3-tk`).

### Options

| Flag | Description |
|------|-------------|
| *(no args)* | Launch interactive setup wizard |
| `--gui` | Open GUI launcher (tkinter) |
| `--full` | Analyze everything upfront, output static HTML |
| `--text` | Print text tree to terminal (no browser) |
| `--no-ai` | Skip AI summaries, show structure only |
| `--model MODEL` | Ollama model to use (default: `qwen3:14b`) |
| `--port PORT` | Port for interactive server (default: auto) |
| `--workers N` | Parallel AI workers for `--full` mode (default: 1) |
| `--output FILE` | Output filename for `--full` mode |

## Supported languages

Codedocent detects **23 file extensions** across these languages. Python and JavaScript/TypeScript get full AST parsing (functions, classes, methods, imports). All other languages get file-level analysis.

| Full parsing | File-level detection |
|-------------|---------------------|
| Python (.py) | C / C++ (.c, .cpp, .h, .hpp) |
| JavaScript (.js) | Rust (.rs) |
| TypeScript (.ts, .tsx) | Go (.go) |
| | Java (.java) |
| | Ruby (.rb) |
| | PHP (.php) |
| | Swift (.swift) |
| | Kotlin (.kt) |
| | Scala (.scala) |
| | HTML / CSS |
| | Config files (JSON, YAML, TOML) |

## How it works

**Interactive mode** starts a local server and opens your browser. The code tree loads instantly. When you click a block, it calls Ollama to analyze just that node — typically 1-2 seconds with a 4B model.

**Full mode** analyzes every node in priority order (directories → files → functions), with an optional `--workers` flag for parallel AI requests. Outputs a self-contained HTML file you can share.

All AI runs locally via Ollama. No data leaves your machine.

## AI models

Codedocent works with any model from the [Ollama library](https://ollama.com/library).

## Quality indicators

Each block shows a quality badge based on static analysis, with warnings that explain *why* — not just colored dots.

| Badge | Meaning |
|-------|---------|
| 🟢 Clean | Low complexity, no warnings |
| 🟡 Complex | Moderate complexity, long functions, or many parameters |
| 🔴 Warning | High complexity or very long code |

Warnings roll up through the tree: a file inherits the worst quality of its functions, and a directory inherits the worst quality of its files. Each level shows a count of problematic children (e.g., "Contains 2 high-risk functions"). Quality scoring works for all supported languages — Python files also get [radon](https://radon.readthedocs.io/) cyclomatic complexity analysis.

## Architecture

```
codedocent/
├── cli.py            Command-line interface, setup wizard, entry point
├── gui.py            Tkinter GUI launcher
├── ollama_utils.py   Shared Ollama detection and model listing
├── scanner.py        File discovery with .gitignore support
├── parser.py         AST parsing via tree-sitter
├── analyzer.py       AI summaries, quality scoring, caching
├── editor.py         Code replacement with backup safety
├── renderer.py       HTML generation (static + interactive)
├── server.py         Local server for interactive mode
└── templates/
    └── interactive.html   Single-page app UI
```

## Current status

- Scanner, parser, renderer, analyzer, editor, server, CLI — all built and tested
- Interactive setup wizard when run with no arguments
- GUI launcher via `--gui` flag or `codedocent-gui` entry point
- Interactive navigation with lazy AI analysis
- Code action buttons (Show Code, Export, Copy for AI, Replace) available immediately — no AI analysis required
- Static HTML full-analysis mode with parallel workers
- Code replacement with `.bak` backup and cache invalidation
- Quality scoring with two-tier thresholds and warning rollup across the tree
- pip-installable package with `codedocent` and `codedocent-gui` CLI entry points
- 96 tests passing
- Code quality: pylint 10/10, bandit/flake8/mypy all clean

## License

MIT

## Contributing

This project is in active early development. Issues and ideas welcome.
