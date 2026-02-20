"""Architecture graph: import parsing, resolution, and dependency graph building."""

from __future__ import annotations

import ast
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

import tree_sitter_language_pack as tslp

from codedocent.parser import CodeNode


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ImportInfo:
    """Represents a single import statement."""

    module: str          # Module path as written (e.g., "os", "codedocent.parser", "sub")
    is_relative: bool    # True for from . / from .. imports
    level: int           # Number of leading dots (0=absolute, 1=., 2=..)


@dataclass
class GraphNode:
    """A node in the architecture dependency graph."""

    id: str              # Module path or filename (unique key)
    name: str            # Display name
    path: str            # Relative path from project root
    node_type: str       # "module" | "file" | "external"
    line_count: int
    file_count: int      # For modules; 1 for files
    quality: str         # "clean" | "complex" | "warning"
    summary: str | None
    node_id: str | None  # CodeNode.node_id for linking to file views


@dataclass
class GraphEdge:
    """A directed edge in the architecture dependency graph."""

    source: str          # GraphNode.id of importer
    target: str          # GraphNode.id of imported
    weight: int          # Number of import statements
    imports: list[str] = field(default_factory=list)  # Actual import strings


# ---------------------------------------------------------------------------
# Import extraction
# ---------------------------------------------------------------------------


def _extract_full_imports(source: str, language: str) -> list[ImportInfo]:
    """Extract structured import information from Python source using tree-sitter.

    Handles all Python import forms:
    - import foo                    -> ImportInfo("foo", False, 0)
    - from foo.bar import baz       -> ImportInfo("foo.bar", False, 0)
    - from . import sibling         -> ImportInfo("", True, 1)
    - from .sub import thing        -> ImportInfo("sub", True, 1)
    - from ..parent import thing    -> ImportInfo("parent", True, 2)
    """
    if language != "python":
        return []

    try:
        parser = tslp.get_parser(language)  # type: ignore[arg-type]
    except (KeyError, ValueError):
        return []

    root = parser.parse(source.encode()).root_node
    results: list[ImportInfo] = []

    for child in root.children:
        if child.type == "import_statement":
            # import foo / import foo.bar
            for gc in child.children:
                if gc.type == "dotted_name":
                    results.append(ImportInfo(
                        module=gc.text.decode(),
                        is_relative=False,
                        level=0,
                    ))
        elif child.type == "import_from_statement":
            # from X import Y
            level = 0
            module = ""
            has_relative = False

            for gc in child.children:
                if gc.type == "relative_import":
                    has_relative = True
                    # Count dots and find module name
                    for ri_child in gc.children:
                        if ri_child.type == "import_prefix":
                            level = len(ri_child.text.decode())
                        elif ri_child.type == "dotted_name":
                            module = ri_child.text.decode()
                    break
                if gc.type == "dotted_name":
                    module = gc.text.decode()
                    break

            if has_relative:
                results.append(ImportInfo(
                    module=module,
                    is_relative=True,
                    level=level,
                ))
            elif module:
                results.append(ImportInfo(
                    module=module,
                    is_relative=False,
                    level=0,
                ))

    return results


# ---------------------------------------------------------------------------
# Import resolution
# ---------------------------------------------------------------------------

# Standard library modules (Python 3.10+)
_STDLIB_MODULES: frozenset[str] | None = None


def _get_stdlib_modules() -> frozenset[str]:
    """Return the set of stdlib module names."""
    global _STDLIB_MODULES  # noqa: PLW0603
    if _STDLIB_MODULES is None:
        if hasattr(sys, "stdlib_module_names"):
            _STDLIB_MODULES = frozenset(sys.stdlib_module_names)
        else:
            # Fallback for Python < 3.10
            _STDLIB_MODULES = frozenset({
                "os", "sys", "io", "re", "json", "math", "time", "datetime",
                "pathlib", "collections", "functools", "itertools", "typing",
                "abc", "copy", "hashlib", "logging", "unittest", "threading",
                "multiprocessing", "socket", "http", "urllib", "email",
                "argparse", "configparser", "dataclasses", "enum", "signal",
                "secrets", "shutil", "glob", "fnmatch", "tempfile",
                "subprocess", "webbrowser", "textwrap", "string", "struct",
                "csv", "xml", "html", "importlib", "inspect", "ast",
                "tokenize", "pdb", "profile", "traceback", "warnings",
                "contextlib", "pickle", "shelve", "sqlite3", "zipfile",
                "tarfile", "gzip", "bz2", "lzma", "base64", "binascii",
                "random", "statistics", "decimal", "fractions", "operator",
                "pprint", "dis", "code", "codeop", "compileall",
            })
    return _STDLIB_MODULES


def _resolve_import(
    info: ImportInfo,
    importing_file: str,
    project_files: set[str],
    project_modules: set[str],
) -> str | None:
    """Resolve an ImportInfo to a relative file path, or None if external.

    *importing_file* is the relative path of the file doing the import.
    *project_files* is the set of all relative file paths in the project.
    *project_modules* is the set of top-level module names in the project.
    """
    if info.is_relative:
        # Relative import: compute base from importing file
        parts = Path(importing_file).parts
        # Go up 'level' directories from the importing file's directory
        if info.level > 0:
            dir_parts = parts[:-1]  # drop filename
            if info.level <= len(dir_parts):
                base_parts = dir_parts[: len(dir_parts) - info.level + 1]
            else:
                return None
        else:
            base_parts = parts[:-1]

        if info.module:
            mod_parts = info.module.split(".")
            candidate_parts = list(base_parts) + mod_parts
        else:
            candidate_parts = list(base_parts)

        # Try module.py
        candidate_file = os.path.join(*candidate_parts) + ".py" if candidate_parts else None
        if candidate_file and candidate_file in project_files:
            return candidate_file

        # Try module/__init__.py
        candidate_init = os.path.join(*(candidate_parts + ["__init__.py"])) if candidate_parts else None
        if candidate_init and candidate_init in project_files:
            return candidate_init

        return None

    # Absolute import
    top_module = info.module.split(".")[0]

    # Check if it's a stdlib module
    if top_module in _get_stdlib_modules():
        return None

    # Check if it's a project module
    mod_parts = info.module.split(".")

    # Try module.replace(".", "/") + ".py"
    candidate = os.path.join(*mod_parts) + ".py"
    if candidate in project_files:
        return candidate

    # Try module.replace(".", "/") + "/__init__.py"
    candidate_init = os.path.join(*(mod_parts + ["__init__.py"]))
    if candidate_init in project_files:
        return candidate_init

    # Try progressively shorter prefixes (import codedocent.parser -> codedocent/parser.py)
    for i in range(len(mod_parts), 0, -1):
        candidate = os.path.join(*mod_parts[:i]) + ".py"
        if candidate in project_files:
            return candidate
        candidate_init = os.path.join(*(mod_parts[:i] + ["__init__.py"]))
        if candidate_init in project_files:
            return candidate_init

    return None


# ---------------------------------------------------------------------------
# Module detection
# ---------------------------------------------------------------------------


def _find_modules(project_files: set[str], project_root_name: str) -> dict[str, list[str]]:
    """Detect modules (directories with __init__.py) and map files to modules.

    Returns a dict mapping module_path -> list of file paths in that module.
    Files not inside any module go under a pseudo-module named after the project root.
    """
    # Find all directories that contain __init__.py
    module_dirs: set[str] = set()
    for f in project_files:
        if os.path.basename(f) == "__init__.py":
            module_dir = os.path.dirname(f)
            if module_dir:
                module_dirs.add(module_dir)

    # Map each file to its module
    modules: dict[str, list[str]] = {}

    for f in sorted(project_files):
        # Find the deepest module directory this file belongs to
        best_module = ""
        fdir = os.path.dirname(f)
        for md in module_dirs:
            if fdir == md or fdir.startswith(md + os.sep):
                if len(md) > len(best_module):
                    best_module = md

        if best_module:
            modules.setdefault(best_module, []).append(f)
        else:
            # Loose file -> project root pseudo-module
            modules.setdefault(project_root_name, []).append(f)

    return modules


def _file_to_module(filepath: str, modules: dict[str, list[str]]) -> str:
    """Return the module path a file belongs to."""
    for mod_path, files in modules.items():
        if filepath in files:
            return mod_path
    return ""


# ---------------------------------------------------------------------------
# Quality aggregation
# ---------------------------------------------------------------------------


def _aggregate_quality(file_nodes: list[CodeNode]) -> str:
    """Return the worst quality label among file nodes."""
    order = {"clean": 0, "complex": 1, "warning": 2}
    worst = "clean"
    for node in file_nodes:
        q = node.quality or "clean"
        if order.get(q, 0) > order.get(worst, 0):
            worst = q
    return worst


# ---------------------------------------------------------------------------
# Summary aggregation
# ---------------------------------------------------------------------------


def _aggregate_summary(name: str, file_nodes: list[CodeNode]) -> str:
    """Build an aggregated summary for a module from its file summaries."""
    summaries = []
    for node in file_nodes:
        if node.summary:
            text = node.summary
            if len(text) > 80:
                text = text[:77] + "..."
            summaries.append(f"{node.name}: {text}")
            if len(summaries) >= 3:
                break

    remaining = len(file_nodes) - len(summaries)
    if summaries:
        result = "; ".join(summaries)
        if remaining > 0:
            result += f" ... and {remaining} more"
        return result
    return f"Module {name} with {len(file_nodes)} files"


# ---------------------------------------------------------------------------
# Tree helpers
# ---------------------------------------------------------------------------


def _collect_file_nodes(node: CodeNode) -> list[CodeNode]:
    """Collect all file-type nodes from a CodeNode tree."""
    results: list[CodeNode] = []
    if node.node_type == "file":
        results.append(node)
    for child in node.children:
        results.extend(_collect_file_nodes(child))
    return results


def _find_file_node(root: CodeNode, rel_path: str) -> CodeNode | None:
    """Find a file node by its relative filepath."""
    if root.node_type == "file" and root.filepath == rel_path:
        return root
    for child in root.children:
        found = _find_file_node(child, rel_path)
        if found is not None:
            return found
    return None


def _build_project_files(root: CodeNode) -> set[str]:
    """Collect relative file paths from the tree."""
    files = set()
    for node in _collect_file_nodes(root):
        if node.filepath:
            files.add(node.filepath)
    return files


# ---------------------------------------------------------------------------
# Graph builders
# ---------------------------------------------------------------------------


def get_module_graph(root: CodeNode, project_root: str) -> dict:
    """Build the Level 0 (module-level) dependency graph.

    Returns {"nodes": [...], "edges": [...], "external": [...]}.
    """
    project_root_name = os.path.basename(project_root) or project_root
    file_nodes = _collect_file_nodes(root)
    project_files = {n.filepath for n in file_nodes if n.filepath}
    project_modules_top = {
        f.split(os.sep)[0] for f in project_files if os.sep in f
    }

    modules = _find_modules(project_files, project_root_name)
    external_deps: set[str] = set()

    # Build file-to-file edges
    file_edges: dict[tuple[str, str], list[str]] = {}  # (source, target) -> import strings

    for fnode in file_nodes:
        if not fnode.filepath or not fnode.source or fnode.language != "python":
            continue
        imports = _extract_full_imports(fnode.source, fnode.language)
        for imp in imports:
            resolved = _resolve_import(
                imp, fnode.filepath, project_files, project_modules_top,
            )
            if resolved is None:
                # External dependency (skip stdlib)
                if not imp.is_relative:
                    top = imp.module.split(".")[0]
                    if top not in _get_stdlib_modules():
                        external_deps.add(top)
                continue
            if resolved != fnode.filepath:
                key = (fnode.filepath, resolved)
                imp_str = imp.module if imp.module else f".{'.' * (imp.level - 1)}"
                file_edges.setdefault(key, []).append(imp_str)

    # Aggregate file edges into module edges
    module_edges: dict[tuple[str, str], list[str]] = {}
    for (src_file, tgt_file), imp_strs in file_edges.items():
        src_mod = _file_to_module(src_file, modules)
        tgt_mod = _file_to_module(tgt_file, modules)
        if src_mod and tgt_mod and src_mod != tgt_mod:
            key = (src_mod, tgt_mod)
            module_edges.setdefault(key, []).extend(imp_strs)

    # Build nodes
    nodes: list[dict] = []
    for mod_path, mod_files in sorted(modules.items()):
        mod_file_nodes = [
            fn for fn in file_nodes if fn.filepath in mod_files
        ]
        mod_name = os.path.basename(mod_path) if mod_path != project_root_name else project_root_name
        total_lines = sum(fn.line_count for fn in mod_file_nodes)

        # Find directory node for this module to get its node_id
        mod_node_id = None
        for fn in mod_file_nodes:
            if fn.name == "__init__.py" and fn.node_id:
                mod_node_id = fn.node_id
                break

        nodes.append({
            "id": mod_path,
            "name": mod_name,
            "path": mod_path,
            "node_type": "module",
            "line_count": total_lines,
            "file_count": len(mod_file_nodes),
            "quality": _aggregate_quality(mod_file_nodes),
            "summary": _aggregate_summary(mod_name, mod_file_nodes),
            "node_id": mod_node_id,
        })

    # Build edges
    edges: list[dict] = []
    for (src, tgt), imp_strs in sorted(module_edges.items()):
        edges.append({
            "source": src,
            "target": tgt,
            "weight": len(imp_strs),
            "imports": sorted(set(imp_strs)),
        })

    return {
        "nodes": nodes,
        "edges": edges,
        "external": sorted(external_deps),
    }


def get_file_graph(
    root: CodeNode, project_root: str, module_path: str,
) -> dict | None:
    """Build the Level 1 (file-level) graph for a specific module.

    Returns {"nodes": [...], "edges": [...]} or None if module not found.
    """
    project_root_name = os.path.basename(project_root) or project_root
    file_nodes = _collect_file_nodes(root)
    project_files = {n.filepath for n in file_nodes if n.filepath}
    project_modules_top = {
        f.split(os.sep)[0] for f in project_files if os.sep in f
    }

    modules = _find_modules(project_files, project_root_name)

    if module_path not in modules:
        return None

    module_files = set(modules[module_path])

    # Build file nodes
    nodes: list[dict] = []
    ghost_nodes: set[str] = set()

    for fnode in file_nodes:
        if fnode.filepath not in module_files:
            continue
        nodes.append({
            "id": fnode.filepath,
            "name": fnode.name,
            "path": fnode.filepath,
            "node_type": "file",
            "line_count": fnode.line_count,
            "file_count": 1,
            "quality": fnode.quality or "clean",
            "summary": fnode.summary,
            "node_id": fnode.node_id,
        })

    # Build file-to-file edges
    edges: list[dict] = []
    for fnode in file_nodes:
        if fnode.filepath not in module_files:
            continue
        if not fnode.source or fnode.language != "python":
            continue
        imports = _extract_full_imports(fnode.source, fnode.language)
        edge_map: dict[str, list[str]] = {}
        for imp in imports:
            resolved = _resolve_import(
                imp, fnode.filepath, project_files, project_modules_top,
            )
            if resolved is None:
                continue
            if resolved == fnode.filepath:
                continue
            imp_str = imp.module if imp.module else f".{'.' * (imp.level - 1)}"
            edge_map.setdefault(resolved, []).append(imp_str)

        for target, imp_strs in edge_map.items():
            if target not in module_files:
                # Ghost node from another module
                if target not in ghost_nodes:
                    ghost_nodes.add(target)
                    tgt_node = _find_file_node(root, target)
                    nodes.append({
                        "id": target,
                        "name": os.path.basename(target),
                        "path": target,
                        "node_type": "external",
                        "line_count": tgt_node.line_count if tgt_node else 0,
                        "file_count": 1,
                        "quality": (tgt_node.quality or "clean") if tgt_node else "clean",
                        "summary": None,
                        "node_id": tgt_node.node_id if tgt_node else None,
                    })
            edges.append({
                "source": fnode.filepath,
                "target": target,
                "weight": len(imp_strs),
                "imports": sorted(set(imp_strs)),
            })

    return {"nodes": nodes, "edges": edges}


# ---------------------------------------------------------------------------
# File dependency lookup
# ---------------------------------------------------------------------------


def get_file_dependencies(
    root: CodeNode, project_root: str, filepath: str,
) -> dict[str, list[str]]:
    """Return import relationships for a single file.

    Returns ``{"imports_from": [...], "imported_by": [...]}``.
    File names are basenames (e.g. ``"parser.py"``).
    """
    file_nodes = _collect_file_nodes(root)
    project_files = {n.filepath for n in file_nodes if n.filepath}
    project_modules_top = {
        f.split(os.sep)[0] for f in project_files if os.sep in f
    }

    imports_from: list[str] = []
    imported_by: list[str] = []

    for fnode in file_nodes:
        if not fnode.filepath or not fnode.source or fnode.language != "python":
            continue
        imports = _extract_full_imports(fnode.source, fnode.language)
        for imp in imports:
            resolved = _resolve_import(
                imp, fnode.filepath, project_files, project_modules_top,
            )
            if resolved is None:
                continue
            if fnode.filepath == filepath and resolved != filepath:
                imports_from.append(os.path.basename(resolved))
            elif resolved == filepath and fnode.filepath != filepath:
                imported_by.append(os.path.basename(fnode.filepath))

    return {
        "imports_from": sorted(set(imports_from)),
        "imported_by": sorted(set(imported_by)),
    }


# ---------------------------------------------------------------------------
# Docstring extraction
# ---------------------------------------------------------------------------


def _extract_module_docstring(source: str) -> str:
    """Extract the module-level docstring from Python source.

    Returns the first line of the docstring, truncated to 80 characters.
    Returns an empty string if no docstring is found.
    """
    try:
        tree = ast.parse(source)
        docstring = ast.get_docstring(tree)
        if docstring:
            first_line = docstring.split("\n")[0].strip()
            if len(first_line) > 80:
                return first_line[:77] + "..."
            return first_line
    except SyntaxError:
        pass
    return ""


# ---------------------------------------------------------------------------
# Context export
# ---------------------------------------------------------------------------


def export_architecture_md(root: CodeNode, project_root: str) -> str:
    """Export Level 0 architecture as markdown."""
    graph = get_module_graph(root, project_root)

    lines = ["# Architecture Overview\n"]

    # Modules table
    lines.append("## Modules\n")
    lines.append("| Module | Files | Lines | Quality |")
    lines.append("|--------|-------|-------|---------|")
    for node in graph["nodes"]:
        quality_icon = {"clean": "OK", "complex": "Complex", "warning": "Warning"}.get(
            node["quality"], "OK"
        )
        lines.append(
            f"| {node['name']} | {node['file_count']} | "
            f"{node['line_count']} | {quality_icon} |"
        )

    # Dependencies table
    if graph["edges"]:
        lines.append("\n## Dependencies\n")
        lines.append("| From | To | Imports |")
        lines.append("|------|----|---------|")
        for edge in graph["edges"]:
            src_name = os.path.basename(edge["source"])
            tgt_name = os.path.basename(edge["target"])
            imports_str = ", ".join(edge["imports"][:5])
            if len(edge["imports"]) > 5:
                imports_str += f" (+{len(edge['imports']) - 5} more)"
            lines.append(f"| {src_name} | {tgt_name} | {imports_str} |")

    # External dependencies
    if graph["external"]:
        lines.append("\n## External Dependencies\n")
        for ext in graph["external"]:
            lines.append(f"- {ext}")

    lines.append("")
    return "\n".join(lines)


def export_module_md(
    root: CodeNode, project_root: str, module_path: str,
) -> str | None:
    """Export Level 1 module detail as markdown."""
    graph = get_file_graph(root, project_root, module_path)
    if graph is None:
        return None

    # Build filepath -> docstring lookup for Purpose column
    docstrings: dict[str, str] = {}
    for node in graph["nodes"]:
        if node["node_type"] == "external":
            continue
        fnode = _find_file_node(root, node["id"])
        if fnode and fnode.source and fnode.language == "python":
            docstrings[node["id"]] = _extract_module_docstring(fnode.source)

    mod_name = os.path.basename(module_path)
    lines = [f"# Module: {mod_name}\n"]

    # Files table
    lines.append("## Files\n")
    lines.append("| File | Lines | Quality | Purpose |")
    lines.append("|------|-------|---------|---------|")
    for node in graph["nodes"]:
        if node["node_type"] == "external":
            continue
        quality_label = {"clean": "OK", "complex": "Complex", "warning": "Warning"}.get(
            node["quality"], "OK"
        )
        purpose = docstrings.get(node["id"], "") or "\u2014"
        lines.append(
            f"| {node['name']} | {node['line_count']} "
            f"| {quality_label} | {purpose} |"
        )

    # Internal dependencies
    internal_edges = [
        e for e in graph["edges"]
        if not any(n["id"] == e["target"] and n["node_type"] == "external"
                   for n in graph["nodes"])
    ]
    if internal_edges:
        lines.append("\n## Internal Dependencies\n")
        lines.append("| From | To | Imports |")
        lines.append("|------|----|---------|")
        for edge in internal_edges:
            lines.append(
                f"| {os.path.basename(edge['source'])} "
                f"| {os.path.basename(edge['target'])} "
                f"| {', '.join(edge['imports'])} |"
            )

    # External dependencies (ghost nodes)
    external_edges = [
        e for e in graph["edges"]
        if any(n["id"] == e["target"] and n["node_type"] == "external"
               for n in graph["nodes"])
    ]
    if external_edges:
        lines.append("\n## External Dependencies\n")
        for edge in external_edges:
            lines.append(
                f"- {os.path.basename(edge['source'])} -> "
                f"{os.path.basename(edge['target'])}"
            )

    lines.append("")
    return "\n".join(lines)
