#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.cli -- the unified command line.

  articulate check [FILE ...] [--profile P] [--json] [--gate] [--verbose]
  articulate score [FILE ...] [--profile P]

With no FILE, reads stdin. The profile is chosen by --profile, else an in-file
`writing-profile:` tag, else the file path, else the default. `--gate` exits 1
when any input is blocked under its profile, for CI use.
"""
import argparse
import json
import os
import sys

from . import modes, profiles, pysource, receipt
from .detector import binary_reason, check_text, ruleset_fingerprint


def _resolve(name, text, args):
    """Return (label, profile_dict). A --mode wins over profile inference."""
    if getattr(args, "mode", None):
        return args.mode, modes.load(args.mode)
    pname = _profile_name(name, text, args.profile)
    return pname, profiles.load(pname)


def _redact(r):
    """Strip the content-bearing fields from a result, so no export path carries a
    verbatim substring OR the exact offsets/length that reconstruct it under
    --content-free. Keeps only line, rule_id, tier, and category per finding."""
    def strip(f):
        # label enumerates a closed-vocabulary rule's candidate words, so drop it
        # from content-free output and report the category alone.
        for k in ("match", "snippet", "col", "start", "end", "label"):
            f.pop(k, None)
    for tier in ("high", "medium", "low"):
        for f in r.get(tier, []):
            strip(f)
    for b in r.get("blocks", []):
        b.pop("snippet", None)
        for tier in ("high", "medium", "low"):
            for f in b.get(tier, []):
                strip(f)
    return r


def _prose(name, text):
    """A .py file's prose is its docstrings and comments; extract those, keeping
    line numbers, so the detector does not score code as prose."""
    if name.lower().endswith(".py"):
        return pysource.prose_of(text)
    return text

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

_SARIF_LEVEL = {"HIGH": "error", "MEDIUM": "warning", "LOW": "note"}


def _pkgver():
    try:
        from . import __version__
        return __version__
    except Exception:  # noqa: BLE001
        return "0.0.0"


def to_sarif(results):
    """SARIF 2.1.0 from check results, using the span records. GitHub Code
    Scanning, Azure DevOps, and reviewdog ingest this for inline PR annotations."""
    rules, out = {}, []
    for r in results:
        uri = "stdin" if r["file"] == "<stdin>" else r["file"].replace("\\", "/")
        for f in r["high"] + r["medium"] + r.get("low", []):
            rid = f["rule_id"]
            desc = f.get("label") or f["category"]      # category only when redacted
            rules.setdefault(rid, {"id": rid, "name": f["category"],
                                   "shortDescription": {"text": desc}})
            if f.get("match") is not None:
                msg = f"{desc}: {f['match']!r}"
            else:
                msg = f"{desc}" if "label" in f else f"{f['category']} tell"
            # Exact offsets when present, else a line-only locator for a content-free
            # run, so the export never leaks the match length or position.
            if all(k in f for k in ("col", "start", "end")):
                region = {"startLine": f["line"], "startColumn": f["col"],
                          "endColumn": f["col"] + (f["end"] - f["start"]),
                          "charOffset": f["start"], "charLength": f["end"] - f["start"]}
            else:
                region = {"startLine": f["line"]}
            out.append({
                "ruleId": rid,
                "level": _SARIF_LEVEL.get(f["tier"], "note"),
                "message": {"text": msg},
                "locations": [{"physicalLocation": {
                    "artifactLocation": {"uri": uri}, "region": region,
                }}],
            })
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {
                "name": "Articulate", "version": _pkgver(),
                "informationUri": "https://github.com/HarperZ9/articulate",
                "rules": list(rules.values()),
            }},
            "results": out,
        }],
    }


def _profile_name(path, text, override):
    if override:
        return override
    tag = profiles.declared_profile(text)
    if tag:
        return tag
    if path and path != "<stdin>":
        return profiles.profile_for(path)
    return profiles.DEFAULT


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
    if files:
        for p in files:
            try:
                with open(p, "rb") as fh:
                    data = fh.read()
            except OSError as e:
                yield p, None, f"cannot read: {e}"
                continue
            reason = binary_reason(data, name=p)
            if reason:
                yield p, None, reason
            else:
                yield p, _decode(data), None
    else:
        yield "<stdin>", sys.stdin.read(), None


def _print_spans(name, pname, blocks):
    """Per-paragraph verdicts, so a block that carries findings is flagged in place
    and one aggregate score cannot smear across a whole clean document."""
    flagged = [b for b in blocks if b["gate"] == "blocked" or b["elevated"]]
    print(f"[articulate] {name} [{pname}]: {len(blocks)} span(s), {len(flagged)} flagged")
    for b in blocks:
        if b["gate"] == "blocked" or b["elevated"]:
            mark = "FLAG"
        elif b["verdict"] == "unverifiable":
            mark = " ?? "
        else:
            mark = " ok "
        print(f"  [{mark}] span {b['index']} L{b['start_line']}-{b['end_line']}: "
              f"{b['verdict']}, texture {b['texture_score']}/100 "
              f"({b['counts']['high']}H/{b['counts']['medium']}M): {b.get('snippet', '')[:52]}")


def _print_check(name, pname, r, verbose):
    base = name
    if r.get("verdict") == "unverifiable":
        head = f"[articulate] {base} [{pname}]: unverifiable (below the signal floor)"
    elif r["clean"]:
        head = f"[articulate] {base} [{pname}]: clean"
    else:
        head = (f"[articulate] {base} [{pname}]: {len(r['high'])} high, "
                f"{len(r['medium'])} medium ({r['gate']})")
    print(head + f"  texture {r['texture_score']}/100")
    for f in r["high"] + r["medium"]:
        print(f"  L{f['line']} [{f['tier']} {f['category']}] "
              f"{f.get('label', f['category'])}: {f.get('snippet', '')}")
    if verbose and r["low"]:
        for f in r["low"]:
            print(f"  L{f['line']} [LOW {f['category']}] "
                  f"{f.get('label', f['category'])}: {f.get('snippet', '')}")


def _cmd_check(args):
    blocked = False
    refused = False
    payload = []
    for name, text, reason in _inputs(args.files):
        if reason:
            print(f"[articulate] {name}: cannot screen ({reason})", file=sys.stderr)
            refused = True
            continue
        text = _prose(name, text)
        try:
            pname, prof = _resolve(name, text, args)
        except (profiles.ProfileError, modes.ModeError) as e:
            print(f"[articulate] {e}", file=sys.stderr)
            return 2
        r = check_text(text, profile=prof)
        r["file"], r["profile"] = name, pname
        if getattr(args, "spans", False):
            from .detector import analyze_blocks
            r["blocks"] = analyze_blocks(text, profile=prof)
        if getattr(args, "content_free", False):
            _redact(r)          # no export path carries a verbatim substring
        payload.append(r)
        if r["gate"] == "blocked":
            blocked = True
        if not args.json and not getattr(args, "sarif", False):
            if getattr(args, "spans", False):
                _print_spans(name, pname, r["blocks"])
            else:
                _print_check(name, pname, r, args.verbose)
    if getattr(args, "sarif", False):
        print(json.dumps(to_sarif(payload), ensure_ascii=False, indent=2))
    elif args.json:
        print(json.dumps({"results": payload}, ensure_ascii=False, indent=2))
    # Fail closed: an unscreenable input fails the gate and never passes silently.
    return 1 if (args.gate and (blocked or refused)) else 0


def _cmd_receipt(args):
    redact = getattr(args, "redact", "none")
    redact = None if redact in (None, "none") else redact
    # The "who": an explicit --reviewer, else the CI actor, else unrecorded.
    reviewer = getattr(args, "reviewer", None) or os.environ.get("GITHUB_ACTOR") or None
    mode = getattr(args, "mode", None)
    if mode:
        # Fail before any output, so a bad mode never yields a partial receipt set.
        try:
            modes.load(mode)
        except modes.ModeError as e:
            print(f"[articulate] {e}", file=sys.stderr)
            return 2
    for name, text, reason in _inputs(args.files):
        if reason:
            print(f"[articulate] {name}: cannot screen ({reason})", file=sys.stderr)
            continue
        # A --mode wins over profile inference, as in `check`, and the receipt
        # records the mode so verify replays the same screening.
        pname = None if mode else _profile_name(name, text, args.profile)
        try:
            rec = receipt.make_receipt(text, pname, mode=mode,
                                       per_span=getattr(args, "spans", False),
                                       redact=redact, reviewer=reviewer)
        except profiles.ProfileError as e:
            print(f"[articulate] {e}", file=sys.stderr)
            return 2
        rec["file"] = name
        print(json.dumps(rec, ensure_ascii=False, indent=2))
    return 0


def _cmd_verify(args):
    try:
        with open(args.receipt, encoding="utf-8") as fh:
            rec = json.load(fh)
    except (OSError, ValueError) as e:
        print(f"[articulate] cannot read receipt {args.receipt}: {e}", file=sys.stderr)
        return 2
    try:
        with open(args.file, "rb") as fh:
            data = fh.read()
    except OSError as e:
        print(f"[articulate] cannot read {args.file}: {e}", file=sys.stderr)
        return 2
    reason = binary_reason(data, name=args.file)
    if reason:
        print(f"[articulate] cannot screen {args.file}: {reason}", file=sys.stderr)
        return 2
    text = _decode(data)
    verdict, detail = receipt.verify_receipt(rec, text)
    print(f"[articulate] {verdict}: {detail}")
    return {"Match": 0, "Drift": 1, "Unverifiable": 2}.get(verdict, 2)


def _load_receipts(paths):
    """Yield (path, receipt) for JSON receipts under the given files or directories.
    Non-JSON, unparseable, and non-receipt files are skipped."""
    files = []
    for p in paths:
        if os.path.isdir(p):
            for root, _dirs, names in os.walk(p):
                files.extend(os.path.join(root, n) for n in names if n.endswith(".json"))
        else:
            files.append(p)
    for fp in sorted(files):
        try:
            with open(fp, encoding="utf-8") as fh:
                rec = json.load(fh)
        except (OSError, ValueError):
            continue
        if isinstance(rec, dict) and rec.get("schema") in receipt.KNOWN:
            yield fp, rec


def _within_days(created_at, days):
    """True if an ISO-8601 timestamp falls in the last `days` (a bounded window, so a
    future-dated stamp is not counted). False on any malformed or non-string value, so
    a bad stamp is never counted as recent and never crashes the audit."""
    if not isinstance(created_at, str):
        return False
    from datetime import datetime, timedelta, timezone
    try:
        ts = datetime.fromisoformat(created_at)
    except (ValueError, TypeError):
        return False
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    return now - timedelta(days=days) <= ts <= now


def _cmd_audit(args):
    """Query a directory of committed receipts locally: recorded verdicts, blocked
    rules, stale-ruleset receipts, recent activity, and (with --reverify) whether
    each receipt still holds against its source. No server, no network."""
    from collections import Counter

    current_fp = ruleset_fingerprint()
    recs = list(_load_receipts(args.paths or ["."]))
    by_gate, by_verdict, blocked_rules, reverify = Counter(), Counter(), Counter(), Counter()
    stale = recent = 0
    for _fp, rec in recs:
        by_gate[rec.get("gate", "?")] += 1
        by_verdict[rec.get("verdict", "?")] += 1
        if rec.get("ruleset_version") != current_fp:
            stale += 1
        if _within_days(rec.get("created_at"), args.days):
            recent += 1
        if rec.get("gate") == "blocked":
            for f in (rec.get("findings") or []):   # `or []` also covers findings: null
                blocked_rules[f.get("rule_id", "?")] += 1
        if args.reverify:
            src = rec.get("file")
            if not src or not os.path.isfile(src):
                reverify["source-missing"] += 1
                continue
            try:
                with open(src, "rb") as fh:
                    data = fh.read()
            except OSError:            # a race or a permission-denied source is unreadable
                reverify["source-unreadable"] += 1
                continue
            if binary_reason(data, name=src):
                reverify["source-unreadable"] += 1
                continue
            text = _decode(data)
            # A source that changed since screening is a stale receipt (a real gate
            # failure), kept apart from an honest sub-threshold/ruleset Unverifiable.
            if rec.get("text_sha256") != receipt.text_sha256(text):
                reverify["source-changed"] += 1
            else:
                verdict, _ = receipt.verify_receipt(rec, text)
                reverify[verdict] += 1

    summary = {
        "receipts": len(recs),
        "by_gate": dict(by_gate),
        "by_verdict": dict(by_verdict),
        "stale_ruleset": stale,
        f"recent_{args.days}d": recent,
        "blocked_by_rule": dict(blocked_rules.most_common(10)),
    }
    if args.reverify:
        summary["reverify"] = dict(reverify)

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"[audit] {len(recs)} receipt(s); "
              f"gate {dict(by_gate)}; verdict {dict(by_verdict)}")
        print(f"[audit] stale-ruleset {stale}; active in last {args.days}d {recent}")
        if blocked_rules:
            top = ", ".join(f"{r} x{n}" for r, n in blocked_rules.most_common(10))
            print(f"[audit] blocked by rule: {top}")
        if args.reverify:
            print(f"[audit] reverify: {dict(reverify)}")
    # Fail closed on a real integrity failure: the source drifted from its receipt,
    # changed since screening, or cannot be read. A sub-threshold or stale-ruleset
    # Unverifiable is informational, never a gate failure.
    bad = (reverify.get("Drift", 0) + reverify.get("source-changed", 0)
           + reverify.get("source-unreadable", 0))
    return 1 if (args.gate and args.reverify and bad) else 0


def _cmd_score(args):
    for name, text, reason in _inputs(args.files):
        if reason:
            print(f"[articulate] {name}: cannot screen ({reason})", file=sys.stderr)
            continue
        text = _prose(name, text)
        try:
            pname, prof = _resolve(name, text, args)
        except (profiles.ProfileError, modes.ModeError) as e:
            print(f"[articulate] {e}", file=sys.stderr)
            return 2
        r = check_text(text, profile=prof)
        print(f"[articulate] {name} [{pname}]: verdict {r['verdict']}, "
              f"texture {r['texture_score']}/100 "
              f"({'elevated' if r['elevated'] else 'low'}), gate {r['gate']} "
              f"[{len(r['high'])}H/{len(r['medium'])}M, {r['cadence']['words']}w]")
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    ap = argparse.ArgumentParser(prog="articulate",
                                 description="Local writing-quality and AI-tell detection.")
    sub = ap.add_subparsers(dest="cmd")
    for cmd in ("check", "score", "receipt"):
        p = sub.add_parser(cmd)
        p.add_argument("files", nargs="*")
        p.add_argument("--profile", default=None, help="force a register profile")
        p.add_argument("--mode", default=None,
                       help="a writing mode (domain/articulation, e.g. memo/argue)")
        if cmd == "check":
            p.add_argument("--json", action="store_true")
            p.add_argument("--sarif", action="store_true", help="emit SARIF 2.1.0")
            p.add_argument("--gate", action="store_true", help="exit 1 if blocked")
            p.add_argument("--verbose", action="store_true")
            p.add_argument("--spans", action="store_true",
                           help="per-paragraph verdicts: find the paragraph that carries "
                                "the findings (a writing-quality view, never an "
                                "authorship finding)")
            p.add_argument("--content-free", action="store_true",
                           help="omit every verbatim substring from console/JSON/SARIF output")
        if cmd == "receipt":
            p.add_argument("--spans", action="store_true",
                           help="record a per-span (per-paragraph) receipt")
            p.add_argument("--redact", choices=["none", "drop", "hash"], default="none",
                           help="content-free audit receipt: drop or hash the matched text")
            p.add_argument("--reviewer", default=None,
                           help="record who screened it (else the CI actor, else unset)")
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
    args = ap.parse_args(argv)
    if args.cmd == "check":
        return _cmd_check(args)
    if args.cmd == "score":
        return _cmd_score(args)
    if args.cmd == "receipt":
        return _cmd_receipt(args)
    if args.cmd == "verify":
        return _cmd_verify(args)
    if args.cmd == "audit":
        return _cmd_audit(args)
    if args.cmd == "modes":
        for m in modes.names():
            print(m)
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
