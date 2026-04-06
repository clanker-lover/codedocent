# Caching Strategy

**Cross-cutting concept appearing in**: [analyzer.py](../summaries/analyzer.md), [server.py](../summaries/server.md), [editor.py](../summaries/editor.md)

## Facts

Codedocent caches AI analysis results to avoid re-analyzing unchanged code.

**Cache format** (source: analyzer.py:277-286):
- JSON file named `.codedocent_cache.json` in the project root
- Schema: `{"version": 1, "model": "<model-id>", "entries": {...}}`
- Each entry keyed by `filepath::name::md5(source)` (source: analyzer.py:271-274)

**Cache invalidation**:
- Entire cache is reset when the model changes (source: analyzer.py:384-386)
- Model ID for cloud providers is `cloud:provider:model` (e.g., `cloud:openai:gpt-4.1-nano`) (source: analyzer.py:259-263)
- Individual entries are invalidated when source code changes (MD5 hash changes) (source: analyzer.py:271-274)
- Code replacement explicitly removes the old cache entry (source: server.py:83-104)

**Atomic writes** (source: analyzer.py:289-318):
- Cache is written to a temp file first, then moved into place via `os.replace`
- Temp file is fsynced before rename
- Leftover temp files are cleaned up on failure

**Cache in interactive mode**:
- `analyze_single_node` reads/writes cache per-request (source: analyzer.py:350-418)
- A threading lock prevents concurrent cache corruption (source: server.py:176)

## Inferences

The cache key includes an MD5 of the source, so editing a file automatically invalidates its cache entry without explicit tracking. This is a clean design that avoids stale data.

The model-level invalidation (resetting the entire cache on model change) is aggressive but safe -- it ensures summaries are always from the same model.

## Open Questions

- No cache size limits -- very large projects could produce large cache files
- No cache expiration -- old entries persist forever as long as source doesn't change
- The benchmark tool deletes the cache between runs (source: benchmark.py:26-29), confirming cache is performance-critical
