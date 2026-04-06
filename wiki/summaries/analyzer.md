# analyzer.py

**Source**: `codedocent/analyzer.py`
**Lines**: 677

## What It Does

Orchestrates AI-powered analysis of the CodeNode tree. Builds prompts, calls Ollama or cloud AI providers, parses structured responses, manages a JSON cache, and handles quality scoring delegation. This is the largest module and the core intelligence layer.

## Facts

- Prompt asks AI to produce four sections: ROLE, SUMMARY, KEY CONCEPTS, PSEUDOCODE (source: analyzer.py:45-117)
- Includes dependency context in prompts when available: "This file imports from: X" / "This file is imported by: Y" (source: analyzer.py:63-68)
- Source code is truncated to 300 lines max (`MAX_SOURCE_LINES`) before sending to AI (source: analyzer.py:28, 56-58)
- Files under 3 lines (`MIN_LINES_FOR_AI`) skip AI analysis entirely (source: analyzer.py:29)
- Appends `/no_think` to prompts for Qwen3 models (source: analyzer.py:114-116)
- Strips `<think>...</think>` and `<|think|>...<|/think|>` tags from model output (source: analyzer.py:120-129)
- AI call timeout is 180 seconds (source: analyzer.py:182)
- Cache is stored as `.codedocent_cache.json` in the project root, keyed by filepath + name + MD5 of source (source: analyzer.py:27, 271-274)
- Cache is invalidated when the model changes (source: analyzer.py:384-386)
- Cache writes are atomic via temp file + `os.replace` (source: analyzer.py:289-318)
- Full analysis runs in 4 phases: quality scoring, quality rollup, AI batch analysis, directory summarization (source: analyzer.py:596-649)
- Supports parallel AI workers via `ThreadPoolExecutor` (source: analyzer.py:471-483)
- `assign_node_ids` generates 12-char hex IDs from MD5 hashes of node paths (source: analyzer.py:325-342)

## Public API

- `analyze(root, model, workers, ai_config) -> CodeNode` -- full tree analysis with AI
- `analyze_no_ai(root) -> CodeNode` -- quality scoring only, no AI calls
- `analyze_single_node(node, model, cache_dir, ai_config, deps)` -- on-demand analysis of one node (used by server)
- `assign_node_ids(root) -> dict[str, CodeNode]` -- assigns unique IDs, returns lookup dict

## Dependencies

- `ollama` (external, optional) -- local AI inference
- [parser](parser.md) -- consumes `CodeNode`
- [quality](quality.md) -- delegates quality scoring
- [graph](graph.md) -- imports dependency context builder
- [cloud_ai](cloud_ai.md) -- delegates cloud AI calls

## Architecture Role

Orchestrator. Sits between the raw parsed tree and the rendered output. Both [server](server.md) (interactive mode) and [CLI](cli.md) (full mode) invoke the analyzer.

See also: [AI prompt design](../concepts/ai-prompt-design.md), [caching strategy](../concepts/caching-strategy.md), [Ollama](../entities/ollama.md)
