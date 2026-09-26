#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.cli -- the unified command line.

  articulate check [FILE ...] [--profile P] [--json] [--gate] [--verbose]
  articulate score [FILE ...] [--profile P]
  articulate receipt | verify | audit | modes

With no FILE, reads stdin. The profile is chosen by --profile, else an in-file
`writing-profile:` tag, else the file path, else the default. `--gate` exits 1
when any input is blocked under its profile, for CI use.
"""
import argparse
import json
import sys

from . import cli_receipts, modes, profiles, pysource
from .cli_output import print_check, print_score, print_spans, redact, to_sarif  # noqa: F401
from .detector import analyze_blocks, binary_reason, check_text
from .tool_text import DOES_NOT_PROVE, PRODUCT

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass


def _profile_name(path, text, override):
    if override:
        return override
    tag = profiles.declared_profile(text)
    if tag:
        return tag
    if path and path != "<stdin>":
        return profiles.profile_for(path)
    return profiles.DEFAULT


def _resolve(name, text, args):
    """Return (label, profile_dict). A --mode wins over profile inference."""
    if getattr(args, "mode", None):
        return args.mode, modes.load(args.mode)
    pname = _profile_name(name, text, args.profile)
    return pname, profiles.load(pname)


def _prose(name, text):
    """A .py file's prose is its docstrings and comments; extract those, keeping
    line numbers, so code is never scored as prose."""
    if name.lower().endswith(".py"):
        return pysource.prose_of(text)
    return text


def _decode(data):
    """Decode source bytes to text with line endings canonicalized to LF, so a
    CRLF/LF rewrite of an otherwise-identical file is not read as a change. The same
    decode runs at receipt issuance and at audit reverify, so their text hashes agree
    across operating systems."""
    return data.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")


def _inputs(files):
    """Yield (name, text, reason). A binary or unsupported document is refused with
    a reason and no text, so the caller fails closed and never scans a lossy decode
    of its bytes."""
    if not files:
        yield "<stdin>", sys.stdin.read(), None
        return
    for p in files:
        try:
            with open(p, "rb") as fh:
                data = fh.read()
        except OSError as e:
            yield p, None, f"cannot read: {e}"
            continue
        reason = binary_reason(data, name=p)
        yield (p, None, reason) if reason else (p, _decode(data), None)


def _screen(args):
    """Yield (name, profile_name, result) per readable input; None on a refusal;
    raise ValueError on an unknown profile or mode."""
    for name, text, reason in _inputs(args.files):
        if reason:
            print(f"[articulate] {name}: cannot screen ({reason})", file=sys.stderr)
            yield None
            continue
        text = _prose(name, text)
        try:
            pname, prof = _resolve(name, text, args)
        except (profiles.ProfileError, modes.ModeError) as e:
            raise ValueError(str(e)) from e
        r = check_text(text, profile=prof)
        r["file"], r["profile"] = name, pname
        if getattr(args, "spans", False):
            r["blocks"] = analyze_blocks(text, profile=prof)
        yield name, pname, r


def _cmd_check(args):
    blocked = refused = False
    payload = []
    quiet = args.json or getattr(args, "sarif", False)
    try:
        for item in _screen(args):
            if item is None:
                refused = True
                continue
            name, pname, r = item
            if getattr(args, "content_free", False):
                redact(r)          # no export path carries a verbatim substring
            payload.append(r)
            blocked = blocked or r["gate"] == "blocked"
            if not quiet:
                if getattr(args, "spans", False):
                    print_spans(name, pname, r["blocks"])
                else:
                    print_check(name, pname, r, args.verbose)
    except ValueError as e:
        print(f"[articulate] {e}", file=sys.stderr)
        return 2
    if getattr(args, "sarif", False):
        print(json.dumps(to_sarif(payload), ensure_ascii=False, indent=2))
    elif args.json:
        print(json.dumps({"results": payload}, ensure_ascii=False, indent=2))
    # Fail closed: an unscreenable input fails the gate and never passes silently.
    return 1 if (args.gate and (blocked or refused)) else 0


def _cmd_score(args):
    try:
        for item in _screen(args):
            if item is not None:
                print_score(item[0], item[1], item[2])
    except ValueError as e:
        print(f"[articulate] {e}", file=sys.stderr)
        return 2
    print(f"[articulate] {DOES_NOT_PROVE}")
    return 0


def _add_check_args(p, cmd):
    p.add_argument("files", nargs="*")
    p.add_argument("--profile", default=None, help="force a profile (house, essay, ...)")
    p.add_argument("--mode", default=None,
                   help="a writing mode (domain/articulation, e.g. memo/argue)")
    if cmd == "check":
        p.add_argument("--json", action="store_true")
        p.add_argument("--sarif", action="store_true", help="emit SARIF 2.1.0")
        p.add_argument("--gate", action="store_true", help="exit 1 if blocked")
        p.add_argument("--verbose", action="store_true")
        p.add_argument("--spans", action="store_true",
                       help="per-paragraph counts by rule, in document order; "
                            "a view of where the findings sit")
        p.add_argument("--content-free", action="store_true",
                       help="omit every verbatim substring from console/JSON/SARIF output")
    if cmd == "receipt":
        p.add_argument("--spans", action="store_true",
                       help="record per-paragraph counts in the receipt")
        p.add_argument("--redact", choices=["none", "drop", "hash"], default="none",
                       help="content-free audit receipt: drop or hash the matched text")
        p.add_argument("--reviewer", default=None,
                       help="record who screened it (else the CI actor, else unset)")


def build_parser():
    ap = argparse.ArgumentParser(prog="articulate", description=PRODUCT)
    sub = ap.add_subparsers(dest="cmd")
    for cmd in ("check", "score", "receipt"):
        _add_check_args(sub.add_parser(cmd), cmd)
    pv = sub.add_parser("verify", help="replay a receipt against text")
    pv.add_argument("receipt", help="a receipt JSON file")
    pv.add_argument("file", help="the text file to re-derive against")
    pa = sub.add_parser("audit", help="query committed receipts locally")
    pa.add_argument("paths", nargs="*", help="receipt files or directories (default: .)")
    pa.add_argument("--days", type=int, default=30, help="recent-activity window")
    pa.add_argument("--reverify", action="store_true",
                    help="replay each receipt against its source file")
    pa.add_argument("--gate", action="store_true",
                    help="with --reverify, exit 1 if any receipt drifts")
    pa.add_argument("--json", action="store_true")
    sub.add_parser("modes", help="list available writing modes")
    return ap


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    ap = build_parser()
    args = ap.parse_args(argv)
    handlers = {
        "check": lambda: _cmd_check(args),
        "score": lambda: _cmd_score(args),
        "receipt": lambda: cli_receipts.cmd_receipt(args, _inputs, _profile_name),
        "verify": lambda: cli_receipts.cmd_verify(args, _decode),
        "audit": lambda: cli_receipts.cmd_audit(args, _decode),
    }
    if args.cmd in handlers:
        return handlers[args.cmd]()
    if args.cmd == "modes":
        for m in modes.names():
            print(m)
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
