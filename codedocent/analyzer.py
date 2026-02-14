"""AI-powered analysis: summaries, pseudocode, quality scoring, and caching."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from codedocent.parser import CodeNode
from codedocent.quality import (
    _score_quality,
    _rollup_quality,
    _summarize_directory,
)

try:
    import ollama
except ImportError:
    ollama = None  # type: ignore[assignment]

CACHE_FILENAME = ".codedocent_cache.json"
MAX_SOURCE_LINES = 200
MIN_LINES_FOR_AI = 3


def _md5(data: bytes) -> "hashlib._Hash":
    """Create an MD5 hash, tolerating FIPS-mode Python builds."""
    try:
        return hashlib.md5(data, usedforsecurity=False)
    except TypeError:
        return hashlib.md5(data)  # nosec B324


def _count_nodes(node: CodeNode) -> int:
    """Recursive count of all nodes in tree."""
    return 1 + sum(_count_nodes(c) for c in node.children)


def _build_prompt(node: CodeNode, model: str = "") -> str:
    """Build the AI prompt for a given node."""
    language = node.language or "unknown"
    source = node.source
    lines = source.splitlines()
    if len(lines) > MAX_SOURCE_LINES:
        source = "\n".join(lines[:MAX_SOURCE_LINES])

    prompt = (
        f"You are a code explainer for non-programmers. "
        f"Given the following {language} code, provide:\n\n"
        f"1. SUMMARY: A plain English explanation (1-3 sentences) "
        f"that a "
        f"non-programmer can understand. Explain WHAT it does "
        f"and WHY, not HOW. "
        f"Avoid jargon.\n\n"
        f"2. PSEUDOCODE: A simplified pseudocode version using plain English "
        f"function/variable names. Keep it short.\n\n"
        f"Respond in exactly this format:\n"
        f"SUMMARY: <your summary>\n"
        f"PSEUDOCODE:\n"
        f"<your pseudocode>\n\n"
        f"Here is the code:\n"
        f"```{language}\n"
        f"{source}\n"
        f"```"
    )

    if "qwen3" in model.lower():
        prompt += "\n\n/no_think"

    return prompt


def _strip_think_tags(text: str) -> str:
    """Remove <think>...</think> blocks from model output.

    Handles variants: <think>, <|think|>, and unclosed tags.
    """
    # Remove well-formed pairs (including <|think|> variants)
    text = re.sub(r"<\|?think\|?>.*?<\|?/think\|?>", "", text, flags=re.DOTALL)
    # Remove unclosed tags (tag to end of string)
    text = re.sub(r"<\|?think\|?>.*", "", text, flags=re.DOTALL)
    return text.strip()


def _parse_ai_response(text: str) -> tuple[str, str]:
    """Parse SUMMARY and PSEUDOCODE from AI response text."""
    summary = ""
    pseudocode = ""

    summary_match = re.search(
        r"SUMMARY:\s*(.*?)(?=\nPSEUDOCODE:|$)", text, re.DOTALL
    )
    pseudocode_match = re.search(r"PSEUDOCODE:\s*(.*)", text, re.DOTALL)

    if summary_match:
        summary = summary_match.group(1).strip()
    if pseudocode_match:
        pseudocode = pseudocode_match.group(1).strip()

    # Fallback: first line as summary if parsing failed
    if not summary:
        lines = text.strip().splitlines()
        if lines:
            summary = lines[0].strip()

    return summary, pseudocode


_AI_TIMEOUT = 120


def _summarize_with_cloud(
    node: CodeNode, ai_config: dict,
) -> tuple[str, str] | None:
    """Call a cloud AI endpoint for summary and pseudocode.

    Returns ``None`` if the call times out.
    Raises ``RuntimeError`` on API errors.
    """
    from codedocent.cloud_ai import cloud_chat  # pylint: disable=import-outside-toplevel  # noqa: E501

    prompt = _build_prompt(node, ai_config["model"])
    pool = ThreadPoolExecutor(max_workers=1)
    future = pool.submit(
        cloud_chat,
        prompt, ai_config["endpoint"],
        ai_config["api_key"], ai_config["model"],
    )
    try:
        raw = future.result(timeout=_AI_TIMEOUT)
    except TimeoutError:
        future.cancel()
        pool.shutdown(wait=False, cancel_futures=True)
        return None
    pool.shutdown(wait=False)
    raw = _strip_think_tags(raw)
    if not raw or len(raw) < 10:
        return ("Could not generate summary", "")
    summary, pseudocode = _parse_ai_response(raw)
    if not summary or len(summary) < 5:
        summary = "Could not generate summary"
    return summary, pseudocode


def _summarize_with_ai(
    node: CodeNode, model: str, ai_config: dict | None = None,
) -> tuple[str, str] | None:
    """Call ollama (or cloud) to get summary and pseudocode for a node.

    Returns ``None`` if the AI call times out.
    """
    if ai_config and ai_config.get("backend") == "cloud":
        return _summarize_with_cloud(node, ai_config)

    prompt = _build_prompt(node, model)
    pool = ThreadPoolExecutor(max_workers=1)
    future = pool.submit(
        ollama.chat,
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    try:
        response = future.result(timeout=_AI_TIMEOUT)
    except TimeoutError:
        future.cancel()
        pool.shutdown(wait=False, cancel_futures=True)
        return None
    pool.shutdown(wait=False)
    msg = getattr(response, "message", None)
    if msg is None:
        raise ValueError("Unexpected Ollama response format")
    raw = getattr(msg, "content", None) or ""
    raw = _strip_think_tags(raw)
    # Garbage response fallback: empty or very short after stripping
    if not raw or len(raw) < 10:
        return ("Could not generate summary", "")
    summary, pseudocode = _parse_ai_response(raw)
    # Final guard: if summary is empty or too short, replace it
    if not summary or len(summary) < 5:
        summary = "Could not generate summary"
    return summary, pseudocode


def _cache_model_id(model: str, ai_config: dict | None = None) -> str:
    """Return a cache-key model identifier."""
    if ai_config and ai_config.get("backend") == "cloud":
        return f"cloud:{ai_config['provider']}:{ai_config['model']}"
    return model


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------


def _cache_key(node: CodeNode) -> str:
    """Generate a cache key based on filepath, name, and source hash."""
    source_hash = _md5(node.source.encode()).hexdigest()
    return f"{node.filepath}::{node.name}::{source_hash}"


def _load_cache(path: str) -> dict:
    """Load cache from JSON file."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and data.get("version") == 1:
            return data
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return {"version": 1, "model": "", "entries": {}}


def _save_cache(path: str, data: dict) -> None:
    """Save cache to JSON file atomically."""
    parent = os.path.dirname(os.path.abspath(path))
    tmp_path: str | None = None
    try:
        fd = tempfile.NamedTemporaryFile(  # pylint: disable=consider-using-with  # noqa: E501
            mode="w", encoding="utf-8",
            dir=parent, delete=False, suffix=".tmp",
        )
        tmp_path = fd.name
        try:
            json.dump(data, fd, indent=2)
            fd.flush()
            os.fsync(fd.fileno())
        finally:
            fd.close()
        os.replace(tmp_path, path)
        tmp_path = None  # success — don't clean up
    except OSError as e:
        print(
            f"Warning: could not save cache: {e}",
            file=sys.stderr,
        )
    finally:
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Node ID assignment
# ---------------------------------------------------------------------------


def assign_node_ids(root: CodeNode) -> dict[str, CodeNode]:
    """Walk tree, assign a unique 12-char hex node_id to every node.

    Returns a lookup dict mapping node_id -> CodeNode.
    """
    lookup: dict[str, CodeNode] = {}

    def _walk(node: CodeNode, path_parts: list[str]) -> None:
        key = "::".join(path_parts)
        node_id = _md5(key.encode()).hexdigest()[:12]
        node.node_id = node_id
        lookup[node_id] = node
        for child in node.children:
            child_parts = path_parts + [child.node_type, child.name]
            _walk(child, child_parts)

    _walk(root, [root.name])
    return lookup


# ---------------------------------------------------------------------------
# Single-node analysis (used by server)
# ---------------------------------------------------------------------------


def analyze_single_node(  # pylint: disable=too-many-locals
    node: CodeNode, model: str, cache_dir: str,
    *, ai_config: dict | None = None,
) -> None:
    """Run quality scoring + AI analysis on a single node.

    Reads/writes the cache. Applies min-lines guard and garbage fallback.
    """
    is_cloud = ai_config and ai_config.get("backend") == "cloud"
    if not is_cloud and ollama is None:
        node.summary = "AI unavailable (ollama not installed)"
        return

    # Quality scoring
    quality, warnings = _score_quality(node)
    node.quality = quality
    node.warnings = warnings

    # Min-lines guard
    if node.line_count < MIN_LINES_FOR_AI:
        node.summary = f"Small {node.node_type} ({node.line_count} lines)"
        return

    # Directory nodes get synthesized summaries, not AI
    if node.node_type == "directory":
        _summarize_directory(node)
        return

    # Cache
    cache_path = os.path.join(cache_dir, CACHE_FILENAME)
    cache = _load_cache(cache_path)

    model_id = _cache_model_id(model, ai_config)
    if cache.get("model") != model_id:
        cache = {"version": 1, "model": model_id, "entries": {}}

    key = _cache_key(node)
    if key in cache["entries"]:
        entry = cache["entries"][key]
        node.summary = entry.get("summary")
        node.pseudocode = entry.get("pseudocode")
        return

    try:
        result = _summarize_with_ai(node, model, ai_config=ai_config)
        if result is None:
            node.summary = "Summary timed out"
            return
        summary, pseudocode = result
        node.summary = summary
        node.pseudocode = pseudocode
        cache["entries"][key] = {"summary": summary, "pseudocode": pseudocode}
        _save_cache(cache_path, cache)
    except (
        ConnectionError, RuntimeError, ValueError,
        OSError, AttributeError, TypeError,
    ) as e:
        print(f"  AI error for {node.name}: {e}", file=sys.stderr)
        node.summary = "Summary generation failed"


# ---------------------------------------------------------------------------
# Main entry points
# ---------------------------------------------------------------------------


def _collect_nodes(
    node: CodeNode, depth: int = 0,
) -> list[tuple[CodeNode, int]]:
    """Collect all nodes with their depth for priority batching."""
    result = [(node, depth)]
    for child in node.children:
        result.extend(_collect_nodes(child, depth + 1))
    return result


def _score_all_nodes(all_nodes: list[tuple[CodeNode, int]]) -> None:
    """Phase 1: Quality-score all nodes."""
    for node, _depth in all_nodes:
        quality, warnings = _score_quality(node)
        node.quality = quality
        node.warnings = warnings


def _rollup_file_quality(all_nodes: list[tuple[CodeNode, int]]) -> None:
    """Phase 1b: Rollup quality to files and classes (deepest first)."""
    rollup_nodes = [
        (n, d) for n, d in all_nodes
        if n.node_type in ("file", "class")
    ]
    rollup_nodes.sort(key=lambda x: x[1], reverse=True)
    for node, _depth in rollup_nodes:
        _rollup_quality(node)


def _select_ai_nodes(
    all_nodes: list[tuple[CodeNode, int]],
) -> list[CodeNode]:
    """Select and sort nodes for AI analysis (files then code)."""
    files = sorted(
        ((n, d) for n, d in all_nodes if n.node_type == "file"),
        key=lambda x: x[1],
    )
    code = sorted(
        ((n, d) for n, d in all_nodes
         if n.node_type in ("class", "function", "method")),
        key=lambda x: x[1],
    )
    return [n for n, _ in files] + [n for n, _ in code]


def _dispatch_work(func, nodes: list[CodeNode], workers: int) -> None:
    """Run *func* on each node, serially or in parallel."""
    if workers == 1:
        for node in nodes:
            func(node)
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = {pool.submit(func, n): n for n in nodes}
            for future in as_completed(futs):
                exc = future.exception()
                if isinstance(exc, ConnectionError):
                    raise exc


def _run_ai_batch(
    all_nodes: list[tuple[CodeNode, int]],
    model: str,
    cache: dict,
    workers: int,
    ai_config: dict | None = None,
) -> int:
    """Phases 2 & 3: AI-analyze files then code nodes."""
    total, counter = len(all_nodes), [0]
    cache_lock, progress_lock = threading.Lock(), threading.Lock()

    def _progress(label: str) -> None:
        with progress_lock:
            counter[0] += 1
            print(f"[{counter[0]}/{total}] {label}...", file=sys.stderr)

    def _do_one(node: CodeNode) -> None:
        if node.line_count < MIN_LINES_FOR_AI:
            node.summary = f"Small {node.node_type} ({node.line_count} lines)"
            _progress(f"Skipping small {node.name}")
            return
        key = _cache_key(node)
        with cache_lock:
            if key in cache["entries"]:
                entry = cache["entries"][key]
                node.summary = entry.get("summary")
                node.pseudocode = entry.get("pseudocode")
                _progress(f"Cache hit: {node.name}")
                return
        _progress(f"Analyzing {node.name}")
        try:
            result = _summarize_with_ai(node, model, ai_config=ai_config)
            if result is None:
                node.summary = "Summary timed out"
                return
            summary, pseudocode = result
            with cache_lock:
                node.summary = summary
                node.pseudocode = pseudocode
                cache["entries"][key] = {
                    "summary": summary,
                    "pseudocode": pseudocode,
                }
        except Exception as e:  # pylint: disable=broad-exception-caught
            node.summary = "Summary generation failed"
            print(f"  AI error for {node.name}: {e}", file=sys.stderr)

    ai_nodes = _select_ai_nodes(all_nodes)
    _dispatch_work(_do_one, ai_nodes, workers)
    return len(ai_nodes)


def _summarize_directories(all_nodes: list[tuple[CodeNode, int]]) -> None:
    """Phase 4: Synthesize directory summaries (deepest first)."""
    dirs = [(n, d) for n, d in all_nodes if n.node_type == "directory"]
    dirs.sort(key=lambda x: x[1], reverse=True)
    for node, _depth in dirs:
        _summarize_directory(node)


def _require_ollama() -> None:
    """Exit with error if ollama is not installed."""
    if ollama is None:
        print(
            "Error: ollama package not installed. "
            "Install with: pip install ollama\n"
            "Or use --no-ai to skip AI analysis.",
            file=sys.stderr,
        )
        sys.exit(1)


def _init_cache(
    root: CodeNode, model: str, ai_config: dict | None = None,
) -> tuple[str, dict]:
    """Load (or reset) the analysis cache for *model*."""
    cache_dir = root.filepath or "."
    cache_path = os.path.join(cache_dir, CACHE_FILENAME)
    cache = _load_cache(cache_path)
    model_id = _cache_model_id(model, ai_config)
    if cache.get("model") != model_id:
        cache = {"version": 1, "model": model_id, "entries": {}}
    return cache_path, cache


def analyze(
    root: CodeNode,
    model: str = "qwen3:14b",
    workers: int = 1,
    *,
    ai_config: dict | None = None,
) -> CodeNode:
    """Analyze the full tree with AI summaries and quality scoring."""
    is_cloud = ai_config and ai_config.get("backend") == "cloud"
    if not is_cloud:
        _require_ollama()

    cache_path, cache = _init_cache(root, model, ai_config=ai_config)
    all_nodes = _collect_nodes(root)
    start_time = time.monotonic()

    _score_all_nodes(all_nodes)
    _rollup_file_quality(all_nodes)

    try:
        ai_count = _run_ai_batch(
            all_nodes, model, cache, workers, ai_config=ai_config,
        )
    except ConnectionError as e:
        print(
            f"\nError: Could not connect to ollama: {e}\n"
            "Make sure ollama is running (ollama serve),"
            " or use --no-ai to skip AI analysis.",
            file=sys.stderr,
        )
        sys.exit(1)
    except RuntimeError as e:
        print(
            f"\nError: Cloud AI request failed: {e}\n"
            "Check your API key and endpoint, or use --no-ai"
            " to skip AI analysis.",
            file=sys.stderr,
        )
        sys.exit(1)

    _summarize_directories(all_nodes)
    _save_cache(cache_path, cache)

    elapsed = time.monotonic() - start_time
    print(
        f"Analysis complete: {ai_count} nodes in {elapsed:.1f}s "
        f"({workers} workers, model: {model})",
        file=sys.stderr,
    )

    return root


def analyze_no_ai(root: CodeNode) -> CodeNode:
    """Analyze with quality scoring only — no ollama calls."""
    total = _count_nodes(root)
    counter = [0]

    def _walk(node: CodeNode) -> None:
        counter[0] += 1
        idx = counter[0]
        print(f"[{idx}/{total}] Scoring {node.name}...", file=sys.stderr)

        quality, warnings = _score_quality(node)
        node.quality = quality
        node.warnings = warnings

        for child in node.children:
            _walk(child)

        if node.node_type in ("file", "class"):
            _rollup_quality(node)

        if node.node_type == "directory":
            _summarize_directory(node)

    _walk(root)
    return root
