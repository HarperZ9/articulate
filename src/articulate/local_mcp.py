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

import json
import sys

from . import __version__
from .mcp_server import do_check, do_fix, do_judge, do_polish, do_score

PROTOCOL = "2025-06-18"

_TEXT = {"text": {"type": "string", "description": "the passage to read"}}
_IS_HTML = {"is_html": {"type": "boolean", "default": False,
                        "description": "treat the input as HTML and preserve its markup"}}

TOOLS = [
    {"name": "check",
     "description": ("Detect AI and prose tells in text. Runs fully local with no network "
                     "call. Returns each finding with its line, tier (HIGH/MEDIUM), category "
                     "and snippet, a clean/flagged device gate, a 0-100 machine-texture "
                     "score, and cadence stats."),
     "inputSchema": {"type": "object", "required": ["text"], "properties": dict(_TEXT)}},
    {"name": "score",
     "description": ("Return the graded 0-100 machine-texture score plus passive-voice and "
                     "adverb rates and cadence flags for a passage. Local, no network."),
     "inputSchema": {"type": "object", "required": ["text"], "properties": dict(_TEXT)}},
    {"name": "judge",
     "description": ("A skilled-editor read of the judgment-level failures a regex cannot "
                     "see: confident emptiness, vague abstraction, uncommitted hedging, weak "
                     "verbs, a buried point. Flags, does not rewrite. Needs an LLM backend."),
     "inputSchema": {"type": "object", "required": ["text"], "properties": dict(_TEXT)}},
    {"name": "fix",
     "description": ("Rewrite the text to the plain-writing standard and self-check the "
                     "rewrite against the detector so it introduces no new tell. Offers a "
                     "suggestion; the human decides. Needs an LLM backend."),
     "inputSchema": {"type": "object", "required": ["text"],
                     "properties": dict(_TEXT, **_IS_HTML)}},
    {"name": "polish",
     "description": ("The quality loop: rewrite, then score five qualities (concreteness, "
                     "commitment, economy, rhythm, restatable-fact-per-paragraph) and iterate "
                     "until every one clears `bar` (1-5) and the detector is clean. Gated on "
                     "writing quality, never on a detector score. Needs an LLM backend."),
     "inputSchema": {"type": "object", "required": ["text"],
                     "properties": dict(
                         _TEXT,
                         bar={"type": "integer", "default": 4, "minimum": 1, "maximum": 5,
                              "description": "the quality bar every dimension must clear"},
                         passes={"type": "integer", "default": 3, "minimum": 1,
                                 "description": "how many rewrite attempts before giving up"},
                         **_IS_HTML)}},
    {"name": "articulate.status",
     "description": ("Liveness and identity of the articulate MCP server (name, version, "
                     "protocol). Network-free health probe."),
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "articulate.doctor",
     "description": ("Readiness diagnostic: identity, the tools exposed, and which of them "
                     "need an LLM backend rather than running local."),
     "inputSchema": {"type": "object", "properties": {}}},
]

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


def _identity(include_detail: bool) -> dict:
    info = {"ok": True, "server": "articulate", "version": __version__,
            "protocol": PROTOCOL}
    if include_detail:
        info["tools"] = [t["name"] for t in TOOLS]
        info["local_only"] = list(LOCAL_ONLY)
        info["needs_llm_backend"] = list(NEEDS_BACKEND)
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
        info = _identity(name == "articulate.doctor")
        return {"content": [{"type": "text", "text": json.dumps(info, indent=2)}]}
    try:
        if name == "check":
            result = do_check(_text_arg(args))
        elif name == "score":
            result = do_score(_text_arg(args))
        elif name == "judge":
            result = do_judge(_text_arg(args))
        elif name == "fix":
            result = do_fix(_text_arg(args), bool(args.get("is_html", False)))
        elif name == "polish":
            result = do_polish(_text_arg(args), int(args.get("bar", 4)),
                               int(args.get("passes", 3)),
                               bool(args.get("is_html", False)))
        else:
            return {"content": [{"type": "text", "text": "unknown tool %r" % (name,)}],
                    "isError": True}
    except Exception as exc:          # a tool error is a result, not a dead server
        return {"content": [{"type": "text",
                             "text": "[error] %s: %s" % (type(exc).__name__, exc)}],
                "isError": True}
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


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
    if method == "tools/list":
        return _ok(rid, {"tools": TOOLS})
    if method == "tools/call":
        params = req["params"] if "params" in req else {}
        if not isinstance(params, dict):
            return _err(rid, -32602, "invalid params")
        return _ok(rid, _call(params))
    return _err(rid, -32601, "method not found: %s" % (method,))


# Sibling lane servers are split on what they call this function. Measured across
# the installed distributions on 2026-09-22: chorus, gather, mneme and
# accountable-surface expose handle_request; plexus, canon and relay expose
# handle. Nothing dispatches across packages by either name, so neither is a
# contract and this alias is a convenience, not a requirement. Both point at one
# function, so there is no second code path to keep in step.
handle_request = handle


def serve(stdin=None, stdout=None) -> int:
    stdin = stdin if stdin is not None else sys.stdin
    stdout = stdout if stdout is not None else sys.stdout
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except ValueError:
            stdout.write(json.dumps(_err(None, -32700, "parse error")) + "\n")
            stdout.flush()
            continue
        resp = handle(req)
        if resp is not None:
            stdout.write(json.dumps(resp) + "\n")
            stdout.flush()
    return 0


def main() -> int:
    return serve()


if __name__ == "__main__":
    raise SystemExit(main())
