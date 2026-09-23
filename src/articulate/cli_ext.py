#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
articulate.cli_ext -- subcommands added after the core CLI.

Each subcommand registers its parser here and sets a `handler`, so the core
dispatcher in articulate.cli only needs one line to reach it.

  articulate compare ORIGINAL REWRITE [--json] [--gate] [--show-kept]
                     [--freeze TERM] [--allow-change KINDS] [--config PATH]
  articulate config [PATH] [--config PATH] [--json]
  articulate drafts {record,show,verify} FILE [--actor LABEL] [--log DIR]
                    [--no-snapshot] [--json]
"""
from __future__ import annotations

import json
import os
import sys

from . import drafts, guard, meaning, project
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
        cfg = project.for_path(args.original, args.config)
    except ValueError as e:          # a bad kind name or a malformed project config
        print(f"[articulate] {e}", file=sys.stderr)
        return 2
    freeze = tuple(args.freeze) + (cfg.freeze if cfg else ())
    report = meaning.compare(texts[0], texts[1], freeze=freeze)
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
    p.add_argument("--config", default=None, metavar="PATH",
                   help="a project config file, or 'none'; its freeze terms join --freeze")
    p.set_defaults(handler=_cmd_compare)


def _cmd_config(args):
    """Show which project config applies to a path and what it sets."""
    try:
        cfg = project.for_path(args.path, args.config)
        name = project.resolve(args.path, "", cfg=cfg)[0]
    except ValueError as e:
        print(f"[articulate] {e}", file=sys.stderr)
        return 2
    term = cfg.terminology if cfg else {}
    info = {"config": cfg.path if cfg else None, "profile": name,
            "banned": len(term.get("banned", [])), "preferred": len(term.get("preferred", [])),
            "allowed": list(term.get("allowed", [])), "freeze": list(cfg.freeze if cfg else ()),
            "protect": dict(cfg.protect) if cfg else {}, "options": cfg.options if cfg else {}}
    if args.json:
        print(json.dumps(info, ensure_ascii=False, indent=2))
    else:
        for key, value in info.items():
            print(f"[config] {key}: {value}")
    return 0


def _register_config(sub):
    p = sub.add_parser("config", help="show the project config that applies to a path")
    p.add_argument("path", nargs="?", default=".", help="a file or directory (default: .)")
    p.add_argument("--config", default=None, metavar="PATH", help="a config file, or 'none'")
    p.add_argument("--json", action="store_true")
    p.set_defaults(handler=_cmd_config)


def _drafts_record(args):
    text, reason = read_text(args.file)
    if reason:
        print(f"[drafts] {args.file}: cannot record ({reason})", file=sys.stderr)
        return 2
    try:
        entry, why = drafts.record(args.file, text, actor=args.actor, log_dir=args.log,
                                   snapshot=not args.no_snapshot)
    except (drafts.LogBroken, OSError) as e:
        print(f"[drafts] {args.file}: {e}", file=sys.stderr)
        return 1
    if why:
        print(f"[drafts] {args.file}: {why}")
        return 0
    change = entry["diff"]
    delta = f"+{change['lines_added']}/-{change['lines_removed']} lines" if change else "first draft"
    print(f"[drafts] recorded draft {entry['seq']} of {args.file} ({delta}): {entry['hash']}")
    return 0


def _drafts_show(args):
    log_path, _ = drafts.paths(args.file, args.log)
    if not os.path.isfile(log_path):
        print(f"[drafts] {args.file}: no draft log at {log_path}", file=sys.stderr)
        return 2
    entries, problems = drafts.load(log_path)
    if args.json:
        print(json.dumps({"log": log_path, "entries": entries, "problems": problems},
                         ensure_ascii=False, indent=2))
        return 1 if problems else 0
    print(f"[drafts] {args.file}: {len(entries)} draft(s) in {log_path}")
    for e in entries:
        d = e.get("diff")
        delta = f"+{d['lines_added']}/-{d['lines_removed']} lines" if d else "no diff"
        print(f"  #{e.get('seq')} {e.get('time')} {e.get('actor') or '-'}: "
              f"{e.get('words')} words, texture {e.get('texture_score')}, {delta}")
    for p in problems:
        print(f"  problem: {p}")
    return 1 if problems else 0


def _drafts_verify(args):
    text = read_text(args.file)[0] if os.path.isfile(args.file) else None
    rep = drafts.verify(args.file, text, args.log)
    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
    else:
        print(f"[drafts] {args.file}: {rep['verdict']}, {rep['drafts']} draft(s)")
        for p in rep["problems"]:
            print(f"  problem: {p}")
        for n in rep["notes"]:
            print(f"  note: {n}")
    return {"intact": 0, "broken": 1}.get(rep["verdict"], 2)


def _register_drafts(sub):
    p = sub.add_parser("drafts", help="a local, hash-chained record of a document's drafts")
    p.add_argument("action", choices=("record", "show", "verify"))
    p.add_argument("file", help="the document")
    p.add_argument("--actor", default=None, help="a label for who recorded this draft")
    p.add_argument("--log", default=None, metavar="DIR",
                   help="the log directory (default: .articulate/drafts beside the file)")
    p.add_argument("--no-snapshot", action="store_true",
                   help="store hashes only, not the draft text")
    p.add_argument("--json", action="store_true")
    handlers = {"record": _drafts_record, "show": _drafts_show, "verify": _drafts_verify}
    p.set_defaults(handler=lambda args: handlers[args.action](args))


def register(sub):
    """Add every extension subcommand to the core CLI's subparsers."""
    _register_compare(sub)
    _register_config(sub)
    _register_drafts(sub)
