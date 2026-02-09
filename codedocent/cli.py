"""CLI for codedocent: scan, parse, and render code visualizations."""

from __future__ import annotations

import argparse

from codedocent.parser import CodeNode, parse_directory
from codedocent.scanner import scan_directory


def print_tree(node: CodeNode, indent: int = 0) -> None:
    """Print a text representation of the code tree."""
    prefix = "  " * indent
    label = node.node_type.upper()

    if node.node_type == "directory":
        print(f"{prefix}{label}: {node.name}/  ({node.line_count} lines)")
    elif node.node_type == "file":
        parts = [f"{label}: {node.name}"]
        if node.language:
            parts.append(f"[{node.language}]")
        parts.append(f"({node.line_count} lines)")
        if node.imports:
            parts.append(f"imports: {', '.join(node.imports)}")
        print(f"{prefix}{' '.join(parts)}")
    else:
        line_info = f"L{node.start_line}-{node.end_line}"
        print(
            f"{prefix}{label}: {node.name}"
            f"  ({line_info}, {node.line_count} lines)"
        )

    for child in node.children:
        print_tree(child, indent + 1)


def main() -> None:
    """Entry point for the codedocent CLI."""
    parser = argparse.ArgumentParser(
        prog="codedocent",
        description="Code visualization for non-programmers",
    )
    parser.add_argument("path", help="Path to the directory to scan")
    parser.add_argument(
        "--text",
        action="store_true",
        help="Print text tree instead of generating HTML",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="codedocent_output.html",
        help="HTML output file path (default: codedocent_output.html)",
    )
    parser.add_argument(
        "--model",
        default="qwen3:14b",
        help="Ollama model for AI summaries (default: qwen3:14b)",
    )
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Skip AI analysis, render with placeholders",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help=(
            "Analyze everything upfront"
            " (priority-batched), write static HTML"
        ),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help=(
            "Port for the interactive server"
            " (default: auto-select from 8420)"
        ),
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of parallel AI workers for --full mode (default: 1)",
    )

    args = parser.parse_args()

    scanned = scan_directory(args.path)
    tree = parse_directory(scanned, root=args.path)

    if args.text:
        # Text mode: quality score only, print tree
        from codedocent.analyzer import analyze_no_ai  # pylint: disable=import-outside-toplevel  # noqa: E501

        analyze_no_ai(tree)
        print_tree(tree)
    elif args.no_ai:
        # No-AI mode: quality score only, static HTML
        from codedocent.analyzer import analyze_no_ai  # pylint: disable=import-outside-toplevel  # noqa: E501
        from codedocent.renderer import render  # pylint: disable=import-outside-toplevel  # noqa: E501

        analyze_no_ai(tree)
        render(tree, args.output)
        print(f"HTML output written to {args.output}")
    elif args.full:
        # Full mode: upfront AI analysis, static HTML
        from codedocent.analyzer import analyze  # pylint: disable=import-outside-toplevel  # noqa: E501
        from codedocent.renderer import render  # pylint: disable=import-outside-toplevel  # noqa: E501

        analyze(tree, model=args.model, workers=args.workers)
        render(tree, args.output)
        print(f"HTML output written to {args.output}")
    else:
        # Default lazy mode: interactive server
        from codedocent.analyzer import analyze_no_ai, assign_node_ids  # pylint: disable=import-outside-toplevel  # noqa: E501
        from codedocent.server import start_server  # pylint: disable=import-outside-toplevel  # noqa: E501

        analyze_no_ai(tree)
        node_lookup = assign_node_ids(tree)
        start_server(
            tree,
            node_lookup,
            model=args.model,
            port=args.port,
        )


if __name__ == "__main__":
    main()
