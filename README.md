# codedocent

Code visualization for non-programmers.

A docent is a guide who explains things to people who aren't experts. Codedocent does that for code.

## What it does

Codedocent takes any codebase and turns it into a visual, navigable map that anyone can read — no programming knowledge required.

Every piece of code becomes a block that shows a plain English explanation of what it does, a pseudocode translation (simplified logic, not real syntax), quality warnings (complexity, security, style issues), and the actual source code (hidden by default, expandable).

Blocks are nested — directories contain files, files contain classes, classes contain functions. Click to drill down. Breadcrumbs to navigate back up. Color-coded by language.

### Who it's for

Project managers, founders, designers, analysts, auditors — anyone who needs to understand what a codebase does without learning to code.

## Getting started

### What you'll need

Codedocent runs on your computer and uses a local AI model to read and explain code. Nothing gets sent to the cloud — everything stays on your machine.

You need three things installed:

- **Python 3.10 or newer** — download from python.org. On Windows, check the box that says "Add Python to PATH" during installation.
- **Git** — download from git-scm.com. This is used to download code. You only need it once.
- **Ollama** — download from ollama.com. This runs AI models locally on your computer. Install it and make sure it's running (you should see the llama icon in your system tray or menu bar).

### Step 1: Download codedocent

Open a terminal (on Mac: search for "Terminal"; on Windows: search for "Command Prompt" or "PowerShell") and paste these three lines one at a time:

```
git clone https://github.com/clanker-lover/codedocent.git
cd codedocent
pip install -e .
```

### Step 2: Download an AI model

Still in the terminal, paste this:

```
ollama pull gemma3:4b
```

This downloads about 3 GB. It only happens once.

### Step 3: Point it at code

```
codedocent /path/to/any/codebase
```

Replace `/path/to/any/codebase` with the actual folder location. Your browser opens automatically. Click any block to see its AI-generated explanation.

That's it. You're reading code.

## How to use it

### Interactive mode (default)

```
codedocent /path/to/code
```

Opens your browser immediately. The code tree loads instantly. When you click a block, the AI analyzes just that piece — usually 1-3 seconds. Best way to explore.

### Full analysis mode

```
codedocent /path/to/code --full
```

Analyzes every block upfront and saves a static HTML file. Takes 2-30 minutes depending on codebase size and your computer. The result is a self-contained file you can open anytime, share with others, or read offline.

### Quick tree view

```
codedocent /path/to/code --text
```

Prints a simple outline to your terminal. No AI, no browser — just a fast look at the structure.

### All options

| Flag | What it does | Example |
|------|-------------|---------|
| `--full` | Analyze everything upfront, save as HTML file | `codedocent ./mycode --full` |
| `--text` | Print a quick text tree, no AI, no browser | `codedocent ./mycode --text` |
| `--no-ai` | Show code structure without AI explanations | `codedocent ./mycode --no-ai` |
| `--model NAME` | Choose which AI model to use | `codedocent ./mycode --model gemma3:4b` |
| `--workers N` | Run N AI analyses at the same time (for `--full`) | `codedocent ./mycode --full --workers 2` |
| `--port PORT` | Set a specific port for the interactive server | `codedocent ./mycode --port 9000` |
| `--output FILE` | Set the output filename (for `--full`) | `codedocent ./mycode --full --output report.html` |

You can combine flags. For example:

```
codedocent ./mycode --full --model gemma3:4b --workers 2
```

## Choosing a model

Codedocent works with any model from the Ollama library. The model determines the quality and speed of the explanations. Here's what we've tested:

| Model | Download size | Speed per block | Quality | Best for |
|-------|--------------|-----------------|---------|----------|
| gemma3:4b | ~3 GB | 1-3 seconds | Good | Interactive browsing, modest hardware |
| qwen3:8b | ~5 GB | 3-8 seconds | Better | Balance of speed and quality |
| qwen3:14b | ~9 GB | 5-15 seconds | Very good | Full analysis when you have time |
| qwen3:32b | ~20 GB | 30-60 seconds | Best | Final quality pass, powerful hardware |

Recommendation: Start with gemma3:4b. If you want richer detail and have the hardware, try a larger model in `--full` mode while you do something else.

To download a different model: `ollama pull qwen3:14b`

To use it: `codedocent ./mycode --model qwen3:14b`

You can use any model from ollama.com/library — not just these. If you have a favorite, try it.

### About --workers

In `--full` mode, codedocent normally analyzes one block at a time. The `--workers` flag lets it analyze multiple blocks simultaneously. Start with 2 and see if it helps. If you set it too high, it won't crash — it just stops getting faster.

## Supported languages

Python and JavaScript/TypeScript get full structural parsing — functions, classes, methods, and imports are broken out individually. All other languages get file-level analysis with AI summaries.

- **Full parsing:** Python, JavaScript, TypeScript
- **File-level detection (23 extensions):** C, C++, Rust, Go, Java, Ruby, PHP, Swift, Kotlin, Scala, HTML, CSS, JSON, YAML, TOML, and more.

## Quality indicators

Each block shows a quality badge based on static analysis:

| Badge | Meaning |
|-------|---------|
| 🟢 Clean | Low complexity, no issues found |
| 🟡 Complex | Moderate complexity or style concerns |
| 🔴 Warning | High complexity, multiple issues |

## How it works

All AI runs locally through Ollama. Your code never leaves your machine.

In interactive mode, a local server starts and your browser opens. The code tree loads instantly. Clicking a block sends just that piece to your local AI model for analysis.

In full mode, every block is analyzed in priority order (directories first, then files, then functions) and the result is saved as a standalone HTML file.

## Current status

Phase 4 of 8 complete — working MVP.

**Done:** Scanner, parser, renderer, analyzer, server, CLI. 50 tests passing. Interactive navigation with lazy AI. Static full-analysis mode with parallel workers.

**Next:** Code export for AI assistance. Surgical code replacement. Easy install via pip.

## License

MIT

## Contributing

Early development. Issues and ideas welcome.
