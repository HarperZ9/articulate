#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.local_only -- the switch that keeps every text on the machine.

The checks never send text anywhere. `judge`, `fix`, `polish` and `review`, and
the MCP tools of those names, send the full text to a hosted model through the
claude CLI. With ARTICULATE_LOCAL_ONLY set (or `--local-only` on the editor
command), each of them is refused before any subprocess starts. The command
line exits with LOCAL_ONLY_EXIT; a library or MCP caller gets LocalOnly.

The switch fails closed. Unset, empty, 0, false, no and off leave it off; any
other value turns it on, so a writer who spells "on" differently never sends
the text.

Standard library only.
"""
import os

LOCAL_ONLY_VAR = "ARTICULATE_LOCAL_ONLY"
LOCAL_ONLY_EXIT = 3
_OFF = ("", "0", "false", "no", "off")

# What each command does with the text. The README and `articulate --help`
# print this map; a test checks both.
LOCAL_COMMANDS = ("check", "score", "receipt", "verify", "audit", "modes", "process",
                  "disclose", "desk", "the LSP server",
                  "the fairness harness (python -m articulate.fairness)",
                  "the benchmark (python -m articulate.bench)",
                  "the check and score tools of both MCP servers")
HOSTED_COMMANDS = ("judge", "review", "fix", "polish")


class LocalOnly(RuntimeError):
    """A hosted call refused because the local-only switch is set."""


def local_only(environ=None):
    """True unless ARTICULATE_LOCAL_ONLY is unset, empty, 0, false, no or off."""
    env = os.environ if environ is None else environ
    return env.get(LOCAL_ONLY_VAR, "").strip().lower() not in _OFF


def refuse_if_local_only(environ=None):
    env = os.environ if environ is None else environ
    if local_only(env):
        raise LocalOnly(f"local-only: {LOCAL_ONLY_VAR} is {env.get(LOCAL_ONLY_VAR)!r}, which "
                        "counts as on, so no text is sent to the hosted model; the local "
                        "checks still run")


def command_map():
    """The map of local and hosted commands, for `--help` and the README."""
    return (
        "Local, sending nothing: " + ", ".join(LOCAL_COMMANDS) + ".\n"
        "Hosted, sending the full text to a model through the claude CLI: "
        + ", ".join(HOSTED_COMMANDS) + " (python -m articulate.editor), and the judge, "
        "fix and polish tools of both MCP servers.\n"
        f"Set {LOCAL_ONLY_VAR}=1, or pass --local-only to the editor, and every hosted "
        "command exits before any network call.\n"
        "Under a brief that allows only spelling and grammar help, use the local "
        "commands; judge and review give structural advice. Do not run the hosted "
        "commands on a manuscript or grant application under review, on health "
        "records, or on unfiled patent material.")
