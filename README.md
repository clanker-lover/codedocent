codedocent
Code visualization for non-programmers.
A docent is a guide who explains things to people who aren't experts. Codedocent does that for code.

Google Translate for code → human understanding.


What it does
Codedocent takes any codebase and turns it into a visual, navigable map that anyone can read — no programming knowledge required.
Every piece of code becomes a block that shows:

A plain English explanation of what it does
A pseudocode translation (simplified logic, not real syntax)
Quality warnings (complexity, security, style issues)
The actual source code (hidden by default, expandable)

Blocks are nested — directories contain files, files contain classes, classes contain functions. Click to drill down. Breadcrumbs to navigate back up. Color-coded by language.
┌──────────────────────────────────────────────────┐
│ 📁 my-project/                                   │
├──────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────────┐  ┌──────────────┐              │
│  │ server.py    │  │ auth.py      │              │
│  │ ───────────  │  │ ───────────  │              │
│  │ Handles HTTP │  │ Manages user │              │
│  │ requests and │  │ login and    │              │
│  │ routes them  │  │ sessions...  │              │
│  │ to handlers  │  │              │              │
│  │ 🟢 Clean     │  │ 🟡 Complex   │              │
│  └──────────────┘  └──────────────┘              │
└──────────────────────────────────────────────────┘
Who it's for
You understand systems. You can read a schematic. You just can't read Python.
Codedocent is for project managers, founders, designers, analysts, auditors — anyone who needs to understand what a codebase does without learning to code.

Getting started
What you'll need
Codedocent runs on your computer and uses a local AI model to read and explain code. Nothing gets sent to the cloud — everything stays on your machine.
You need three things installed:

Python 3.10 or newer — Download Python. During installation on Windows, check the box that says "Add Python to PATH."
Git — Download Git. This is a tool developers use to download code. You only need it once.
Ollama — Download Ollama. This runs AI models locally on your computer. Install it and make sure it's running (you should see the llama icon in your system tray or menu bar).

Step 1: Download codedocent
Open a terminal (on Mac: search for "Terminal"; on Windows: search for "Command Prompt" or "PowerShell") and paste this:
bashgit clone https://github.com/clanker-lover/codedocent.git
cd codedocent
pip install -e .
Step 2: Download an AI model
Still in the terminal, paste this to download a small, fast AI model:
bashollama pull gemma3:4b
This downloads about 3 GB. It only needs to happen once. If you have a powerful computer (16+ GB RAM, dedicated GPU), you can try larger models later for better quality explanations — see Choosing a model below.
Step 3: Point it at code
bashcodedocent /path/to/any/codebase
Replace /path/to/any/codebase with the actual folder location. Your browser will open automatically with the interactive map. Click any block to see its AI-generated explanation.
That's it. You're reading code.

How to use it
Codedocent has two main ways to work:
Interactive mode (default)
bashcodedocent /path/to/code
Opens your browser immediately. The code tree loads instantly with no waiting. When you click on a block, the AI analyzes just that one piece — usually takes 1-3 seconds. This is the best way to explore a codebase, because you only wait for the parts you're actually looking at.
Full analysis mode
bashcodedocent /path/to/code --full
Analyzes every single block in the codebase upfront and saves the result as an HTML file. This takes longer (anywhere from 2-30 minutes depending on codebase size and your computer), but gives you a complete, self-contained file you can open anytime, share with others, or read offline — no server needed.
Quick tree view
bashcodedocent /path/to/code --text
Prints a simple outline of the codebase to your terminal. No AI, no browser — just a fast look at the structure.

All options
You control codedocent by adding flags after the command. Here's every option:
FlagWhat it doesExample--fullAnalyze everything upfront, save as HTML filecodedocent ./mycode --full--textPrint a quick text tree (no AI, no browser)codedocent ./mycode --text--no-aiShow code structure without AI explanationscodedocent ./mycode --no-ai--model NAMEChoose which AI model to usecodedocent ./mycode --model gemma3:4b--workers NRun N AI analyses at the same time (for --full)codedocent ./mycode --full --workers 2--port PORTSet a specific port for the interactive servercodedocent ./mycode --port 9000--output FILESet the output filename (for --full)codedocent ./mycode --full --output report.html
Combining options
You can mix and match. Some examples:
bash# Full analysis with a fast model and 2 parallel workers
codedocent ./mycode --full --model gemma3:4b --workers 2

# Interactive mode with a high-quality model
codedocent ./mycode --model qwen3:14b

# Just see the structure, no AI needed
codedocent ./mycode --text --no-ai

Choosing a model
Codedocent works with any model available through Ollama. The model determines the quality and speed of the English explanations and pseudocode. Here are some we've tested:
ModelDownloadSpeed per blockQualityBest forgemma3:4b~3 GB1-3 secondsGoodInteractive browsing, modest hardwareqwen3:8b~5 GB3-8 secondsBetterGood balance of speed and qualityqwen3:14b~9 GB5-15 secondsVery goodFull analysis when you have timeqwen3:32b~20 GB30-60 secondsBestFinal quality pass, powerful hardware
Our recommendation: Start with gemma3:4b. It's fast and produces clear, accurate explanations. If you want richer detail and have the hardware for it, try a larger model in --full mode while you do something else.
To download a new model:
bashollama pull qwen3:14b
To use it:
bashcodedocent ./mycode --model qwen3:14b
You can use any model from the Ollama library — not just the ones listed above. If you have a favorite model, try it.
About the --workers flag
When using --full mode, codedocent normally analyzes one block at a time. The --workers flag lets it analyze multiple blocks simultaneously, which can speed things up if your hardware can handle it.

--workers 1 — one at a time (safest, works on any computer)
--workers 2 — two at once (usually a modest speedup)
--workers 4 — four at once (only helps if you have a powerful GPU)

If you set workers too high for your computer, it won't crash — it'll just stop getting faster. Start with 2 and see if it helps.

Supported languages
Codedocent detects 23 file extensions. Python and JavaScript/TypeScript get full structural parsing (functions, classes, methods, imports). All other languages get file-level analysis with AI summaries.
Full parsingDetected (file-level AI)Python (.py)C / C++ (.c, .cpp, .h, .hpp)JavaScript (.js)Rust (.rs)TypeScript (.ts, .tsx)Go (.go)Java (.java)Ruby (.rb)PHP (.php)Swift (.swift)Kotlin (.kt)Scala (.scala)HTML / CSSConfig (JSON, YAML, TOML)

Quality indicators
Each block shows a quality badge based on static analysis:
BadgeMeaning🟢 CleanLow complexity, no issues found🟡 ComplexModerate complexity or style concerns🔴 WarningHigh complexity, multiple issues
Warnings include things like: high cyclomatic complexity, functions that are too long, functions with too many parameters.

How it works under the hood
codedocent /path/to/code
       │
       ▼
┌──────────────────────────┐
│ 1. SCANNER               │
│ Walk directory tree       │
│ Detect languages          │
│ Respect .gitignore        │
└──────────────────────────┘
       │
       ▼
┌──────────────────────────┐
│ 2. PARSER                │
│ Tree-sitter AST extract   │
│ Build CodeNode tree       │
└──────────────────────────┘
       │
       ├── interactive ──▶ Local server, AI on-demand per click
       │
       └── --full ───────▶ Batch AI analysis → static HTML file
All AI runs locally through Ollama. Your code never leaves your machine.

Current status
Phase 4 of 8 complete — working MVP.

✅ Scanner, parser, renderer, analyzer, server, CLI
✅ 50 tests passing
✅ Interactive navigation with lazy AI analysis
✅ Static full-analysis mode with parallel workers
🔲 Code export for AI assistance (Phase 5)
🔲 Surgical code replacement (Phase 7)
🔲 Easy install via pip (Phase 8)


License
MIT
Contributing
This project is in active early development. Issues and ideas welcome.
