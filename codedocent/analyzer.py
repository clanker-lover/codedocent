"""AI-powered analysis: summaries, pseudocode, quality scoring, and caching."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys

from codedocent.parser import CodeNode

try:
    import ollama
except ImportError:
    ollama = None

CACHE_FILENAME = ".codedocent_cache.json"
MAX_SOURCE_LINES = 200


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
        f"1. SUMMARY: A plain English explanation (1-3 sentences) that a "
        f"non-programmer can understand. Explain WHAT it does and WHY, not HOW. "
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
    """Remove <think>...</think> blocks from model output."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


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


def _summarize_with_ai(
    node: CodeNode, model: str
) -> tuple[str, str]:
    """Call ollama to get summary and pseudocode for a node."""
    prompt = _build_prompt(node, model)
    response = ollama.chat(
        model=model, messages=[{"role": "user", "content": prompt}]
    )
    raw = response.message.content
    raw = _strip_think_tags(raw)
    return _parse_ai_response(raw)


def _count_parameters(node: CodeNode) -> int:
    """Count parameters of a function/method using tree-sitter."""
    if not node.source or not node.language:
        return 0

    import tree_sitter_language_pack as tslp

    try:
        parser = tslp.get_parser(node.language)
    except Exception:
        return 0

    tree = parser.parse(node.source.encode())
    root = tree.root_node

    # Find the parameters / formal_parameters node
    param_node = None

    def _find_params(n):
        nonlocal param_node
        if param_node is not None:
            return
        if n.type in ("parameters", "formal_parameters"):
            param_node = n
            return
        for child in n.children:
            _find_params(child)

    _find_params(root)
    if param_node is None:
        return 0

    count = 0
    for child in param_node.children:
        # Skip punctuation like ( ) ,
        if child.type in ("(", ")", ","):
            continue
        # For Python, skip self/cls
        if node.language == "python":
            text = child.text.decode() if child.text else ""
            if text in ("self", "cls"):
                continue
        count += 1

    return count


def _score_quality(
    node: CodeNode,
) -> tuple[str | None, list[str] | None]:
    """Score code quality using radon and heuristics.

    Returns (quality, warnings) where quality is 'clean', 'complex',
    or 'warning', and warnings is a list of warning strings.
    For directories, returns (None, None).
    """
    if node.node_type == "directory":
        return None, None

    warnings: list[str] = []
    quality = "clean"

    # Radon complexity for Python
    if node.language == "python" and node.source:
        try:
            from radon.complexity import cc_visit, cc_rank

            blocks = cc_visit(node.source)
            if blocks:
                worst = max(b.complexity for b in blocks)
                rank = cc_rank(worst)
                if rank in ("A", "B"):
                    pass  # clean
                elif rank == "C":
                    quality = "complex"
                    warnings.append(f"Cyclomatic complexity grade {rank}")
                else:
                    quality = "warning"
                    warnings.append(f"High cyclomatic complexity grade {rank}")
        except Exception:
            pass

    # Heuristic: long function
    if node.node_type in ("function", "method") and node.line_count > 50:
        warnings.append("Long function: consider splitting")

    # Heuristic: many parameters
    if node.node_type in ("function", "method"):
        param_count = _count_parameters(node)
        if param_count > 5:
            warnings.append("Many parameters: consider grouping")

    # Escalate if heuristic warnings exist but quality is still clean
    if warnings and quality == "clean":
        quality = "complex"

    return quality, warnings if warnings else None


def _summarize_directory(node: CodeNode) -> None:
    """Synthesize a directory summary from children. No AI needed."""
    if node.node_type != "directory":
        return

    child_names = [c.name for c in node.children]
    file_children = [c for c in node.children if c.node_type == "file"]
    dir_children = [c for c in node.children if c.node_type == "directory"]

    parts: list[str] = []
    if file_children:
        names = ", ".join(c.name for c in file_children)
        parts.append(f"{len(file_children)} files: {names}")
    if dir_children:
        names = ", ".join(c.name for c in dir_children)
        parts.append(f"{len(dir_children)} directories: {names}")

    node.summary = f"Contains {'; '.join(parts)}" if parts else "Empty directory"

    # Quality = worst child quality
    quality_order = {"warning": 2, "complex": 1, "clean": 0}
    worst = "clean"
    all_warnings: list[str] = []
    for child in node.children:
        if child.quality and quality_order.get(child.quality, 0) > quality_order.get(
            worst, 0
        ):
            worst = child.quality
        if child.warnings:
            all_warnings.extend(child.warnings)

    node.quality = worst
    node.warnings = all_warnings if all_warnings else None


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------


def _cache_key(node: CodeNode) -> str:
    """Generate a cache key based on filepath, name, and source hash."""
    source_hash = hashlib.md5(node.source.encode()).hexdigest()
    return f"{node.filepath}::{node.name}::{source_hash}"


def _load_cache(path: str) -> dict:
    """Load cache from JSON file."""
    try:
        with open(path) as f:
            data = json.load(f)
        if isinstance(data, dict) and data.get("version") == 1:
            return data
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return {"version": 1, "model": "", "entries": {}}


def _save_cache(path: str, data: dict) -> None:
    """Save cache to JSON file."""
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    except OSError as e:
        print(f"Warning: could not save cache: {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Main entry points
# ---------------------------------------------------------------------------


def analyze(root: CodeNode, model: str = "qwen3:14b") -> CodeNode:
    """Analyze the full tree with AI summaries and quality scoring.

    Walks the tree depth-first. For each non-directory node, calls ollama
    for summaries (with caching). For directories, synthesizes summaries
    from children. Always runs quality scoring.
    """
    if ollama is None:
        print(
            "Error: ollama package not installed. "
            "Install with: pip install ollama\n"
            "Or use --no-ai to skip AI analysis.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Determine cache path
    cache_dir = root.filepath or "."
    cache_path = os.path.join(cache_dir, CACHE_FILENAME)
    cache = _load_cache(cache_path)

    # Invalidate cache if model changed
    if cache.get("model") != model:
        cache = {"version": 1, "model": model, "entries": {}}

    total = _count_nodes(root)
    counter = [0]

    def _walk(node: CodeNode) -> None:
        counter[0] += 1
        idx = counter[0]

        # Progress
        label = node.name
        if node.filepath and node.filepath != node.name:
            parts = node.filepath.split(os.sep)
            if len(parts) > 1:
                label = f"{parts[-1]} \u2192 {node.name}" if node.node_type not in ("file", "directory") else node.name

        print(f"[{idx}/{total}] Analyzing {label}...", file=sys.stderr)

        # Quality scoring (always)
        quality, warnings = _score_quality(node)
        node.quality = quality
        node.warnings = warnings

        # AI summary (non-directory only)
        if node.node_type != "directory":
            key = _cache_key(node)
            if key in cache["entries"]:
                entry = cache["entries"][key]
                node.summary = entry.get("summary")
                node.pseudocode = entry.get("pseudocode")
                print(
                    f"[{idx}/{total}] cache hit: {label}",
                    file=sys.stderr,
                )
            else:
                try:
                    summary, pseudocode = _summarize_with_ai(node, model)
                    node.summary = summary
                    node.pseudocode = pseudocode
                    cache["entries"][key] = {
                        "summary": summary,
                        "pseudocode": pseudocode,
                    }
                except Exception as e:
                    node.summary = "Summary generation failed"
                    print(
                        f"[{idx}/{total}] AI error for {label}: {e}",
                        file=sys.stderr,
                    )

        # Recurse into children
        for child in node.children:
            _walk(child)

        # After children, synthesize directory summaries
        if node.node_type == "directory":
            _summarize_directory(node)

    try:
        _walk(root)
    except ConnectionError as e:
        print(
            f"\nError: Could not connect to ollama: {e}\n"
            "Make sure ollama is running (ollama serve), or use --no-ai to skip AI analysis.",
            file=sys.stderr,
        )
        sys.exit(1)

    _save_cache(cache_path, cache)
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

        if node.node_type == "directory":
            _summarize_directory(node)

    _walk(root)
    return root
