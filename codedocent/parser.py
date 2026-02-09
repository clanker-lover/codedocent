"""Parse source files into a tree of CodeNodes using tree-sitter."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import tree_sitter_language_pack as tslp

from codedocent.scanner import ScannedFile


@dataclass
class CodeNode:
    name: str
    node_type: str  # 'directory' | 'file' | 'class' | 'function' | 'method'
    language: str | None
    filepath: str | None
    start_line: int  # 1-indexed
    end_line: int  # 1-indexed, inclusive
    source: str  # actual source code of this node
    children: list[CodeNode] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    line_count: int = 0
    # Filled in by analyzer later:
    summary: str | None = None
    pseudocode: str | None = None
    quality: str | None = None  # 'clean' | 'complex' | 'warning'
    warnings: list[str] | None = None


# ---------------------------------------------------------------------------
# Language-specific AST extraction rules
# ---------------------------------------------------------------------------

# Maps tree-sitter node types to our node_type values, and how to find the name
# key: (ts_node_type,) -> (our_node_type, name_child_type)
_PYTHON_RULES: dict[str, tuple[str, str]] = {
    "function_definition": ("function", "identifier"),
    "class_definition": ("class", "identifier"),
}

_JS_TS_RULES: dict[str, tuple[str, str]] = {
    "function_declaration": ("function", "identifier"),
    "class_declaration": ("class", "identifier"),
}

# Node types that contain the body / children of a class
_CLASS_BODY_TYPES: dict[str, str] = {
    "python": "block",
    "javascript": "class_body",
    "typescript": "class_body",
    "tsx": "class_body",
}

# Method definition node types inside class bodies
_METHOD_TYPES: dict[str, dict[str, str]] = {
    "python": {"function_definition": "identifier"},
    "javascript": {"method_definition": "property_identifier"},
    "typescript": {"method_definition": "property_identifier"},
    "tsx": {"method_definition": "property_identifier"},
}


def _rules_for(language: str) -> dict[str, tuple[str, str]]:
    if language == "python":
        return _PYTHON_RULES
    if language in ("javascript", "typescript", "tsx"):
        return _JS_TS_RULES
    return {}


# ---------------------------------------------------------------------------
# Import extraction
# ---------------------------------------------------------------------------

def _extract_imports_python(root_node) -> list[str]:
    """Extract imported module names from a Python AST."""
    imports: list[str] = []
    for child in root_node.children:
        if child.type == "import_statement":
            for gc in child.children:
                if gc.type == "dotted_name":
                    imports.append(gc.text.decode())
        elif child.type == "import_from_statement":
            for gc in child.children:
                if gc.type == "dotted_name":
                    imports.append(gc.text.decode())
                    break  # only the module name, not the imported symbols
    return imports


def _extract_imports_js(root_node) -> list[str]:
    """Extract imported module paths from a JS/TS AST."""
    imports: list[str] = []
    for child in root_node.children:
        if child.type == "import_statement":
            for gc in child.children:
                if gc.type == "string":
                    # strip quotes
                    text = gc.text.decode().strip("'\"")
                    imports.append(text)
    return imports


def _extract_imports(root_node, language: str) -> list[str]:
    if language == "python":
        return _extract_imports_python(root_node)
    if language in ("javascript", "typescript", "tsx"):
        return _extract_imports_js(root_node)
    return []


# ---------------------------------------------------------------------------
# Arrow-function extraction (JS/TS)
# ---------------------------------------------------------------------------

def _extract_arrow_functions(root_node, language: str) -> list[CodeNode]:
    """Find top-level `const name = () => ...` declarations."""
    if language not in ("javascript", "typescript", "tsx"):
        return []
    results: list[CodeNode] = []
    for child in root_node.children:
        if child.type != "lexical_declaration":
            continue
        for decl in child.children:
            if decl.type != "variable_declarator":
                continue
            name_node = None
            has_arrow = False
            for part in decl.children:
                if part.type == "identifier":
                    name_node = part
                if part.type == "arrow_function":
                    has_arrow = True
            if name_node and has_arrow:
                results.append(CodeNode(
                    name=name_node.text.decode(),
                    node_type="function",
                    language=language,
                    filepath=None,  # filled by caller
                    start_line=child.start_point[0] + 1,
                    end_line=child.end_point[0] + 1,
                    source=child.text.decode(),
                    line_count=child.end_point[0] - child.start_point[0] + 1,
                ))
    return results


# ---------------------------------------------------------------------------
# Name extraction helper
# ---------------------------------------------------------------------------

def _find_child_text(node, child_type: str) -> str:
    """Find the first child of the given type and return its text."""
    for child in node.children:
        if child.type == child_type:
            return child.text.decode()
    return "<anonymous>"


# ---------------------------------------------------------------------------
# Method extraction from class body
# ---------------------------------------------------------------------------

def _extract_methods(class_node, language: str) -> list[CodeNode]:
    """Extract method nodes from a class body."""
    body_type = _CLASS_BODY_TYPES.get(language)
    method_map = _METHOD_TYPES.get(language, {})
    if not body_type or not method_map:
        return []

    body = None
    for child in class_node.children:
        if child.type == body_type:
            body = child
            break
    if body is None:
        return []

    methods: list[CodeNode] = []
    for child in body.children:
        if child.type in method_map:
            name_type = method_map[child.type]
            methods.append(CodeNode(
                name=_find_child_text(child, name_type),
                node_type="method",
                language=language,
                filepath=None,
                start_line=child.start_point[0] + 1,
                end_line=child.end_point[0] + 1,
                source=child.text.decode(),
                line_count=child.end_point[0] - child.start_point[0] + 1,
            ))
    return methods


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_file(filepath: str, language: str, source: str | None = None) -> CodeNode:
    """Parse a single source file and return a file-level CodeNode.

    If *source* is provided it is used directly; otherwise the file is read
    from disk.
    """
    if source is None:
        with open(filepath) as f:
            source = f.read()

    source_bytes = source.encode()
    lines = source.splitlines()
    line_count = len(lines)

    # Build the file-level node
    file_node = CodeNode(
        name=os.path.basename(filepath),
        node_type="file",
        language=language,
        filepath=filepath,
        start_line=1,
        end_line=line_count,
        source=source,
        line_count=line_count,
    )

    # Languages we can parse with tree-sitter
    parseable = _rules_for(language)
    if not parseable:
        return file_node

    try:
        parser = tslp.get_parser(language)
    except Exception:
        return file_node

    tree = parser.parse(source_bytes)
    root = tree.root_node

    # Extract imports
    file_node.imports = _extract_imports(root, language)

    # Walk top-level children for classes/functions
    for child in root.children:
        if child.type in parseable:
            our_type, name_child = parseable[child.type]
            node = CodeNode(
                name=_find_child_text(child, name_child),
                node_type=our_type,
                language=language,
                filepath=filepath,
                start_line=child.start_point[0] + 1,
                end_line=child.end_point[0] + 1,
                source=child.text.decode(),
                line_count=child.end_point[0] - child.start_point[0] + 1,
            )
            # If it's a class, extract methods as children
            if our_type == "class":
                node.children = _extract_methods(child, language)
                for m in node.children:
                    m.filepath = filepath
            file_node.children.append(node)

    # Arrow functions (JS/TS)
    arrows = _extract_arrow_functions(root, language)
    for a in arrows:
        a.filepath = filepath
    file_node.children.extend(arrows)

    # Sort children by start_line
    file_node.children.sort(key=lambda n: n.start_line)

    return file_node


def parse_directory(scanned_files: list[ScannedFile], root: str | None = None) -> CodeNode:
    """Build a full tree with directory nodes from scanner output.

    *root* is the base directory path. If not provided, it's inferred from
    the common prefix of file paths.
    """
    if root is None:
        root = "."

    root_path = str(Path(root).resolve())
    root_name = os.path.basename(root_path) or root_path

    dir_node = CodeNode(
        name=root_name,
        node_type="directory",
        language=None,
        filepath=root_path,
        start_line=0,
        end_line=0,
        source="",
        line_count=0,
    )

    # Build a tree of directories, then attach file parse results
    dir_nodes: dict[str, CodeNode] = {"": dir_node}

    for sf in scanned_files:
        # Ensure parent directory nodes exist
        parts = Path(sf.filepath).parts
        for i in range(len(parts) - 1):
            dir_key = os.path.join(*parts[: i + 1])
            if dir_key not in dir_nodes:
                parent_key = os.path.join(*parts[:i]) if i > 0 else ""
                d = CodeNode(
                    name=parts[i],
                    node_type="directory",
                    language=None,
                    filepath=os.path.join(root_path, dir_key),
                    start_line=0,
                    end_line=0,
                    source="",
                    line_count=0,
                )
                dir_nodes[parent_key].children.append(d)
                dir_nodes[dir_key] = d

        # Parse the file
        abs_path = os.path.join(root_path, sf.filepath)
        file_node = parse_file(abs_path, sf.language)
        file_node.filepath = sf.filepath  # store relative path

        # Attach to parent directory
        parent_key = os.path.join(*parts[:-1]) if len(parts) > 1 else ""
        dir_nodes[parent_key].children.append(file_node)

    # Sort all directory children: dirs first, then files, alphabetically
    def _sort_children(node: CodeNode) -> None:
        node.children.sort(key=lambda n: (0 if n.node_type == "directory" else 1, n.name))
        for child in node.children:
            if child.node_type == "directory":
                _sort_children(child)

    _sort_children(dir_node)

    # Accumulate line counts up the tree
    def _accumulate(node: CodeNode) -> int:
        if node.node_type in ("directory",):
            total = sum(_accumulate(c) for c in node.children)
            node.line_count = total
            return total
        return node.line_count

    _accumulate(dir_node)

    return dir_node
