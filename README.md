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
- **Quality warnings** (complexity, security, style issues)
- The **actual source code** (hidden by default, expandable)

Blocks are **nested** — directories contain files, files contain classes, classes contain functions. Click to drill down. Breadcrumbs to navigate back up. Color-coded by language.

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

### Options

| Flag | Description |
|------|-------------|
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

Each block shows a quality badge based on static analysis:

| Badge | Meaning |
|-------|---------|
| 🟢 Clean | Low complexity, no warnings |
| 🟡 Complex | Moderate complexity or style warnings |
| 🔴 Warning | High complexity, many issues |

## Current status

**Phase 5 of 8 complete — working MVP.**

- ✅ Scanner, parser, renderer, analyzer, server, CLI — all built and tested
- ✅ Code export with Show Code, Export Code, and Copy for AI buttons
- ✅ 57 tests passing
- ✅ Interactive navigation with lazy AI analysis
- ✅ Static HTML full-analysis mode
- ✅ Parallel workers for batch analysis
- ✅ Code export — Show Code, Export Code, Copy for AI (Phase 5)
- 🔲 Code replacement (Phase 7)
- 🔲 pip packaging (Phase 8)

## License

MIT

## Contributing

This project is in active early development. Issues and ideas welcome.
