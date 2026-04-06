# Codedocent Wiki

**Repository**: `~/codedocent/`
**Version**: 1.0.3
**Description**: Code visualization for non-programmers -- a fractal code comprehension system (Codestrata methodology)

## Summaries (one per source file)

### Core Package (`codedocent/`)
| Page | Module | Role | Lines |
|------|--------|------|-------|
| [scanner](summaries/scanner.md) | `scanner.py` | Foundation -- file discovery | 144 |
| [parser](summaries/parser.md) | `parser.py` | Foundation -- AST parsing, CodeNode tree | 392 |
| [analyzer](summaries/analyzer.md) | `analyzer.py` | Orchestrator -- AI analysis, caching | 677 |
| [quality](summaries/quality.md) | `quality.py` | Utility -- static quality scoring | 207 |
| [renderer](summaries/renderer.md) | `renderer.py` | Output -- HTML rendering (3 modes) | 95 |
| [server](summaries/server.md) | `server.py` | Infrastructure -- localhost HTTP server | 596 |
| [cloud_ai](summaries/cloud_ai.md) | `cloud_ai.py` | Integration -- cloud AI providers | 208 |
| [ollama_utils](summaries/ollama_utils.md) | `ollama_utils.py` | Utility -- Ollama connectivity | 32 |
| [graph](summaries/graph.md) | `graph.py` | Analysis -- dependency graph builder | 728 |
| [editor](summaries/editor.md) | `editor.py` | Infrastructure -- safe file replacement | 174 |
| [cli](summaries/cli.md) | `cli.py` | Entry point -- CLI and wizard | 439 |
| [gui](summaries/gui.md) | `gui.py` | Entry point -- Tkinter GUI launcher | 298 |
| [init](summaries/init.md) | `__init__.py` | Package marker | 1 |
| [main](summaries/main.md) | `__main__.py` | Entry point shim | 4 |

### Project Root
| Page | File | Role |
|------|------|------|
| [pyproject](summaries/pyproject.md) | `pyproject.toml` | Build config, dependencies |
| [benchmark](summaries/benchmark.md) | `benchmark.py` | Dev tool -- model benchmarking |

## Concepts (cross-cutting ideas)

| Page | Appears In |
|------|-----------|
| [CodeNode data model](concepts/codenode-data-model.md) | parser, analyzer, renderer, server, quality, graph, editor |
| [AI prompt design](concepts/ai-prompt-design.md) | analyzer, cloud_ai, graph |
| [Caching strategy](concepts/caching-strategy.md) | analyzer, server, editor |
| [Five execution modes](concepts/execution-modes.md) | cli, gui, server, renderer |
| [Security model](concepts/security-model.md) | server, editor, cloud_ai, renderer |
| [AI backend routing](concepts/ai-backend-routing.md) | analyzer, cloud_ai, ollama_utils, cli, gui |
| [Architecture mode](concepts/architecture-mode.md) | graph, server, renderer, cli |
| [Rendering pipeline](concepts/rendering-pipeline.md) | renderer, server, cli |
| [Quality scoring pipeline](concepts/quality-scoring.md) | quality, analyzer, graph |
| [Four-level drill-down](concepts/four-level-drilldown.md) | graph, server, parser |
| [Test architecture](concepts/test-architecture.md) | all test files |

## Entities (tools, libraries, dependencies)

| Page | Type | Used By |
|------|------|---------|
| [tree-sitter](entities/tree-sitter.md) | External dependency | parser, quality, graph |
| [Ollama](entities/ollama.md) | External dependency/service | analyzer, ollama_utils, cli, gui, benchmark |
| [radon](entities/radon.md) | External dependency | quality |
| [Jinja2](entities/jinja2.md) | External dependency | renderer |
| [pathspec](entities/pathspec.md) | External dependency | scanner |
| [D3.js](entities/d3js.md) | Frontend dependency | architecture.html template |

## Architecture Overview

```
User -> CLI (cli.py) -> Scanner (scanner.py) -> Parser (parser.py) -> CodeNode tree
                                                                          |
                          +-----------------------------------------------+
                          |                    |                           |
                   Analyzer (analyzer.py)  Quality (quality.py)    Graph (graph.py)
                     |           |                                        |
              Ollama (local)  Cloud AI (cloud_ai.py)                      |
                          |                    |                           |
                          +-----------------------------------------------+
                                               |
                          +--------------------+--------------------+
                          |                    |                    |
                   Renderer (renderer.py) Server (server.py)  Editor (editor.py)
                          |                    |
                    Static HTML         Interactive Web App
```

## Data Flow

1. **Scan**: `scanner.py` walks the directory, produces `list[ScannedFile]`
2. **Parse**: `parser.py` builds a `CodeNode` tree from scanned files via tree-sitter
3. **Score**: `quality.py` scores complexity and parameter counts
4. **Analyze**: `analyzer.py` sends code to AI (Ollama or cloud), caches results
5. **Graph**: `graph.py` resolves imports and builds dependency graphs
6. **Render**: `renderer.py` produces HTML via Jinja2 templates
7. **Serve**: `server.py` runs localhost server for interactive browsing
8. **Edit**: `editor.py` writes modified code back with safe backups

## Dependency Graph (internal modules)

```
cli.py -----> scanner.py
  |---------> parser.py
  |---------> analyzer.py -----> quality.py
  |               |-----------> graph.py -----> parser.py
  |               |-----------> cloud_ai.py
  |               |-----------> ollama (external)
  |---------> renderer.py -----> server.py (cyclic, deferred)
  |---------> server.py -------> analyzer.py
  |               |-----------> renderer.py (cyclic, deferred)
  |               |-----------> editor.py
  |               |-----------> graph.py
  |---------> cloud_ai.py
  |---------> ollama_utils.py
  |---------> gui.py (deferred)
gui.py -----> cloud_ai.py
  |---------> ollama_utils.py
```
