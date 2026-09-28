#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.cli -- the unified command line.

  articulate check [FILE ...] [--profile P] [--json] [--gate] [--verbose]
  articulate score [FILE ...] [--profile P]
  articulate receipt | verify | audit | modes
  articulate process ... | disclose     (a writer-held process record)
  articulate desk FILE                  (questions for a reviewer)

With no FILE, reads stdin. The profile is chosen by --profile, else an in-file
`writing-profile:` tag, else the file path, else the default. `--gate` exits 1
when any input is blocked under its profile, for CI use.
"""
import argparse
import json
import sys

from . import cli_desk, cli_process, cli_receipts, modes, profiles, pysource
from .cli_output import print_check, print_score, print_spans, redact, to_sarif  # noqa: F401
from .detector import analyze_blocks, binary_reason, check_text
from .local_only import command_map
from .markup import ALLOW_HELP
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
        notes = getattr(args, "house_notes", False)
        r = check_text(text, profile=prof, house_notes=notes)
        r["file"], r["profile"] = name, pname
        if getattr(args, "spans", False):
            r["blocks"] = analyze_blocks(text, profile=prof, house_notes=notes)
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
    elif payload and not getattr(args, "spans", False):
        print(f"[articulate] {DOES_NOT_PROVE}")   # every run, a passing gate included
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
    print("[articulate] density counts the findings that block under the profile, per "
          "1,000 words; the per-rule counts are the primary output.")
    print(f"[articulate] {DOES_NOT_PROVE}")
    return 0


def _add_check_args(p, cmd):
    p.add_argument("files", nargs="*")
    p.add_argument("--profile", default=None, help="force a profile (house, essay, ...)")
    p.add_argument("--mode", default=None,
                   help="a writing mode (domain/articulation, e.g. memo/argue)")
    if cmd in ("check", "score"):
        p.add_argument("--house-notes", action="store_true",
                       help="also report the house style's patterns as low notes "
                            "(a house profile gates them; no other profile shows them)")
    if cmd == "check":
        p.add_argument("--json", action="store_true",
                       help="the findings, gate, counts and does-not-prove line as JSON")
        p.add_argument("--sarif", action="store_true", help="emit SARIF 2.1.0")
        p.add_argument("--gate", action="store_true",
                       help="exit 1 when any file is blocked or cannot be screened")
        p.add_argument("--verbose", action="store_true",
                       help="expand the low notes and print each finding's reason")
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


_CHECK_HELP = {
    "check": "report the findings and the gate (local)",
    "score": "per-rule counts and density per 1,000 words (local)",
    "receipt": "a re-derivable screening as JSON; --redact for a content-free one (local)",
}


def _read_edit_file(path):
    with open(path, "rb") as fh:
        data = fh.read()
    reason = binary_reason(data, name=path)
    if reason:
        raise ValueError(f"cannot edit binary input ({reason})")
    return _decode(data)

def _cmd_edit(args):
    from . import editing, host_edit
    try:
        text = _read_edit_file(args.file)
        if args.cmd == "submit":
            result = host_edit.edit_submit(
                text, _read_edit_file(args.rewrite), args.plan,
                scores=json.loads(args.scores) if args.scores else None,
                model=args.model)
        else:
            options = {"mode": args.mode,
                       "profile": None if args.mode else _profile_name(args.file, text, args.profile),
                       "is_html": args.is_html or args.file.lower().endswith((".html", ".htm")),
                       "is_tex": args.is_tex or args.file.lower().endswith(".tex")}
            if args.cmd == "plan":
                result = host_edit.edit_plan(text, goal=args.goal, **options)
            else:
                result = editing.run_edit(text, goal=args.cmd, backend=args.backend,
                                          bar=args.bar, passes=args.passes,
                                          timeout=args.timeout, **options)
        if not result.get("ok", False):
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 2
        # Host plans need another step; they are JSON even without --json.
        if getattr(args, "out", None) and "text" in result and "plan_id" not in result:
            with open(args.out, "w", encoding="utf-8", newline="") as fh:
                fh.write(result["text"])
        if args.cmd in ("fix", "polish", "submit") and "plan_id" not in result and result.get("text") != text:
            from .process_events import record_editor_pass
            from .process_ledger import LogBroken
            try:
                record_editor_pass(args.file, args.cmd, backend=result.get("backend"), model=result.get("model"))
            except LogBroken as exc:
                result["process_log_warning"] = str(exc)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print(f"[articulate] {exc}", file=sys.stderr)
        return 2


def build_parser():
    ap = argparse.ArgumentParser(prog="articulate", description=PRODUCT, epilog=command_map(),
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    for cmd in ("plan", "submit", "judge", "fix", "polish"):
        p = sub.add_parser(cmd)
        p.add_argument("file", help="original text file")
        if cmd == "submit":
            p.add_argument("rewrite", help="host rewrite or assessment file")
            p.add_argument("--plan", required=True, help="plan_id returned by plan")
            p.add_argument("--scores", help="JSON with before and after quality scores")
            p.add_argument("--model", help="caller-supplied host model name")
        else:
            p.add_argument("--profile")
            p.add_argument("--mode")
            p.add_argument("--is-html", action="store_true")
            p.add_argument("--is-tex", action="store_true")
            if cmd == "plan":
                p.add_argument("--goal", choices=("fix", "polish", "judge"), default="fix")
            else:
                p.add_argument("--backend", choices=("auto", "host", "sampling", "anthropic",
                                                     "claude-cli", "openai", "ollama", "none"))
                p.add_argument("--bar", type=int, default=4)
                p.add_argument("--passes", type=int, default=3)
                p.add_argument("--timeout", type=float, default=600)
        p.add_argument("--out", help="write accepted text to this file")
        p.add_argument("--json", action="store_true", help="emit result JSON (the editor default)")
    for cmd, text in _CHECK_HELP.items():
        _add_check_args(sub.add_parser(cmd, help=text, epilog=ALLOW_HELP), cmd)
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
    cli_process.register(sub)
    cli_desk.register(sub)
    return ap


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    ap = build_parser()
    args = ap.parse_args(argv)
    if args.cmd in ("plan", "submit", "judge", "fix", "polish"):
        return _cmd_edit(args)
    handlers = {
        "check": lambda: _cmd_check(args),
        "score": lambda: _cmd_score(args),
        "receipt": lambda: cli_receipts.cmd_receipt(args, _inputs, _profile_name),
        "verify": lambda: cli_receipts.cmd_verify(args, _decode),
        "audit": lambda: cli_receipts.cmd_audit(args, _decode),
        "process": lambda: cli_process.cmd_process(args),
        "disclose": lambda: cli_process.cmd_disclose(args),
        "desk": lambda: cli_desk.cmd_desk(args),
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
