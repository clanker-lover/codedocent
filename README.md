# codedocent

**Code visualization for non-programmers.**

A docent is a guide who explains complex things to non-experts. Codedocent does that for code.

---

## What it does

Codedocent transforms any codebase into an interactive visual map. No programming knowledge required.

Each piece of code becomes a **block** containing:
- A plain English explanation of what it does
- A pseudocode translation (logic without syntax)
- Quality warnings (complexity, security, style)
- The actual source code (hidden by default)

Blocks are nested like a schematic — directories contain files, files contain classes, classes contain functions. Click to drill down. Breadcrumbs to navigate back up.

---

## Who it's for

Project managers, founders, designers, analysts, auditors — anyone who needs to understand a codebase without learning to code.

---

## Installation

**Requirements:**
- Python 3.10+
- [Ollama](https://ollama.com) (runs AI models locally)
```bash
git clone https://github.com/clanker-lover/codedocent.git
cd codedocent
pip install -e .
ollama pull gemma3:4b
```

---

## Usage

**Interactive mode** (default) — opens in browser, analyzes on-demand:
```bash
codedocent /path/to/code
```

**Full analysis** — analyzes everything upfront, outputs static HTML:
```bash
codedocent /path/to/code --full
```

**Text outline** — quick structure view, no AI:
```bash
codedocent /path/to/code --text
```

---

## Options

| Flag | Description |
|------|-------------|
| `--full` | Analyze all blocks upfront, save as HTML |
| `--text` | Print text outline only |
| `--no-ai` | Show structure without AI analysis |
| `--model NAME` | Select Ollama model (default: gemma3:4b) |
| `--workers N` | Parallel AI requests for `--full` mode |
| `--port PORT` | Set server port for interactive mode |
| `--output FILE` | Set output filename for `--full` mode |

---

## Supported Languages

**Full parsing:** Python, JavaScript, TypeScript

**File-level analysis:** C, C++, Rust, Go, Java, Ruby, PHP, Swift, Kotlin, Scala, HTML, CSS, JSON, YAML, TOML (23 extensions total)

---

## How it works

All AI runs locally through Ollama. Your code never leaves your machine.

Interactive mode starts a local server and opens your browser. The code tree loads instantly. Clicking a block triggers on-demand AI analysis.

Full mode analyzes every block in priority order and outputs a standalone HTML file.

---

## Status

**Phase 4 of 8 complete.**

✅ Scanner, parser, renderer, analyzer, server, CLI  
✅ 50 tests passing  
✅ Interactive navigation with lazy analysis  
✅ Static full-analysis mode with parallel workers  

🔲 Code export for AI assistance  
🔲 Surgical code replacement  
🔲 pip packaging  

---

## License

MIT
