#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.cli_receipts -- `articulate receipt`, `verify` and `audit`.

Standard library only; no server and no network.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

from . import modes, profiles, receipt
from .detector import binary_reason, ruleset_fingerprint


def cmd_receipt(args, inputs, profile_name):
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
    for name, text, reason in inputs(args.files):
        if reason:
            print(f"[articulate] {name}: cannot screen ({reason})", file=sys.stderr)
            continue
        # A --mode wins over profile inference, as in `check`, and the receipt
        # records the mode so verify replays the same screening.
        pname = None if mode else profile_name(name, text, args.profile)
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


def cmd_verify(args, decode):
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
    result, detail = receipt.verify_receipt(rec, decode(data))
    print(f"[articulate] {result}: {detail}")
    return {"Match": 0, "Drift": 1, "Unverifiable": 2}.get(result, 2)


def load_receipts(paths):
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


def within_days(created_at, days):
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


def _reverify_one(rec, decode):
    src = rec.get("file")
    if not src or not os.path.isfile(src):
        return "source-missing"
    try:
        with open(src, "rb") as fh:
            data = fh.read()
    except OSError:            # a race or a permission-denied source is unreadable
        return "source-unreadable"
    if binary_reason(data, name=src):
        return "source-unreadable"
    text = decode(data)
    # A source that changed since screening is a stale receipt (a real gate
    # failure), kept apart from an honest ruleset Unverifiable.
    if rec.get("text_sha256") != receipt.text_sha256(text):
        return "source-changed"
    return receipt.verify_receipt(rec, text)[0]


def _state(rec):
    """A receipt's findings state; pre-0.7.0 receipts recorded a verdict value."""
    if "findings_state" in rec:
        return rec["findings_state"]
    legacy = rec.get("verdict")
    return {"flagged": "has_findings", "clean": "no_findings"}.get(legacy, legacy or "?")


def cmd_audit(args, decode):
    """Query a directory of committed receipts locally: recorded findings states,
    blocked rules, stale-ruleset receipts, recent activity and (with --reverify)
    whether each receipt still holds against its source."""
    current_fp = ruleset_fingerprint()
    recs = list(load_receipts(args.paths or ["."]))
    by_gate, by_state, blocked_rules, reverify = Counter(), Counter(), Counter(), Counter()
    stale = recent = 0
    for _fp, rec in recs:
        by_gate[rec.get("gate", "?")] += 1
        by_state[_state(rec)] += 1
        stale += rec.get("ruleset_version") != current_fp
        recent += within_days(rec.get("created_at"), args.days)
        if rec.get("gate") == "blocked":
            for f in (rec.get("findings") or []):   # `or []` also covers findings: null
                blocked_rules[f.get("rule_id", "?")] += 1
        if args.reverify:
            reverify[_reverify_one(rec, decode)] += 1
    summary = {"receipts": len(recs), "by_gate": dict(by_gate),
               "by_findings_state": dict(by_state), "stale_ruleset": stale,
               f"recent_{args.days}d": recent,
               "blocked_by_rule": dict(blocked_rules.most_common(10))}
    if args.reverify:
        summary["reverify"] = dict(reverify)
    _print_audit(args, summary, blocked_rules)
    # Fail closed on a real integrity failure: the source drifted from its receipt,
    # changed since screening, or cannot be read. A stale-ruleset Unverifiable is
    # informational, never a gate failure.
    bad = (reverify.get("Drift", 0) + reverify.get("source-changed", 0)
           + reverify.get("source-unreadable", 0))
    return 1 if (args.gate and args.reverify and bad) else 0


def _print_audit(args, summary, blocked_rules):
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return
    print(f"[audit] {summary['receipts']} receipt(s); gate {summary['by_gate']}; "
          f"findings {summary['by_findings_state']}")
    print(f"[audit] stale-ruleset {summary['stale_ruleset']}; active in last "
          f"{args.days}d {summary[f'recent_{args.days}d']}")
    if blocked_rules:
        top = ", ".join(f"{r} x{n}" for r, n in blocked_rules.most_common(10))
        print(f"[audit] blocked by rule: {top}")
    if args.reverify:
        print(f"[audit] reverify: {summary['reverify']}")
