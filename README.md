codedocent
Code visualization for non-programmers.
A docent is a guide who explains things to people who aren't experts. Codedocent does that for code.

What it does
Codedocent takes any codebase and turns it into a visual, navigable map that anyone can read — no programming knowledge required.
Every piece of code becomes a block that shows a plain English explanation of what it does, a pseudocode translation (simplified logic, not real syntax), quality warnings (complexity, security, style issues), and the actual source code (hidden by default, expandable).
Blocks are nested — directories contain files, files contain classes, classes contain functions. Click to drill down. Breadcrumbs to navigate back up. Color-coded by language.
Who it's for
Project managers, founders, designers, analysts, auditors — anyone who needs to understand what a codebase does without learning to code.

Getting started
What you'll need
Codedocent runs on your computer and uses a local AI model to read and explain code. Nothing gets sent to the cloud — everything stays on your machine.
You need three things installed:

Python 3.10 or newer — download from python.org. On Windows, check the box that says "Add Python to PATH" during installation.
Git — download from git-scm.com. This is used to download code. You only need it once.
Ollama — download from ollama.com. This runs AI models locally on your computer. Install it and make sure it's running (you should see the llama icon in your system tray or menu bar).

Step 1: Download codedocent
Open a terminal (on Mac: search for "Terminal"; on Windows: search for "Command Prompt" or "PowerShell") and paste these three lines one at a time:
git clone https://github.com/clanker-lover/codedocent.git
cd codedocent
pip install -e .
Step 2: Download an AI model
Still in the terminal, paste this:
ollama pull gemma3:4b
This downloads about 3 GB. It only happens once.
Step 3: Point it at code
codedocent /path/to/any/codebase
Replace /path/to/any/codebase with the actual folder location. Your browser opens automatically. Click any block to see its AI-generated explanation.
That's it. You're reading code.

How to use it
Interactive mode (default)
codedocent /path/to/code
Opens your browser immediately. The code tree loads instantly. When you click a block, the AI analyzes just that piece — usually 1-3 seconds. Best way to explore.
Full analysis mode
codedocent /path/to/code --full
Analyzes every block upfront and saves a static HTML file. Takes 2-30 minutes depending on codebase size and your computer. The result is a self-contained file you can open anytime, share with others, or read offline.
Quick tree view
codedocent /path/to/code --text
Prints a simple outline to your terminal. No AI, no browser — just a fast look at the structure.

All options
FlagWhat it doesExample--fullAnalyze everything upfront, save as HTML filecodedocent ./mycode --full--textPrint a quick text tree, no AI, no browsercodedocent ./mycode --text--no-aiShow code structure without AI explanationscodedocent ./mycode --no-ai--model NAMEChoose which AI model to usecodedocent ./mycode --model gemma3:4b--workers NRun N AI analyses at the same time (for --full)codedocent ./mycode --full --workers 2--port PORTSet a specific port for the interactive servercodedocent ./mycode --port 9000--output FILESet the output filename (for --full)codedocent ./mycode --full --output report.html
You can combine flags. For example:
codedocent ./mycode --full --model gemma3:4b --workers 2

Choosing a model
Codedocent works with any model from the Ollama library. The model determines the quality and speed of the explanations. Here's what we've tested:
ModelDownload sizeSpeed per blockQualityBest forgemma3:4b~3 GB1-3 secondsGoodInteractive browsing, modest hardwareqwen3:8b~5 GB3-8 secondsBetterBalance of speed and qualityqwen3:14b~9 GB5-15 secondsVery goodFull analysis when you have timeqwen3:32b~20 GB30-60 secondsBestFinal quality pass, powerful hardware
Recommendation: Start with gemma3:4b. If you want richer detail and have the hardware, try a larger model in --full mode while you do something else.
To download a different model: ollama pull qwen3:14b
To use it: codedocent ./mycode --model qwen3:14b
You can use any model from ollama.com/library — not just these. If you have a favorite, try it.
About --workers
In --full mode, codedocent normally analyzes one block at a time. The --workers flag lets it analyze multiple blocks simultaneously. Start with 2 and see if it helps. If you set it too high, it won't crash — it just stops getting faster.

Supported languages
Python and JavaScript/TypeScript get full structural parsing — functions, classes, methods, and imports are broken out individually. All other languages get file-level analysis with AI summaries.
Full parsing: Python, JavaScript, TypeScript
File-level detection (23 extensions): C, C++, Rust, Go, Java, Ruby, PHP, Swift, Kotlin, Scala, HTML, CSS, JSON, YAML, TOML, and more.

Quality indicators
Each block shows a quality badge based on static analysis:
BadgeMeaning🟢 CleanLow complexity, no issues found🟡 ComplexModerate complexity or style concerns🔴 WarningHigh complexity, multiple issues

How it works
All AI runs locally through Ollama. Your code never leaves your machine.
In interactive mode, a local server starts and your browser opens. The code tree loads instantly. Clicking a block sends just that piece to your local AI model for analysis.
In full mode, every block is analyzed in priority order (directories first, then files, then functions) and the result is saved as a standalone HTML file.

Current status
Phase 4 of 8 complete — working MVP.
Done: Scanner, parser, renderer, analyzer, server, CLI. 50 tests passing. Interactive navigation with lazy AI. Static full-analysis mode with parallel workers.
Next: Code export for AI assistance. Surgical code replacement. Easy install via pip.

License
MIT
Contributing
Early development. Issues and ideas welcome.
