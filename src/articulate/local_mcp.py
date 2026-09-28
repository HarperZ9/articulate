"""local_mcp.py - a zero-dependency MCP server over stdio JSON-RPC 2.0.

articulate already speaks MCP through ``mcp_server.build_server()``, which is
built on fastmcp. fastmcp is declared under the ``mcp`` extra, so a plain
``pip install articulate-writing`` produces a package whose MCP entry point
raises ``ModuleNotFoundError: No module named 'fastmcp'`` the moment a host
launches it. The install succeeds and the server does not start, which is the
worst shape for a defect: nothing fails until a user tries to use it.

This module serves the same five tools with nothing but the standard library,
so the package's MCP surface works from a bare install. It is not a second
implementation. The tool bodies stay in ``mcp_server`` as ``do_check``,
``do_score``, ``do_judge``, ``do_fix`` and ``do_polish``; both transports call
those same functions, so the two surfaces cannot drift apart in behavior.
Importing ``mcp_server`` is safe without fastmcp because that module imports it
lazily, inside ``build_server``.

``handle`` maps one request dict to one response dict and is testable without
pipes. ``serve`` is the thin stdio loop. stdout carries the protocol; anything
else belongs on stderr.
"""
from __future__ import annotations

import io
import json
import sys

from . import __version__
from .mcp_server import do_check, do_fix, do_judge, do_polish, do_score
from .mcp_server import _failure_note
from .tool_text import TOOLS as TOOL_TEXT
from .local_only import LocalOnly, refuse_if_local_only
from .local_only import local_only as _local_only_switch
from .tool_meta import TOOLS_VAR, tool_set
from .tool_meta import annotations as _annotations
from .tool_meta import is_listed as _listed

PROTOCOL = "2025-06-18"

_TEXT = {"text": {"type": "string", "description": "the passage to read"}}
_IS_HTML = {"is_html": {"type": "boolean", "default": False,
                        "description": "treat the input as HTML and preserve its markup"}}
_IS_TEX = {"is_tex": {"type": "boolean", "default": False,
                      "description": ("treat the input as LaTeX: mask every math span "
                                      "before each model call and restore it byte "
                                      "for byte")}}

_MAX_HITS = {"max_hits": {"type": "integer", "default": 50, "minimum": 0,
                          "maximum": 1000,
                          "description": ("the most findings to return in hits, which "
                                          "also stop at about 30,000 characters; the "
                                          "gate and rule_counts always cover every "
                                          "finding")}}

_SCHEMAS = {
    "check": {"type": "object", "required": ["text"],
              "properties": dict(_TEXT, **_MAX_HITS)},
    "score": {"type": "object", "required": ["text"], "properties": dict(_TEXT)},
    "judge": {"type": "object", "required": ["text"], "properties": dict(_TEXT)},
    "fix": {"type": "object", "required": ["text"],
            "properties": dict(_TEXT, **_IS_HTML, **_IS_TEX)},
    "polish": {"type": "object", "required": ["text"],
               "properties": dict(
                   _TEXT,
                   bar={"type": "integer", "default": 4, "minimum": 1, "maximum": 5,
                        "description": "the quality bar every dimension must clear"},
                   passes={"type": "integer", "default": 3, "minimum": 1,
                           "description": "how many rewrite attempts before giving up"},
                   **_IS_HTML, **_IS_TEX)},
    "articulate.status": {"type": "object", "properties": {}},
    "articulate.doctor": {"type": "object", "properties": {}},
}
# One description table serves both MCP servers (tool_text.TOOLS).
TOOLS = [{"name": name, "description": TOOL_TEXT[name], "inputSchema": schema}
         for name, schema in _SCHEMAS.items()]

# check and score read the text and nothing else. The rest call out to an editor
# backend, so a host with no backend still gets a working detector.
LOCAL_ONLY = ("check", "score")
NEEDS_BACKEND = ("judge", "fix", "polish")


def _ok(rid, result):
    return {"jsonrpc": "2.0", "id": rid, "result": result}


def _err(rid, code, message):
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}}


def _valid_request_id(value) -> bool:
    return type(value) is str or type(value) is int


def listed_tools(environ=None) -> list:
    """The tools/list payload: each listed tool with its title and behavior hints."""
    return [dict(tool, title=_annotations(tool["name"])["title"],
                 annotations=_annotations(tool["name"]))
            for tool in TOOLS if _listed(tool["name"], environ)]


def _backend_found() -> bool:
    from .claude_cli import ClaudeUnavailable, resolve
    try:
        resolve()
    except ClaudeUnavailable:
        return False
    return True


def _identity(include_detail: bool) -> dict:
    info = {"ok": True, "server": "articulate", "version": __version__,
            "protocol": PROTOCOL}
    if include_detail:
        info["tools"] = [t["name"] for t in listed_tools()]
        info["local_only"] = list(LOCAL_ONLY)
        info["needs_llm_backend"] = list(NEEDS_BACKEND)
        # Facts a user can paste into an issue. None of them is a path.
        info["tool_set"] = tool_set()
        info["hidden"] = [t["name"] for t in TOOLS if not _listed(t["name"])]
        info["python"] = "%d.%d.%d" % sys.version_info[:3]
        info["local_only_switch"] = _local_only_switch()
        if info["tool_set"] == "all":
            # Looked up on the PATH only when the hosted tools are listed, so the
            # local tool set never reads the file system.
            info["backend_cli_found"] = _backend_found()
    return info


def _text_arg(args: dict) -> str:
    text = args.get("text")
    if not isinstance(text, str):
        raise ValueError("'text' is required and must be a string")
    return text


def _call(params: dict) -> dict:
    name = params.get("name")
    args = params.get("arguments") or {}
    if not isinstance(args, dict):
        return {"content": [{"type": "text", "text": "'arguments' must be an object"}],
                "isError": True}
    if name in ("articulate.status", "articulate.doctor"):
        return _tool_result(_identity(name == "articulate.doctor"))
    if name in NEEDS_BACKEND:
        refused = _refused_by_switch()
        if refused is not None:
            return refused
    try:
        if name == "check":
            result = do_check(_text_arg(args), _max_hits(args))
        elif name == "score":
            result = do_score(_text_arg(args))
        elif name == "judge":
            result = do_judge(_text_arg(args))
        elif name == "fix":
            result = do_fix(_text_arg(args), bool(args.get("is_html", False)),
                            bool(args.get("is_tex", False)))
        elif name == "polish":
            result = do_polish(_text_arg(args), int(args.get("bar", 4)),
                               int(args.get("passes", 3)),
                               bool(args.get("is_html", False)),
                               bool(args.get("is_tex", False)))
        else:
            return {"content": [{"type": "text", "text": "unknown tool %r" % (name,)}],
                    "isError": True}
    except Exception as exc:          # a tool error is a result, not a dead server
        return {"content": [{"type": "text",
                             "text": "[error] %s: %s" % (type(exc).__name__, exc)}],
                "isError": True}
    return _tool_result(result)


def _refused_by_switch():
    """The result for a hosted tool under the local-only switch, or None.

    Checked before the tool body runs, so no body can write the text anywhere
    first, whatever it does before its model call."""
    try:
        refuse_if_local_only()
    except LocalOnly as exc:
        return _tool_result({"ok": False, "error": str(exc), "note": _failure_note(exc)})
    return None


def _max_hits(args: dict) -> int:
    value = args.get("max_hits")
    if value is None:                 # absent, or null from a client that sends one
        return 50
    if type(value) is not int or not 0 <= value <= 1000:
        raise ValueError("'max_hits' must be a whole number from 0 to 1000; the gate "
                         "and rule_counts always cover every finding")
    return value


def _tool_result(result: dict) -> dict:
    """One tool result as MCP content.

    Compact JSON keeps a long check inside a host's output cap, and non-ASCII
    text stays readable in the result. A result whose ok field is false is marked
    as an error, so a host never reads a failed call as a success.
    """
    out = {"content": [{"type": "text", "text": json.dumps(
        result, separators=(",", ":"), ensure_ascii=False)}]}
    if result.get("ok") is False:
        out["isError"] = True
    return out


def _call_listed(params: dict) -> dict:
    name = params.get("name")
    if isinstance(name, str) and not _listed(name):
        if _local_only_switch():
            # The Claude plugin sets both switches, and no setting a user can change
            # lists these tools there, so the message offers no how-to.
            text = "%s is not available: this server runs the local checks only." % name
        else:
            text = ("%s is not listed: %s=local lists only the tools that read the "
                    "text on this computer. Set %s=all to list the tools that send the "
                    "text to a hosted model." % (name, TOOLS_VAR, TOOLS_VAR))
        return {"content": [{"type": "text", "text": text}], "isError": True}
    return _call(params)


def handle(req):
    """Map one JSON-RPC request to a response dict, or None for a notification."""
    if not isinstance(req, dict):
        return _err(None, -32600, "invalid request")
    rid = req.get("id") if "id" in req and _valid_request_id(req.get("id")) else None
    if "id" in req and not _valid_request_id(req["id"]):
        return _err(None, -32600, "invalid request")
    if req.get("jsonrpc") != "2.0":
        return _err(rid, -32600, "invalid request")
    method = req.get("method")
    if not isinstance(method, str):
        return _err(rid, -32600, "invalid request: method must be a string")
    if "id" not in req:
        return None
    if method == "initialize":
        return _ok(rid, {"protocolVersion": PROTOCOL, "capabilities": {"tools": {}},
                         "serverInfo": {"name": "articulate", "version": __version__}})
    if method == "ping":
        return _ok(rid, {})
    if method == "tools/list":
        return _ok(rid, {"tools": listed_tools()})
    if method == "tools/call":
        params = req["params"] if "params" in req else {}
        if not isinstance(params, dict):
            return _err(rid, -32602, "invalid params")
        return _ok(rid, _call_listed(params))
    return _err(rid, -32601, "method not found: %s" % (method,))


# Some MCP servers name their request handler handle_request and others name it
# handle. Both names point at one function here, so there is no second code path
# to keep in step.
handle_request = handle


def _utf8(stream, **options):
    """Switch a standard stream to UTF-8, the encoding MCP messages use.

    Without this, Windows reads stdin in the console code page (cp1252 on an
    English install): a curly quote arrives as three wrong characters, the
    quotation exemption fails, and a quoted passage is reported as a finding.
    """
    try:
        stream.reconfigure(encoding="utf-8", **options)
    except (AttributeError, ValueError, io.UnsupportedOperation) as exc:
        sys.stderr.write("articulate-mcp: could not switch %s to UTF-8 (%s); non-ASCII "
                         "text may be misread\n" % (getattr(stream, "name", "a stream"), exc))
    return stream


def _respond(line: str):
    """The response to one request line, or None for a notification.

    A line the parser cannot read, deep nesting included, is a parse error. A
    failure while handling a request is an internal error, logged to stderr. The
    server answers either one and keeps serving.
    """
    try:
        req = json.loads(line)
    except (ValueError, RecursionError):
        return _err(None, -32700, "parse error")
    try:
        return handle(req)
    except Exception as exc:          # one failed request must not stop the server
        sys.stderr.write("articulate-mcp: internal error: %s: %s\n"
                         % (type(exc).__name__, exc))
        if not isinstance(req, dict) or "id" not in req:
            return None
        rid = req["id"] if _valid_request_id(req["id"]) else None
        return _err(rid, -32603, "internal error (%s)" % type(exc).__name__)


def serve(stdin=None, stdout=None) -> int:
    stdin = stdin if stdin is not None else _utf8(sys.stdin, errors="replace")
    stdout = stdout if stdout is not None else _utf8(sys.stdout, newline="\n")
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        resp = _respond(line)
        if resp is not None:
            stdout.write(json.dumps(resp) + "\n")
            stdout.flush()
    return 0


def main() -> int:
    return serve()


if __name__ == "__main__":
    raise SystemExit(main())
