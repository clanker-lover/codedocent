# Security Model

**Cross-cutting concept appearing in**: [server.py](../summaries/server.md), [editor.py](../summaries/editor.md), [cloud_ai.py](../summaries/cloud_ai.md), [renderer.py](../summaries/renderer.md)

## Facts

Codedocent implements multiple security layers, primarily around the localhost HTTP server and code editing features.

### Server Security (source: server.py)
- **CSRF protection**: 32-byte `secrets.token_urlsafe` token required on all API endpoints via `X-Codedocent-Token` header (source: server.py:520, 315-319)
- **Host header validation**: rejects requests with Host headers other than `127.0.0.1`, `localhost`, `::1` (source: server.py:296-300)
- **Bind address**: server binds to `127.0.0.1` only, not `0.0.0.0` (source: server.py:573-575)
- **Request body limits**: max 10 MB body size, rejected before reading (source: server.py:23, 459-464)
- **Connection timeout**: 30-second read timeout on request bodies (source: server.py:465)

### Code Replacement Security (source: server.py:194-269, editor.py)
- **Path traversal prevention**: resolved real path must be within the project directory (source: server.py:229-236)
- **Symlink escape detection**: `os.path.realpath` used to follow symlinks before path check (source: server.py:219-220)
- **Template protection**: files inside codedocent's own `templates/` directory cannot be replaced (source: server.py:221-228)
- **Source size limit**: replacement source capped at 1 MB (source: server.py:213-217)
- **Directory rejection**: directory nodes cannot be replaced (source: server.py:204-209)
- **External modification detection**: mtime+size check prevents overwriting concurrent edits (source: editor.py:67-69)
- **Backup before write**: timestamped `.bak` file created before every modification (source: editor.py:71-76)
- **Atomic writes**: temp file + `os.replace` prevents partial writes (source: editor.py:104-118)
- **Symlink-safe backups**: `O_CREAT | O_EXCL | O_NOFOLLOW` flags prevent symlink attacks on backup paths (source: editor.py:77-79)

### API Key Security (source: cloud_ai.py)
- **Masked secrets**: `_MaskedSecret` wraps API keys so `repr()` and `str()` return `***` (source: cloud_ai.py:59-81)
- **Error message sanitization**: API keys never appear in error messages (source: cloud_ai.py:156-173, verified by test_cloud_ai.py:236-253)
- **Endpoint validation**: non-HTTPS endpoints rejected except for loopback addresses (source: cloud_ai.py:83-112)

### HTML Security
- **XSS prevention**: Jinja2 `autoescape=True` prevents script injection via node names (source: renderer.py:53, verified by test_renderer.py:261-293)

## Inferences

The security model is thorough for a tool that runs on localhost. The CSRF token, host validation, and bind-to-localhost combination form a defense-in-depth against DNS rebinding attacks. The code replacement guards are particularly careful -- multiple tests verify symlink escapes, path traversal, and template protection.

## Open Questions

- No rate limiting on AI requests -- a script could trigger many expensive API calls
- Idle timeout (5 minutes) is the only session expiration mechanism
