"""Quality scoring: complexity and parameter checks."""

from __future__ import annotations

from codedocent.parser import CodeNode

PARAM_THRESHOLD = 5


def _count_parameters(node: CodeNode) -> int:
    """Count parameters of a function/method using tree-sitter."""
    if not node.source or not node.language:
        return 0

    import tree_sitter_language_pack as tslp  # pylint: disable=import-outside-toplevel  # noqa: E501

    try:
        parser = tslp.get_parser(node.language)  # type: ignore[arg-type]
    except (KeyError, ValueError):
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


def _worst_quality(a: str, b: str) -> str:
    """Return the worse of two quality labels."""
    order = {"clean": 0, "complex": 1, "warning": 2}
    return a if order.get(a, 0) >= order.get(b, 0) else b


def _score_radon(node: CodeNode) -> tuple[str, str | None]:
    """Score cyclomatic complexity via radon (Python only)."""
    if node.language != "python" or not node.source:
        return "clean", None

    try:
        from radon.complexity import cc_visit, cc_rank  # type: ignore[import-untyped]  # pylint: disable=import-outside-toplevel  # noqa: E501

        blocks = cc_visit(node.source)
        if blocks:
            worst = max(b.complexity for b in blocks)
            rank = cc_rank(worst)
            if rank in ("A", "B", "C"):
                return "clean", None
            if rank == "D":
                return (
                    "complex",
                    f"High complexity (grade {rank},"
                    f" score {worst})",
                )
            return (
                "warning",
                f"Severe complexity (grade {rank},"
                f" score {worst})",
            )
    except (ImportError, AttributeError, SyntaxError):  # nosec B110
        pass

    return "clean", None


def _score_param_count(node: CodeNode) -> tuple[str, str | None]:
    """Score based on parameter count."""
    if node.node_type in ("function", "method"):
        if _count_parameters(node) > PARAM_THRESHOLD:
            return "complex", "Many parameters: consider grouping"
    return "clean", None


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

    for scorer in (_score_radon, _score_param_count):
        label, warning = scorer(node)
        quality = _worst_quality(quality, label)
        if warning:
            warnings.append(warning)

    return quality, warnings if warnings else None


def _child_quality_counts(
    children: list[CodeNode],
) -> tuple[str, int, int]:
    """Count complex/warning children and determine worst quality.

    Returns (worst_quality, complex_count, warning_count).
    """
    _order = {"warning": 2, "complex": 1, "clean": 0}
    worst = "clean"
    complex_count = 0
    warning_count = 0
    for child in children:
        rank = _order.get(child.quality or "clean", 0)
        if rank > _order.get(worst, 0):
            worst = child.quality or "clean"
        if child.quality == "complex":
            complex_count += 1
        elif child.quality == "warning":
            warning_count += 1
    return worst, complex_count, warning_count


def _build_rollup_warnings(
    complex_count: int,
    warning_count: int,
    singular: str,
    plural: str,
) -> list[str]:
    """Build rollup warning strings from child quality counts."""
    warnings: list[str] = []
    if warning_count:
        lbl = singular if warning_count == 1 else plural
        warnings.append(f"Contains {warning_count} high-risk {lbl}")
    if complex_count:
        lbl = singular if complex_count == 1 else plural
        warnings.append(f"{complex_count} complex {lbl} inside")
    return warnings


def _rollup_quality(node: CodeNode) -> None:
    """Roll up child quality into a file or class node."""
    if not node.children:
        return
    _order = {"warning": 2, "complex": 1, "clean": 0}
    own_quality = node.quality or "clean"
    own_warnings = list(node.warnings) if node.warnings else []
    worst, c_count, w_count = _child_quality_counts(node.children)
    if _order[worst] > _order.get(own_quality, 0):
        node.quality = worst
    own_warnings.extend(
        _build_rollup_warnings(c_count, w_count, "function", "functions"),
    )
    node.warnings = own_warnings if own_warnings else None


def _summarize_directory(node: CodeNode) -> None:
    """Synthesize a directory summary from children. No AI needed."""
    if node.node_type != "directory":
        return

    file_children = [c for c in node.children if c.node_type == "file"]
    dir_children = [c for c in node.children if c.node_type == "directory"]

    parts: list[str] = []
    if file_children:
        names = ", ".join(c.name for c in file_children)
        parts.append(f"{len(file_children)} files: {names}")
    if dir_children:
        names = ", ".join(c.name for c in dir_children)
        parts.append(f"{len(dir_children)} directories: {names}")

    node.summary = (
        f"Contains {'; '.join(parts)}" if parts else "Empty directory"
    )

    worst, c_count, w_count = _child_quality_counts(node.children)
    node.quality = worst
    rollup = _build_rollup_warnings(
        c_count, w_count, "child", "children",
    )
    node.warnings = rollup if rollup else None
