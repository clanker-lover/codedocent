"""CLI for codedocent: scan, parse, and render code visualizations."""

from __future__ import annotations

import argparse
import os
import sys

from codedocent.ollama_utils import check_ollama, fetch_ollama_models
from codedocent.parser import CodeNode, parse_directory
from codedocent.scanner import scan_directory


# Re-export for backwards compatibility and testability
_check_ollama = check_ollama
_fetch_ollama_models = fetch_ollama_models


def _safe_input(prompt: str) -> str:
    """Wrap input() to handle EOF gracefully."""
    try:
        return input(prompt)
    except EOFError:
        print("\nInput closed. Exiting.")
        sys.exit(0)


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


def _ask_folder() -> str:
    """Prompt for a valid folder path, re-asking on invalid input."""
    while True:
        path = _safe_input("What folder do you want to analyze? ").strip()
        path = os.path.expanduser(path)
        if os.path.isdir(path):
            file_count = len(list(scan_directory(path)))
            print(f"\u2713 Found {file_count} files\n")
            return path
        print(f"  '{path}' is not a valid directory. Try again.\n")


def _ask_no_ai_fallback() -> bool:
    """Ask user whether to continue without AI. Returns True for no-ai."""
    fallback = _safe_input("Continue without AI? [Y/n]: ").strip().lower()
    if fallback in ("", "y", "yes"):
        return True
    raise SystemExit(0)


def _pick_model(models: list[str]) -> str:
    """Let the user pick from a numbered list of models."""
    print("Available models:")
    for i, m in enumerate(models, 1):
        print(f"  {i}. {m}")
    choice = _safe_input("Which model? [1]: ").strip()
    if choice == "":
        return models[0]
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(models):
            return models[idx]
    except ValueError:
        pass
    return models[0]


def _run_wizard() -> argparse.Namespace:
    """Interactive setup wizard for codedocent."""
    print("\ncodedocent \u2014 code visualization for humans\n")

    path = _ask_folder()

    # --- Ollama check ---
    model = "qwen3:14b"
    no_ai = False

    print("Checking for Ollama...", end=" ", flush=True)
    if _check_ollama():
        print("found!")
        models = _fetch_ollama_models()
        if models:
            model = _pick_model(models)
        else:
            print("No models found.")
            no_ai = _ask_no_ai_fallback()
    else:
        print("not found.")
        no_ai = _ask_no_ai_fallback()

    # --- Mode ---
    print("\nHow do you want to view it?")
    print("  1. Interactive \u2014 browse in browser [default]")
    print("  2. Full export \u2014 analyze everything, save HTML")
    print("  3. Text tree \u2014 plain text in terminal")
    mode_choice = _safe_input("Choice [1]: ").strip()

    text = mode_choice == "3"
    full = mode_choice == "2"

    print()

    return argparse.Namespace(
        path=path,
        text=text,
        output="codedocent_output.html",
        model=model,
        no_ai=no_ai,
        full=full,
        port=None,
        workers=1,
        gui=False,
    )


def _build_arg_parser() -> argparse.ArgumentParser:
    """Create and return the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="codedocent",
        description="Code visualization for non-programmers",
    )
    parser.add_argument(
        "path", nargs="?", default=None,
        help="Path to the directory to scan",
    )
    parser.add_argument(
        "--text", action="store_true",
        help="Print text tree instead of generating HTML",
    )
    parser.add_argument(
        "-o", "--output", default="codedocent_output.html",
        help="HTML output file path (default: codedocent_output.html)",
    )
    parser.add_argument(
        "--model", default="qwen3:14b",
        help="Ollama model for AI summaries (default: qwen3:14b)",
    )
    parser.add_argument(
        "--no-ai", action="store_true",
        help="Skip AI analysis, render with placeholders",
    )
    parser.add_argument(
        "--full", action="store_true",
        help="Analyze everything upfront, write static HTML",
    )
    parser.add_argument(
        "--port", type=int, default=None,
        help="Port for interactive server (default: auto from 8420)",
    )
    parser.add_argument(
        "--workers", type=int, default=1,
        help="Number of parallel AI workers for --full mode (default: 1)",
    )
    parser.add_argument(
        "--gui", action="store_true",
        help="Open GUI launcher",
    )
    return parser


def _run_text_mode(tree: CodeNode) -> None:
    """Text mode: quality score only, print tree."""
    from codedocent.analyzer import analyze_no_ai  # pylint: disable=import-outside-toplevel  # noqa: E501

    analyze_no_ai(tree)
    print_tree(tree)


def _run_no_ai_mode(tree: CodeNode, output: str) -> None:
    """No-AI mode: quality score only, static HTML."""
    from codedocent.analyzer import analyze_no_ai  # pylint: disable=import-outside-toplevel  # noqa: E501
    from codedocent.renderer import render  # pylint: disable=import-outside-toplevel  # noqa: E501

    analyze_no_ai(tree)
    render(tree, output)
    print(f"HTML output written to {output}")


def _run_full_mode(
    tree: CodeNode, model: str, workers: int, output: str,
) -> None:
    """Full mode: upfront AI analysis, static HTML."""
    from codedocent.analyzer import analyze  # pylint: disable=import-outside-toplevel  # noqa: E501
    from codedocent.renderer import render  # pylint: disable=import-outside-toplevel  # noqa: E501

    analyze(tree, model=model, workers=workers)
    render(tree, output)
    print(f"HTML output written to {output}")


def _run_interactive_mode(
    tree: CodeNode, model: str, port: int | None,
) -> None:
    """Default lazy mode: interactive server."""
    from codedocent.analyzer import analyze_no_ai, assign_node_ids  # pylint: disable=import-outside-toplevel  # noqa: E501
    from codedocent.server import start_server  # pylint: disable=import-outside-toplevel  # noqa: E501

    analyze_no_ai(tree)
    node_lookup = assign_node_ids(tree)
    start_server(tree, node_lookup, model=model, port=port)


def main() -> None:
    """Entry point for the codedocent CLI."""
    parser = _build_arg_parser()
    args = parser.parse_args()

    if args.gui:
        from codedocent.gui import main as gui_main  # pylint: disable=import-outside-toplevel  # noqa: E501

        gui_main()
        return

    if args.path is None:
        args = _run_wizard()

    scanned = scan_directory(args.path)
    tree = parse_directory(scanned, root=args.path)

    if args.text:
        _run_text_mode(tree)
    elif args.no_ai:
        _run_no_ai_mode(tree, args.output)
    elif args.full:
        _run_full_mode(tree, args.model, args.workers, args.output)
    else:
        _run_interactive_mode(tree, args.model, args.port)


if __name__ == "__main__":
    main()
