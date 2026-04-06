# AI Prompt Design

**Cross-cutting concept appearing in**: [analyzer.py](../summaries/analyzer.md), [cloud_ai.py](../summaries/cloud_ai.md), [graph.py](../summaries/graph.md)

## Facts

The AI prompt in `_build_prompt` (source: analyzer.py:45-117) is designed for a specific audience: "someone who can read schematics but not source code." The prompt requests four structured sections:

1. **ROLE** -- What job does this code do in the system? (1-2 sentences)
2. **SUMMARY** -- What does it receive, produce, and who cares? (2-4 sentences)
3. **KEY CONCEPTS** -- Main functions, classes, data structures (3-5 bullet items)
4. **PSEUDOCODE** -- Simplified plain-English version of main logic

The prompt includes dependency context when available (source: analyzer.py:63-68):
- "This file imports from: scanner.py, parser.py"
- "This file is imported by: cli.py, server.py"

This context comes from [graph.py](../summaries/graph.md)'s `get_file_dependencies` function.

Source code is truncated to 300 lines maximum before inclusion (source: analyzer.py:28, 56-58). A `/no_think` suffix is appended for Qwen3 models to suppress chain-of-thought output (source: analyzer.py:114-116).

Response parsing in `_parse_ai_response` (source: analyzer.py:132-179) uses regex to extract each section. ROLE and SUMMARY are merged into a single summary field. Falls back to using the first line of text if no markers are found.

Think-tag stripping handles `<think>`, `<|think|>`, and unclosed variants (source: analyzer.py:120-129).

## Inferences

The structured four-section format is an attempt to get deterministic, parseable output from non-deterministic language models. The fallback logic suggests this sometimes fails -- the system is designed to degrade gracefully rather than crash.

The dependency context injection is a significant design choice: it gives the AI model awareness of where a file sits in the system, enabling it to produce more accurate role descriptions.

## Open Questions

- Temperature is fixed at 0.3 (source: cloud_ai.py:128) -- no user control over creativity vs consistency
- max_tokens is 1024 (source: cloud_ai.py:129) -- may be insufficient for large, complex files
