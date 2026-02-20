"""Tests for codedocent.graph — import parsing, resolution, and graph building."""

from __future__ import annotations

import os

import pytest

from codedocent.graph import (
    ImportInfo,
    _extract_full_imports,
    _extract_module_docstring,
    _resolve_import,
    _find_modules,
    _aggregate_quality,
    _aggregate_summary,
    get_file_dependencies,
    get_module_graph,
    get_file_graph,
    export_architecture_md,
    export_module_md,
)
from codedocent.parser import CodeNode


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _make_file_node(
    name: str = "test.py",
    filepath: str | None = None,
    source: str = "x = 1\n",
    language: str = "python",
    quality: str | None = "clean",
    summary: str | None = None,
    imports: list[str] | None = None,
    children: list[CodeNode] | None = None,
    node_id: str | None = None,
) -> CodeNode:
    lines = source.splitlines()
    return CodeNode(
        name=name,
        node_type="file",
        language=language,
        filepath=filepath or name,
        start_line=1,
        end_line=len(lines),
        source=source,
        line_count=len(lines),
        quality=quality,
        summary=summary,
        imports=imports or [],
        children=children or [],
        node_id=node_id,
    )


def _make_dir_node(
    name: str = "project",
    children: list[CodeNode] | None = None,
    filepath: str | None = None,
) -> CodeNode:
    return CodeNode(
        name=name,
        node_type="directory",
        language=None,
        filepath=filepath or "/tmp/project",
        start_line=0,
        end_line=0,
        source="",
        line_count=0,
        children=children or [],
    )


# ---------------------------------------------------------------------------
# Import extraction tests
# ---------------------------------------------------------------------------


class TestExtractFullImports:
    """Tests for _extract_full_imports."""

    def test_absolute_import(self):
        source = "import os\nimport sys\n"
        result = _extract_full_imports(source, "python")
        assert len(result) == 2
        assert result[0] == ImportInfo("os", False, 0)
        assert result[1] == ImportInfo("sys", False, 0)

    def test_from_import_absolute(self):
        source = "from pathlib import Path\n"
        result = _extract_full_imports(source, "python")
        assert len(result) == 1
        assert result[0] == ImportInfo("pathlib", False, 0)

    def test_dotted_absolute_import(self):
        source = "from codedocent.parser import CodeNode\n"
        result = _extract_full_imports(source, "python")
        assert len(result) == 1
        assert result[0] == ImportInfo("codedocent.parser", False, 0)

    def test_relative_import_dot(self):
        source = "from . import sibling\n"
        result = _extract_full_imports(source, "python")
        assert len(result) == 1
        assert result[0].is_relative is True
        assert result[0].level == 1
        assert result[0].module == ""

    def test_relative_import_with_module(self):
        source = "from .sub import thing\n"
        result = _extract_full_imports(source, "python")
        assert len(result) == 1
        assert result[0].is_relative is True
        assert result[0].level == 1
        assert result[0].module == "sub"

    def test_relative_import_double_dot(self):
        source = "from ..parent import thing\n"
        result = _extract_full_imports(source, "python")
        assert len(result) == 1
        assert result[0].is_relative is True
        assert result[0].level == 2
        assert result[0].module == "parent"

    def test_mixed_imports(self):
        source = (
            "import os\n"
            "from pathlib import Path\n"
            "from .utils import helper\n"
            "from codedocent.parser import CodeNode\n"
        )
        result = _extract_full_imports(source, "python")
        assert len(result) == 4
        assert result[0] == ImportInfo("os", False, 0)
        assert result[1] == ImportInfo("pathlib", False, 0)
        assert result[2].is_relative is True
        assert result[2].module == "utils"
        assert result[3] == ImportInfo("codedocent.parser", False, 0)

    def test_non_python_returns_empty(self):
        result = _extract_full_imports("import foo", "javascript")
        assert result == []


# ---------------------------------------------------------------------------
# Import resolution tests
# ---------------------------------------------------------------------------


class TestResolveImport:
    """Tests for _resolve_import."""

    def setup_method(self):
        self.project_files = {
            "codedocent/__init__.py",
            "codedocent/parser.py",
            "codedocent/server.py",
            "codedocent/utils.py",
            "codedocent/sub/__init__.py",
            "codedocent/sub/helper.py",
            "setup.py",
        }
        self.project_modules = {"codedocent"}

    def test_stdlib_returns_none(self):
        info = ImportInfo("os", False, 0)
        result = _resolve_import(info, "codedocent/parser.py",
                                 self.project_files, self.project_modules)
        assert result is None

    def test_absolute_internal_resolves(self):
        info = ImportInfo("codedocent.parser", False, 0)
        result = _resolve_import(info, "setup.py",
                                 self.project_files, self.project_modules)
        assert result == "codedocent/parser.py"

    def test_absolute_package_resolves_to_init(self):
        info = ImportInfo("codedocent", False, 0)
        result = _resolve_import(info, "setup.py",
                                 self.project_files, self.project_modules)
        assert result == "codedocent/__init__.py"

    def test_external_returns_none(self):
        info = ImportInfo("numpy", False, 0)
        result = _resolve_import(info, "codedocent/parser.py",
                                 self.project_files, self.project_modules)
        assert result is None

    def test_relative_same_dir(self):
        info = ImportInfo("utils", True, 1)
        result = _resolve_import(info, "codedocent/parser.py",
                                 self.project_files, self.project_modules)
        assert result == "codedocent/utils.py"

    def test_relative_parent(self):
        info = ImportInfo("parser", True, 2)
        result = _resolve_import(info, "codedocent/sub/helper.py",
                                 self.project_files, self.project_modules)
        assert result == "codedocent/parser.py"

    def test_relative_package_init(self):
        info = ImportInfo("sub", True, 1)
        result = _resolve_import(info, "codedocent/parser.py",
                                 self.project_files, self.project_modules)
        assert result == "codedocent/sub/__init__.py"


# ---------------------------------------------------------------------------
# Module detection tests
# ---------------------------------------------------------------------------


class TestFindModules:
    """Tests for _find_modules."""

    def test_directories_with_init_are_modules(self):
        files = {
            "pkg/__init__.py",
            "pkg/main.py",
            "pkg/utils.py",
        }
        modules = _find_modules(files, "project")
        assert "pkg" in modules
        assert len(modules["pkg"]) == 3

    def test_directories_without_init_not_modules(self):
        files = {
            "scripts/run.py",
            "scripts/build.py",
        }
        modules = _find_modules(files, "project")
        # All files go under project root pseudo-module
        assert "project" in modules
        assert "scripts" not in modules

    def test_loose_files_under_root(self):
        files = {
            "setup.py",
            "README.md",
            "pkg/__init__.py",
            "pkg/core.py",
        }
        modules = _find_modules(files, "project")
        assert "project" in modules
        assert "setup.py" in modules["project"]
        assert "README.md" in modules["project"]
        assert "pkg" in modules
        assert "pkg/core.py" in modules["pkg"]


# ---------------------------------------------------------------------------
# Quality aggregation tests
# ---------------------------------------------------------------------------


class TestAggregateQuality:
    """Tests for _aggregate_quality."""

    def test_all_clean(self):
        nodes = [
            _make_file_node(quality="clean"),
            _make_file_node(quality="clean"),
        ]
        assert _aggregate_quality(nodes) == "clean"

    def test_worst_propagates(self):
        nodes = [
            _make_file_node(quality="clean"),
            _make_file_node(quality="warning"),
            _make_file_node(quality="complex"),
        ]
        assert _aggregate_quality(nodes) == "warning"

    def test_none_quality_treated_as_clean(self):
        nodes = [_make_file_node(quality=None)]
        assert _aggregate_quality(nodes) == "clean"


# ---------------------------------------------------------------------------
# Summary aggregation tests
# ---------------------------------------------------------------------------


class TestAggregateSummary:
    """Tests for _aggregate_summary."""

    def test_with_summaries(self):
        nodes = [
            _make_file_node(name="a.py", summary="Does thing A"),
            _make_file_node(name="b.py", summary="Does thing B"),
        ]
        result = _aggregate_summary("mymod", nodes)
        assert "a.py: Does thing A" in result
        assert "b.py: Does thing B" in result

    def test_without_summaries_fallback(self):
        nodes = [
            _make_file_node(name="a.py", summary=None),
            _make_file_node(name="b.py", summary=None),
        ]
        result = _aggregate_summary("mymod", nodes)
        assert "Module mymod with 2 files" in result

    def test_truncates_long_summaries(self):
        long_summary = "A" * 100
        nodes = [_make_file_node(summary=long_summary)]
        result = _aggregate_summary("mod", nodes)
        assert "..." in result

    def test_shows_remaining_count(self):
        nodes = [
            _make_file_node(name=f"f{i}.py", summary=f"Summary {i}")
            for i in range(5)
        ]
        result = _aggregate_summary("mod", nodes)
        assert "and 2 more" in result


# ---------------------------------------------------------------------------
# Graph construction tests
# ---------------------------------------------------------------------------


def _make_multi_module_tree():
    """Build a tree with two modules and cross-module imports."""
    # Module A: codedocent/
    init_a = _make_file_node(
        name="__init__.py",
        filepath="codedocent/__init__.py",
        source="",
        node_id="init_a",
    )
    parser_node = _make_file_node(
        name="parser.py",
        filepath="codedocent/parser.py",
        source="from codedocent.server import start_server\nx = 1\n",
        node_id="parser_node",
    )
    server_node = _make_file_node(
        name="server.py",
        filepath="codedocent/server.py",
        source="from codedocent.parser import CodeNode\nx = 1\n",
        node_id="server_node",
    )
    dir_a = _make_dir_node(
        name="codedocent",
        children=[init_a, parser_node, server_node],
        filepath="/tmp/project/codedocent",
    )

    # Module B: tests/
    init_b = _make_file_node(
        name="__init__.py",
        filepath="tests/__init__.py",
        source="",
        node_id="init_b",
    )
    test_file = _make_file_node(
        name="test_parser.py",
        filepath="tests/test_parser.py",
        source="from codedocent.parser import CodeNode\nimport pytest\n",
        node_id="test_parser",
    )
    dir_b = _make_dir_node(
        name="tests",
        children=[init_b, test_file],
        filepath="/tmp/project/tests",
    )

    root = _make_dir_node(
        name="project",
        children=[dir_a, dir_b],
        filepath="/tmp/project",
    )

    return root


class TestGetModuleGraph:
    """Tests for get_module_graph."""

    def test_correct_node_count(self):
        root = _make_multi_module_tree()
        graph = get_module_graph(root, "/tmp/project")
        # Should have codedocent and tests modules
        assert len(graph["nodes"]) == 2
        names = {n["name"] for n in graph["nodes"]}
        assert "codedocent" in names
        assert "tests" in names

    def test_correct_edge_count(self):
        root = _make_multi_module_tree()
        graph = get_module_graph(root, "/tmp/project")
        # tests -> codedocent edge (test_parser imports from codedocent.parser)
        assert len(graph["edges"]) >= 1
        # Check at least one cross-module edge exists
        cross_edges = [
            e for e in graph["edges"]
            if e["source"] != e["target"]
        ]
        assert len(cross_edges) >= 1

    def test_external_deps(self):
        root = _make_multi_module_tree()
        graph = get_module_graph(root, "/tmp/project")
        assert "pytest" in graph["external"]

    def test_stdlib_excluded_from_external_deps(self):
        """Stdlib modules should not appear in external dependencies."""
        root = _make_multi_module_tree()
        graph = get_module_graph(root, "/tmp/project")
        stdlib_names = {"os", "sys", "json", "pathlib", "collections", "re"}
        for dep in graph["external"]:
            assert dep not in stdlib_names, f"stdlib module '{dep}' in external deps"

    def test_module_stats(self):
        root = _make_multi_module_tree()
        graph = get_module_graph(root, "/tmp/project")
        cd_node = next(n for n in graph["nodes"] if n["name"] == "codedocent")
        assert cd_node["file_count"] == 3
        assert cd_node["node_type"] == "module"


class TestGetFileGraph:
    """Tests for get_file_graph."""

    def test_returns_file_nodes(self):
        root = _make_multi_module_tree()
        graph = get_file_graph(root, "/tmp/project", "codedocent")
        assert graph is not None
        file_nodes = [n for n in graph["nodes"] if n["node_type"] == "file"]
        assert len(file_nodes) == 3

    def test_ghost_nodes_for_external_deps(self):
        root = _make_multi_module_tree()
        graph = get_file_graph(root, "/tmp/project", "tests")
        assert graph is not None
        ghost_nodes = [n for n in graph["nodes"] if n["node_type"] == "external"]
        # test_parser.py imports from codedocent.parser, which is external to tests/
        assert len(ghost_nodes) >= 1

    def test_returns_none_for_invalid_module(self):
        root = _make_multi_module_tree()
        result = get_file_graph(root, "/tmp/project", "nonexistent")
        assert result is None

    def test_edges_between_files(self):
        root = _make_multi_module_tree()
        graph = get_file_graph(root, "/tmp/project", "codedocent")
        assert graph is not None
        # parser imports from server and vice versa
        assert len(graph["edges"]) >= 1

    def test_file_nodes_have_valid_node_ids(self):
        """File nodes in graph response must carry node_ids that match
        the CodeNode tree, so the interactive view can look them up."""
        root = _make_multi_module_tree()
        # Simulate what the server does: assign IDs first
        from codedocent.analyzer import assign_node_ids
        lookup = assign_node_ids(root)

        graph = get_file_graph(root, "/tmp/project", "codedocent")
        assert graph is not None
        file_nodes = [
            n for n in graph["nodes"] if n["node_type"] == "file"
        ]
        for fn in file_nodes:
            assert fn["node_id"] is not None, (
                f"{fn['name']} has node_id=None"
            )
            assert fn["node_id"] in lookup, (
                f"{fn['name']} node_id {fn['node_id']} not in lookup"
            )

    def test_ghost_nodes_have_valid_node_ids(self):
        """Ghost (external) nodes should also carry node_ids when the
        target file exists in the tree."""
        root = _make_multi_module_tree()
        from codedocent.analyzer import assign_node_ids
        lookup = assign_node_ids(root)

        graph = get_file_graph(root, "/tmp/project", "tests")
        assert graph is not None
        ghost_nodes = [
            n for n in graph["nodes"] if n["node_type"] == "external"
        ]
        for gn in ghost_nodes:
            # Ghost nodes referencing internal files should have IDs
            if gn["node_id"] is not None:
                assert gn["node_id"] in lookup


# ---------------------------------------------------------------------------
# Docstring extraction tests
# ---------------------------------------------------------------------------


class TestExtractModuleDocstring:
    """Tests for _extract_module_docstring."""

    def test_extracts_triple_double_quote_docstring(self):
        source = '"""Parse source files into a tree."""\nimport os\n'
        assert _extract_module_docstring(source) == "Parse source files into a tree."

    def test_extracts_triple_single_quote_docstring(self):
        source = "'''Helper utilities for scanning.'''\nimport sys\n"
        assert _extract_module_docstring(source) == "Helper utilities for scanning."

    def test_returns_empty_for_no_docstring(self):
        source = "import os\nx = 1\n"
        assert _extract_module_docstring(source) == ""

    def test_returns_first_line_of_multiline(self):
        source = '"""First line.\n\nMore detail here.\n"""\nimport os\n'
        assert _extract_module_docstring(source) == "First line."

    def test_truncates_long_docstring(self):
        long_text = "A" * 100
        source = f'"""{long_text}"""\n'
        result = _extract_module_docstring(source)
        assert len(result) <= 80
        assert result.endswith("...")

    def test_returns_empty_for_syntax_error(self):
        source = "def foo(:\n"
        assert _extract_module_docstring(source) == ""

    def test_returns_empty_for_empty_source(self):
        assert _extract_module_docstring("") == ""


# ---------------------------------------------------------------------------
# Context export tests
# ---------------------------------------------------------------------------


class TestExportArchitectureMd:
    """Tests for export_architecture_md."""

    def test_produces_valid_markdown(self):
        root = _make_multi_module_tree()
        md = export_architecture_md(root, "/tmp/project")
        assert "# Architecture Overview" in md
        assert "## Modules" in md
        assert "codedocent" in md
        assert "tests" in md

    def test_contains_modules_table(self):
        root = _make_multi_module_tree()
        md = export_architecture_md(root, "/tmp/project")
        assert "| Module | Files | Lines | Quality |" in md

    def test_contains_external_deps(self):
        root = _make_multi_module_tree()
        md = export_architecture_md(root, "/tmp/project")
        assert "pytest" in md

    def test_excludes_stdlib_from_external_deps(self):
        """Stdlib modules like os, sys should not appear in External Dependencies."""
        root = _make_multi_module_tree()
        md = export_architecture_md(root, "/tmp/project")
        # The test tree includes files that import os/sys but those are stdlib
        for line in md.splitlines():
            if line.startswith("- "):
                dep = line[2:].strip()
                assert dep not in ("os", "sys", "json", "pathlib")


class TestExportModuleMd:
    """Tests for export_module_md."""

    def test_produces_valid_markdown(self):
        root = _make_multi_module_tree()
        md = export_module_md(root, "/tmp/project", "codedocent")
        assert md is not None
        assert "# Module: codedocent" in md
        assert "## Files" in md

    def test_contains_purpose_column(self):
        root = _make_multi_module_tree()
        md = export_module_md(root, "/tmp/project", "codedocent")
        assert md is not None
        assert "| File | Lines | Quality | Purpose |" in md

    def test_returns_none_for_invalid_module(self):
        root = _make_multi_module_tree()
        result = export_module_md(root, "/tmp/project", "nonexistent")
        assert result is None

    def test_lists_files(self):
        root = _make_multi_module_tree()
        md = export_module_md(root, "/tmp/project", "codedocent")
        assert md is not None
        assert "parser.py" in md
        assert "server.py" in md

    def test_shows_docstring_in_purpose(self):
        """Files with module docstrings should show them in the Purpose column."""
        init_node = _make_file_node(
            name="__init__.py",
            filepath="mypkg/__init__.py",
            source='"""My package init."""\n',
            node_id="init",
        )
        core_node = _make_file_node(
            name="core.py",
            filepath="mypkg/core.py",
            source='"""Core business logic for the app."""\nimport os\nx = 1\n',
            node_id="core",
        )
        nodc_node = _make_file_node(
            name="utils.py",
            filepath="mypkg/utils.py",
            source="import os\nx = 1\n",
            node_id="utils",
        )
        dir_node = _make_dir_node(
            name="mypkg",
            children=[init_node, core_node, nodc_node],
            filepath="/tmp/project/mypkg",
        )
        root = _make_dir_node(
            name="project",
            children=[dir_node],
            filepath="/tmp/project",
        )
        md = export_module_md(root, "/tmp/project", "mypkg")
        assert md is not None
        assert "Core business logic for the app" in md
        # utils.py has no docstring -> em dash
        assert "\u2014" in md


# ---------------------------------------------------------------------------
# File dependency lookup tests
# ---------------------------------------------------------------------------


class TestGetFileDependencies:
    """Tests for get_file_dependencies."""

    def test_imports_from(self):
        root = _make_multi_module_tree()
        deps = get_file_dependencies(root, "/tmp/project", "codedocent/parser.py")
        assert "server.py" in deps["imports_from"]

    def test_imported_by(self):
        root = _make_multi_module_tree()
        deps = get_file_dependencies(root, "/tmp/project", "codedocent/parser.py")
        # server.py imports parser, test_parser.py imports parser
        assert "server.py" in deps["imported_by"]
        assert "test_parser.py" in deps["imported_by"]

    def test_empty_for_unused_file(self):
        root = _make_multi_module_tree()
        deps = get_file_dependencies(root, "/tmp/project", "codedocent/__init__.py")
        # __init__.py has no source imports in the mock
        assert deps["imports_from"] == []

    def test_results_are_sorted_and_deduplicated(self):
        root = _make_multi_module_tree()
        deps = get_file_dependencies(root, "/tmp/project", "codedocent/parser.py")
        assert deps["imported_by"] == sorted(set(deps["imported_by"]))
        assert deps["imports_from"] == sorted(set(deps["imports_from"]))
