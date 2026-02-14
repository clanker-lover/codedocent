# codedocent

<img width="1658" height="2158" alt="Screenshot_2026-02-09_13-17-06" src="https://github.com/user-attachments/assets/ff097ead-69ec-4618-b7b7-2b99c60ac57e" />

**Code visualization for non-programmers.**

A docent is a guide who explains things to people who aren't experts. Codedocent does that for code.

## The problem

You're staring at a codebase you didn't write — maybe thousands of files across dozens of directories — and you need to understand what it does. Reading every file isn't realistic. You need a way to visualize the code structure, get a high-level map of what's where, and drill into the parts that matter without losing context.

Codedocent parses the codebase into a navigable, visual block structure and explains each piece in plain English. It's an AI code analysis tool — use a cloud provider for speed or run locally through Ollama for full privacy. Point it at any codebase and get a structural overview you can explore interactively, understand quickly, and share as a static HTML file.

## Who this is for

- **Developers onboarding onto an unfamiliar codebase** — get oriented in minutes instead of days
- **Non-programmers** (managers, designers, PMs) who need to understand what code does without reading it
- **Solo developers inheriting legacy code** — map out the structure before making changes
- **Code reviewers** who want a high-level overview before diving into details
- **Security reviewers** who need a structural map of an application
- **Students** learning to read and navigate real-world codebases

## What you see

Nested, color-coded blocks representing directories, files, classes, and functions — the entire structure of a codebase laid out visually. Each block shows a plain English summary, a pseudocode translation, and quality warnings (green/yellow/red). Click any block to drill down; breadcrumbs navigate you back up. You can export code from any block or paste replacement code back into the source file. AI explanations come from your choice of cloud provider or local Ollama.

## Install

```bash
pip install codedocent
```

Requires Python 3.10+. Cloud AI needs an API key set in an env var (e.g. `OPENAI_API_KEY`). Local AI needs [Ollama](https://ollama.com) running. `--no-ai` skips AI entirely.

## Quick start

```bash
codedocent                         # setup wizard — walks you through everything
codedocent /path/to/code           # interactive mode (recommended)
codedocent /path/to/code --full    # full analysis, static HTML output
codedocent --gui                   # graphical launcher
codedocent /path/to/code --cloud openai    # use OpenAI
codedocent /path/to/code --cloud groq      # use Groq
codedocent /path/to/code --cloud custom --endpoint https://my-llm/v1/chat/completions
```

## How it works

Parses code structure with tree-sitter, scores quality with static analysis, and sends individual blocks to a cloud AI provider or local Ollama model for plain English summaries and pseudocode. Interactive mode analyzes on click — typically 1-2 seconds per block. Full mode analyzes everything upfront into a self-contained HTML file you can share.

## AI options

- **Cloud AI** — send code to OpenAI, OpenRouter, Groq, or any OpenAI-compatible endpoint. Fast, no local setup. Your code is sent to that service. API keys are read from env vars (`OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `GROQ_API_KEY`, `CODEDOCENT_API_KEY` for custom endpoints).
- **Local AI** — [Ollama](https://ollama.com) on your machine. Code never leaves your laptop. No API keys, no accounts.
- **No AI** (`--no-ai`) — structure and quality scores only.

The setup wizard (`codedocent` with no args) walks you through choosing.

## Supported languages

Full AST parsing for Python and JavaScript/TypeScript (functions, classes, methods, imports). File-level detection for 23 extensions including C, C++, Rust, Go, Java, Ruby, PHP, Swift, Kotlin, Scala, HTML, CSS, and config formats.

## License

MIT
