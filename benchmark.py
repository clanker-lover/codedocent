#!/usr/bin/env python3
"""Benchmark codedocent --full across models and worker counts."""

import os
import re
import subprocess
import sys

CACHE_FILE = ".codedocent_cache.json"
TIMEOUT = 600  # 10 minutes
RESULTS_FILE = "benchmark_results.txt"

REPO_DIR = os.path.dirname(os.path.abspath(__file__))

TESTS = [
    ("gemma3:4b", [1, 2, 4, 8]),
    ("qwen3:8b", [1, 2, 4]),
    ("gemma3:12b", [1, 2]),
]

ANALYSIS_RE = re.compile(
    r"Analysis complete: (\d+) nodes in ([\d.]+)s"
)


def delete_cache():
    path = os.path.join(REPO_DIR, CACHE_FILE)
    if os.path.exists(path):
        os.remove(path)


def pull_model(model):
    print(f"--- Pulling {model}...", flush=True)
    result = subprocess.run(
        ["ollama", "pull", model],
        capture_output=True, text=True, timeout=TIMEOUT,
    )
    if result.returncode != 0:
        print(f"    Failed to pull {model}: {result.stderr.strip()}", flush=True)
        return False
    print(f"    {model} ready.", flush=True)
    return True


def run_benchmark(model, workers):
    delete_cache()
    cmd = [
        sys.executable, "-c",
        "from codedocent.cli import main; main()",
        ".", "--full",
        "--model", model, "--workers", str(workers),
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = REPO_DIR
    print(f"  Running: {model} workers={workers} ...", end=" ", flush=True)
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=TIMEOUT,
            cwd=REPO_DIR, env=env,
        )
    except subprocess.TimeoutExpired:
        print("TIMEOUT", flush=True)
        return {"model": model, "workers": workers, "time": "TIMEOUT",
                "nodes": "", "notes": f"Exceeded {TIMEOUT}s"}

    stderr = result.stderr
    if result.returncode != 0:
        # Extract a short error note from stderr
        lines = stderr.strip().splitlines()
        note = lines[-1][:60] if lines else "Unknown error"
        print("ERROR", flush=True)
        return {"model": model, "workers": workers, "time": "ERROR",
                "nodes": "", "notes": note}

    match = ANALYSIS_RE.search(stderr)
    if match:
        nodes = match.group(1)
        elapsed = match.group(2)
        print(f"{elapsed}s", flush=True)
        return {"model": model, "workers": workers, "time": elapsed,
                "nodes": nodes, "notes": ""}
    else:
        print("OK (no timing)", flush=True)
        return {"model": model, "workers": workers, "time": "?",
                "nodes": "", "notes": "Could not parse timing"}


def format_table(results):
    header = f"| {'Model':<12}| {'Workers':<8}| {'Time (s)':<9}| {'Nodes':<6}| {'Notes':<30}|"
    sep = f"|{'-'*13}|{'-'*9}|{'-'*10}|{'-'*7}|{'-'*31}|"
    rows = [header, sep]
    for r in results:
        row = (
            f"| {r['model']:<12}"
            f"| {r['workers']:<8}"
            f"| {str(r['time']):<9}"
            f"| {str(r['nodes']):<6}"
            f"| {r['notes']:<30}|"
        )
        rows.append(row)
    return "\n".join(rows)


def main():
    # Check ollama is reachable
    try:
        subprocess.run(["ollama", "list"], capture_output=True, text=True,
                        timeout=10, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        print("Error: ollama is not running or not installed.", file=sys.stderr)
        sys.exit(1)

    results = []
    pulled = set()

    for model, worker_counts in TESTS:
        print(f"\n=== Model: {model} ===", flush=True)

        # Pull model if not yet pulled
        if model not in pulled:
            if not pull_model(model):
                # Skip entire model on pull failure
                for w in worker_counts:
                    results.append({"model": model, "workers": w, "time": "SKIP",
                                    "nodes": "", "notes": "Pull failed"})
                continue
            pulled.add(model)

        skip_rest = False
        for w in worker_counts:
            if skip_rest:
                results.append({"model": model, "workers": w, "time": "SKIP",
                                "nodes": "", "notes": "Skipped (prior failure)"})
                continue

            r = run_benchmark(model, w)
            results.append(r)

            if r["time"] in ("ERROR", "TIMEOUT"):
                skip_rest = True

    # Clean up cache one last time
    delete_cache()

    table = format_table(results)
    print(f"\n{'='*72}")
    print("BENCHMARK RESULTS")
    print(f"{'='*72}")
    print(table)

    with open(os.path.join(REPO_DIR, RESULTS_FILE), "w") as f:
        f.write(table + "\n")
    print(f"\nResults saved to {RESULTS_FILE}")


if __name__ == "__main__":
    main()
