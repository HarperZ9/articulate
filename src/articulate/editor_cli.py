#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.editor_cli -- the command line of the editor layer.

`python -m articulate.editor` runs this. Commands select a configured backend, offer a host plan, or use local
deterministic editing. Local-only permits loopback Ollama and no-model edits. `--advise` is `--review` under a name that cannot be read as peer
review; the desk is the reviewer tool.

Standard library only.
"""
import argparse
import os
import sys

from . import editor as ed
from .local_only import LOCAL_ONLY_EXIT, LOCAL_ONLY_VAR, command_map, local_only

_COMMANDS = ("judge", "fix", "polish", "review", "advise")
_COMMAND_HELP = (
    ("--judge", "an editor's read of judgment-level failures; no rewrite"),
    ("--fix", "rewrite for the intended reader and re-check the rewrite"),
    ("--polish", "the quality loop: keep a pass only when no quality score falls, the "
                 "gate does not go from ok to blocked and no required note opens"),
    ("--review", "the checks plus an editor's read, no rewrite"),
)


def _parser():
    ap = argparse.ArgumentParser(
        prog="python -m articulate.editor",
        description="Articulate editor layer with guarded backend selection.",
        epilog=command_map(), formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    for flag, text in _COMMAND_HELP:
        g.add_argument(flag, metavar="FILE", help=text)
    g.add_argument("--advise", metavar="FILE",
                   help="the same as --review: the checks plus an editor's read, no rewrite")
    ap.add_argument("--backend", choices=("auto", "host", "sampling", "anthropic", "claude-cli", "openai", "ollama", "none"))
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
    # An empty FILE is still the command's argument: it reports "no such file".
    cmd = next(c for c in _COMMANDS if getattr(args, c) is not None)
    target = getattr(args, cmd)
    if args.local_only:
        os.environ[LOCAL_ONLY_VAR] = "1"
    reason = _unreadable(target)
    if reason:
        print(f"[articulate] {reason}")
        return 2
    if cmd == "judge":
        ed.judge(target, args.mode, args.profile, backend=args.backend)
        return 0
    if cmd in ("review", "advise"):
        ed.review(target, args.mode, args.profile, backend=args.backend)
        return 0
    if cmd == "polish":
        return ed.polish(target, args.out, max(1, args.passes), max(1, min(5, args.bar)),
                         mode=args.mode, profile=args.profile, backend=args.backend)
    return ed.fix(target, args.out, max(1, args.passes), mode=args.mode, profile=args.profile, backend=args.backend)


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
