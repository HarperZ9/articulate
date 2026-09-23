#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
articulate.cli_ext -- subcommands added after the core CLI.

Each subcommand registers its parser here and sets a `handler`, so the core
dispatcher in articulate.cli only needs one line to reach it.

  articulate compare ORIGINAL REWRITE [--json] [--gate] [--show-kept]
                     [--freeze TERM] [--allow-change KINDS]
"""
from __future__ import annotations

import json
import sys

from . import guard, meaning
from .detector import binary_reason


def read_text(path):
    """(text, None) for a readable text file, or (None, reason). A binary or an
    unsupported document is refused with a reason, never decoded lossily."""
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError as e:
        return None, f"cannot read: {e}"
    reason = binary_reason(data, name=path)
    if reason:
        return None, reason
    text = data.decode("utf-8", errors="replace")
    return text.replace("\r\n", "\n").replace("\r", "\n"), None


def _cmd_compare(args):
    texts = []
    for path in (args.original, args.rewrite):
        text, reason = read_text(path)
        if reason:
            print(f"[articulate] {path}: cannot compare ({reason})", file=sys.stderr)
            return 2
        texts.append(text)
    try:
        allow = guard.parse_allow(args.allow_change)
    except ValueError as e:
        print(f"[articulate] {e}", file=sys.stderr)
        return 2
    report = meaning.compare(texts[0], texts[1], freeze=args.freeze)
    block = meaning.blocking(report, allow)
    if args.json:
        payload = dict(report, files={"original": args.original, "rewrite": args.rewrite},
                       blocking=len(block), allowed=sorted(allow))
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(meaning.format_report(report, show_kept=args.show_kept))
    return 1 if (args.gate and block) else 0


def _register_compare(sub):
    p = sub.add_parser("compare", help="meaning guard: compare a rewrite with its original")
    p.add_argument("original", help="the original text file")
    p.add_argument("rewrite", help="the rewritten text file")
    p.add_argument("--json", action="store_true", help="the full report as JSON")
    p.add_argument("--gate", action="store_true",
                   help="exit 1 when an invariant not allowed to change was dropped, "
                        "added, or changed")
    p.add_argument("--show-kept", action="store_true", help="also list kept invariants")
    p.add_argument("--freeze", action="append", default=[], metavar="TERM",
                   help="a term that must survive verbatim (repeatable)")
    p.add_argument("--allow-change", default="", metavar="KINDS",
                   help="invariant kinds that may change without failing --gate")
    p.set_defaults(handler=_cmd_compare)


def register(sub):
    """Add every extension subcommand to the core CLI's subparsers."""
    _register_compare(sub)
