"""CLI for codedocent: scan, parse, and render code visualizations."""

from __future__ import annotations

import argparse

from codedocent.parser import CodeNode, parse_directory
from codedocent.scanner import scan_directory


def print_tree(node: CodeNode, indent: int = 0) -> None:
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
        print(f"{prefix}{label}: {node.name}  ({line_info}, {node.line_count} lines)")

    for child in node.children:
        print_tree(child, indent + 1)


def main() -> None:
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

    args = parser.parse_args()

    scanned = scan_directory(args.path)
    tree = parse_directory(scanned, root=args.path)

    from codedocent.analyzer import analyze, analyze_no_ai

    if args.no_ai:
        analyze_no_ai(tree)
    else:
        analyze(tree, model=args.model)

    if args.text:
        print_tree(tree)
    else:
        from codedocent.renderer import render

        render(tree, args.output)
        print(f"HTML output written to {args.output}")


if __name__ == "__main__":
    main()
