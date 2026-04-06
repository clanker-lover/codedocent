# benchmark.py

**Source**: `benchmark.py` (project root)
**Type**: Development tool
**Lines**: 158

## What It Does

Benchmarks codedocent `--full` mode across multiple Ollama models and worker counts. Pulls models, runs analysis with cache cleared between runs, parses timing output, and produces a results table.

## Facts

- Tests three models by default: `gemma3:4b` (1,2,4,8 workers), `qwen3:8b` (1,2,4 workers), `gemma3:12b` (1,2 workers) (source: benchmark.py:15-19)
- 10-minute timeout per benchmark run (source: benchmark.py:10)
- Deletes `.codedocent_cache.json` before each run to ensure cold starts (source: benchmark.py:26-29)
- Parses "Analysis complete: N nodes in Xs" from stderr to extract timing (source: benchmark.py:21-22)
- Skips remaining worker counts for a model if any run fails or times out (source: benchmark.py:129-140)
- Results saved to `benchmark_results.txt` (source: benchmark.py:11)
- Auto-pulls models via `ollama pull` if not already pulled (source: benchmark.py:32-40)

## Public API

- `main()` -- runs the full benchmark suite

## Dependencies

- Requires `ollama` CLI tool installed and running
- Invokes codedocent via subprocess

## Architecture Role

Development/testing tool. Not part of the installed package. Used to evaluate model and parallelism performance.
