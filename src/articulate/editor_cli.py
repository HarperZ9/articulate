#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.editor_cli -- the command line of the editor layer.

`python -m articulate.editor` runs this. Every command here sends the full text
to a hosted model through the claude CLI, so the first thing each run does is
say so, and with the local-only switch set it refuses before any subprocess
starts. `--advise` is `--review` under a name that cannot be read as peer
review; the desk is the reviewer tool.

Standard library only.
"""
import argparse
import os
import sys

from . import editor as ed
from .local_only import LOCAL_ONLY_EXIT, LOCAL_ONLY_VAR, command_map, local_only

_COMMANDS = ("judge", "fix", "polish", "review", "advise")


def _parser():
    ap = argparse.ArgumentParser(
        prog="python -m articulate.editor",
        description="Articulate editor layer. Each command sends the full text to a "
                    "hosted model through the claude CLI.",
        epilog=command_map(), formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    for flag in ("--judge", "--fix", "--polish", "--review"):
        g.add_argument(flag, metavar="FILE")
    g.add_argument("--advise", metavar="FILE",
                   help="the same as --review: the checks plus an editor's read, no rewrite")
    ap.add_argument("--out", metavar="FILE", default=None)
    ap.add_argument("--passes", type=int, default=3)
    ap.add_argument("--bar", type=int, default=4, help="quality bar 1-5 for --polish")
    ap.add_argument("--mode", default=None,
                    help="a writing mode (domain/articulation, e.g. memo/argue)")
    ap.add_argument("--profile", default=None,
                    help="a profile; `house` sends the house writing standard")
    ap.add_argument("--local-only", action="store_true",
                    help=f"refuse every hosted call, as {LOCAL_ONLY_VAR}=1 does")
    return ap


def main(argv=None):
    args = _parser().parse_args(argv)
    cmd = next(c for c in _COMMANDS if getattr(args, c))
    target = getattr(args, cmd)
    if args.local_only or local_only():
        print(f"[articulate] local-only: {cmd} was refused and {target} was not sent. "
              f"The local checks (articulate check, score, desk) still run.", file=sys.stderr)
        return LOCAL_ONLY_EXIT
    reason = _unreadable(target)
    if reason:
        print(f"[articulate] {reason}")
        return 2
    print(f"[articulate] {cmd} sends the full text of {os.path.basename(target)} to a hosted "
          f"model through the claude CLI; the checks themselves run offline. Set "
          f"{LOCAL_ONLY_VAR}=1 to refuse.", file=sys.stderr)
    if cmd == "judge":
        ed.judge(target, args.mode, args.profile)
        return 0
    if cmd in ("review", "advise"):
        ed.review(target, args.mode, args.profile)
        return 0
    if cmd == "polish":
        return ed.polish(target, args.out, max(1, args.passes), max(1, min(5, args.bar)),
                         mode=args.mode, profile=args.profile)
    return ed.fix(target, args.out, max(1, args.passes), mode=args.mode, profile=args.profile)


def _unreadable(target):
    if not os.path.isfile(target):
        return f"no such file: {target}"
    from . import detector
    try:
        with open(target, "rb") as fh:
            head = fh.read(8192)
    except OSError as e:
        return f"cannot read {target}: {e}"
    reason = detector.binary_reason(head, name=target)
    return f"cannot edit {target}: {reason}" if reason else None
