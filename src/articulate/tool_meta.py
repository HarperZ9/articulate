#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.tool_meta -- the title and behavior hints each MCP tool declares,
and which tools a server lists.

A host reads these hints to decide which calls need the user's approval. Both MCP
servers read this one table, as they read tool_text for descriptions, so the two
surfaces cannot declare different behavior for the same tool.

Every tool sets all four hints. The protocol defaults are readOnlyHint false,
destructiveHint true and openWorldHint true, so a hint left out would describe a
local check as a tool that deletes data and reaches the network.

The local tools read the text they are given and nothing else: no file, no
network, no other program. The hosted tools send the text to a hosted model
through the claude CLI. They change none of the user's files, and they are marked
as not read-only so a host asks before each call: the text leaves the machine and
the call spends the user's quota.

Standard library only.
"""
from __future__ import annotations

import os

TITLES = {
    "check": "Check prose for named patterns",
    "score": "Score pattern density",
    # compare ships with the meaning guard; its entry is here so both land together.
    "compare": "Compare a rewrite with the original",
    "judge": "Editor read through a hosted model",
    "fix": "Suggest a rewrite through a hosted model",
    "polish": "Rewrite in passes through a hosted model",
    "articulate.status": "Articulate server status",
    "articulate.doctor": "Articulate readiness check",
}

# The tools that send the text to a hosted model. local_mcp.NEEDS_BACKEND names
# the same set, and a test holds the two equal.
HOSTED = frozenset(("judge", "fix", "polish"))

_LOCAL_HINTS = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True,
                "openWorldHint": False}
_HOSTED_HINTS = {"readOnlyHint": False, "destructiveHint": False,
                 "idempotentHint": False, "openWorldHint": True}


def annotations(name: str) -> dict:
    """The MCP ToolAnnotations object for one tool: its title and all four hints.

    An unknown name raises KeyError, so a tool added without a title fails the
    first tools/list call in the test suite.
    """
    hints = _HOSTED_HINTS if name in HOSTED else _LOCAL_HINTS
    return dict(title=TITLES[name], **hints)


def fastmcp_options(name: str) -> dict:
    """The keyword arguments fastmcp's ``tool()`` takes for the same metadata."""
    return {"title": TITLES[name], "annotations": annotations(name)}


# ARTICULATE_MCP_TOOLS=local lists only the tools that read the text and nothing
# else. The Claude plugin sets it, so a plugin install never offers a tool that
# sends the text off the machine.
TOOLS_VAR = "ARTICULATE_MCP_TOOLS"


def tool_set(environ=None) -> str:
    """'all' when the variable is unset, empty or 'all'; 'local' for any other
    value, so a mistyped value lists fewer tools and never more."""
    env = os.environ if environ is None else environ
    return "all" if env.get(TOOLS_VAR, "").strip().lower() in ("", "all") else "local"


def is_listed(name: str, environ=None) -> bool:
    """Whether a server lists this tool under the current tool set."""
    return name not in HOSTED or tool_set(environ) == "all"
