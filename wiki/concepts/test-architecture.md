# Test Architecture

**Cross-cutting concept appearing in**: all `tests/test_*.py` files

## Facts

The test suite uses pytest and covers all source modules. 10 test files with approximately 150+ test cases.

### Test File Mapping
| Test File | Module Under Test | Focus |
|-----------|-------------------|-------|
| `test_scanner.py` | scanner | File discovery, gitignore, binary detection, FIFO handling |
| `test_parser.py` | parser | Python/JS/TS AST parsing, imports, exports, arrow functions |
| `test_renderer.py` | renderer | HTML output, escaping, code buttons, interactive rendering |
| `test_analyzer.py` | analyzer | Prompts, response parsing, caching, timeouts, quality scoring |
| `test_cli.py` | cli | Wizard flow, arg parsing, cloud config building |
| `test_server.py` | server | HTTP endpoints, CSRF, replace, symlink escapes, graph API |
| `test_cloud_ai.py` | cloud_ai | Request formatting, error handling, endpoint validation, key masking |
| `test_editor.py` | editor | File replacement, backups, line endings, atomic writes |
| `test_gui.py` | gui | Import checks, tkinter fallback, structural tests |
| `test_graph.py` | graph | Import extraction/resolution, module detection, graph construction |

### Testing Patterns
- **Mock-heavy for AI**: `unittest.mock.patch` on `ollama.chat` and `urllib.request.urlopen` (source: test_analyzer.py, test_cloud_ai.py)
- **Real filesystem**: `tmp_path` fixture used extensively for file I/O tests (source: test_editor.py, test_scanner.py)
- **Integration tests**: actual HTTP server started in background thread for server tests (source: test_server.py:134-178)
- **Factory functions**: `_make_func_node`, `_make_file_node`, `_make_dir_node`, `_make_tree` helper factories reused across test files
- **Security-focused**: explicit tests for CSRF, symlink escapes, path traversal, XSS, oversized payloads, API key leakage

## Inferences

The test suite is notably security-conscious. Multiple test files include sections labeled "Security audit fixes" suggesting a systematic security review was performed.

The server integration tests are genuinely end-to-end: they start a real HTTP server, make real HTTP requests, and verify real responses. This is more robust than mocking the HTTP layer.

No test file tests the templates themselves (HTML structure, D3 behavior) -- those would require browser-level testing.
