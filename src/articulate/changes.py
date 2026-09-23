#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
articulate.changes -- the change report for a rewrite.

`build(original, final)` aligns the two texts sentence by sentence and returns
each changed pair: the sentence before, the sentence after, the detector
findings in the original sentence (the tells the rewrite was asked to fix), the
findings that remain in the new sentence, and the meaning-guard rows located in
that pair. It also carries the overall meaning verdict and every candidate the
guard refused, with the reason.

The pairing uses difflib over whitespace-normalized sentences, so a merged or
split sentence shows up as one replace record spanning several sentences. The
findings column lists what the detector saw in the original sentence; it does
not prove the model changed the sentence for that reason. Standard library only.
"""
from __future__ import annotations

import bisect
import difflib
import json
import os
import re

from . import meaning

SCHEMA = "articulate/changes/v1"
_SENT_END = re.compile("(?<=[.!?])[\"'”’)\\]]*(\\s+)")
_BLOCK_START = re.compile(r"^\s{0,3}(?:[-*+]\s|\d{1,3}[.)]\s|#{1,6}\s|>|\|)")


def _blocks(text):
    """(start, end) of paragraph-like blocks: split at blank lines and at lines
    that open a list item, heading, quote, or table row. A fenced code block is
    one block."""
    out, pos, start, in_fence = [], 0, None, False
    for line in text.splitlines(keepends=True):
        body = line.strip()
        is_fence = body.startswith(("```", "~~~"))
        if in_fence:
            if is_fence:                       # the closing fence ends the block
                out.append((start, pos + len(line)))
                start, in_fence = None, False
        elif is_fence or not body or _BLOCK_START.match(line):
            if start is not None:
                out.append((start, pos))
            start = pos if body else None
            in_fence = is_fence
            if body.startswith("#"):           # a heading is a block of one line
                out.append((pos, pos + len(line)))
                start = None
        elif start is None:
            start = pos
        pos += len(line)
    if start is not None:
        out.append((start, pos))
    return out


def segments(text):
    """(start, end) of each sentence-like segment, in document order."""
    out = []
    for bstart, bend in _blocks(text):
        block = text[bstart:bend].rstrip()
        pos = 0
        if not block.lstrip().startswith(("```", "~~~")):
            for m in _SENT_END.finditer(block):
                if block[pos:m.start(1)].strip():
                    out.append((bstart + pos, bstart + m.start(1)))
                pos = m.end()
        if block[pos:].strip():
            out.append((bstart + pos, bstart + len(block)))
    return out


def _span(text, segs, starts):
    if not segs:
        return None
    s, e = segs[0][0], segs[-1][1]
    return {"text": text[s:e], "start": s, "end": e,
            "line_start": bisect.bisect_right(starts, s),
            "line_end": bisect.bisect_right(starts, max(s, e - 1))}


def _findings(result, span):
    if not result or span is None:
        return []
    out = []
    for f in result["high"] + result["medium"] + result["low"]:
        if span["start"] <= f["start"] < span["end"]:
            out.append({"rule_id": f["rule_id"], "tier": f["tier"], "line": f["line"],
                        "message": f"{f.get('label', f['category'])}: {f.get('match', '')!r}"})
    return out


def _meaning_rows(report, before, after):
    rows = []
    for r in report["items"]:
        if r["status"] == "kept":
            continue
        b, a = r["before"], r["after"]
        if (b and before and before["start"] <= b["start"] < before["end"]) or \
                (a and after and after["start"] <= a["start"] < after["end"]):
            rows.append(meaning.describe_item(r))
    return rows


def _pairs(original, final):
    a_segs, b_segs = segments(original), segments(final)
    norm = [[" ".join(t[s:e].split()) for s, e in segs]
            for t, segs in ((original, a_segs), (final, b_segs))]
    sm = difflib.SequenceMatcher(None, norm[0], norm[1], autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op != "equal":
            yield op, a_segs[i1:i2], b_segs[j1:j2]


def build(original, final, *, profile=None, guard=None, freeze=()):
    """The change report as a dict. `guard` (a RewriteGuard) contributes its
    refusals; `profile` sets the detector profile for the findings columns."""
    from .detector import check_text
    before_r = check_text(original, profile=profile)
    after_r = check_text(final, profile=profile)
    report = meaning.compare(original, final, freeze=freeze)
    starts = [[0] + [m.end() for m in re.finditer("\n", t)] for t in (original, final)]
    changes = []
    for op, a_segs, b_segs in _pairs(original, final):
        before, after = _span(original, a_segs, starts[0]), _span(final, b_segs, starts[1])
        changes.append({"index": len(changes) + 1, "op": op, "before": before,
                        "after": after, "findings_before": _findings(before_r, before),
                        "findings_after": _findings(after_r, after),
                        "meaning": _meaning_rows(report, before, after)})
    refusals = [{"stage": e["stage"], "blocking": _blocking_text(e)}
                for e in (guard.refusals() if guard else [])]
    return {"schema": SCHEMA, "changes": changes, "refusals": refusals,
            "summary": {"changes": len(changes), "meaning": report["verdict"],
                        "findings_before": _count(before_r), "findings_after": _count(after_r)},
            "does_not_prove": meaning.DOES_NOT_PROVE}


def _count(r):
    return len(r["high"]) + len(r["medium"]) + len(r["low"])


def _blocking_text(entry):
    if entry["stage"] == "meaning":
        return [meaning.describe_item(r) for r in entry["blocking"]]
    return [f"{p['problem']} placeholder {p.get('kind', '')} {p.get('text', p['placeholder'])!r}"
            for p in entry["blocking"]]


def _clip(text, n=160):
    one = " ".join(text.split())
    return one if len(one) <= n else one[: n - 3] + "..."


def format_report(rep, header=""):
    """The human-readable change report."""
    s = rep["summary"]
    lines = [f"[changes] {header}{s['changes']} change(s); detector findings "
             f"{s['findings_before']} -> {s['findings_after']}; meaning {s['meaning']}"]
    for c in rep["changes"]:
        b, a = c["before"], c["after"]
        where = f"L{(b or a)['line_start']}" if (b or a) else ""
        lines.append(f"  #{c['index']} {where} {c['op']}")
        if b:
            lines.append(f"    - {_clip(b['text'])}")
        if a:
            lines.append(f"    + {_clip(a['text'])}")
        for f in c["findings_before"]:
            lines.append(f"      flagged before: {f['tier']} {f['rule_id']}: {f['message']}")
        for f in c["findings_after"]:
            lines.append(f"      still flagged: {f['tier']} {f['rule_id']}: {f['message']}")
        for m in c["meaning"]:
            lines.append(f"      meaning: {m}")
    for r in rep["refusals"]:
        lines.append(f"[changes] refused a candidate ({r['stage']}): " + "; ".join(r["blocking"][:5]))
    lines.append(f"[changes] does not prove: {rep['does_not_prove']}")
    return "\n".join(lines)


def add_arguments(ap):
    ap.add_argument("--explain", nargs="?", const="text", choices=("text", "json"),
                    default=None, help="after --fix or --polish, print the change "
                                       "report (text, or json)")


def default_out(path, suffix):
    """The editor's default output path: post.md -> post.fixed.md."""
    stem, ext = os.path.splitext(path)
    return f"{stem}.{suffix}{ext}"


def _profile(args, path, text):
    from . import modes, profiles
    if getattr(args, "mode", None):
        return modes.load(args.mode)
    return profiles.resolve(path=path, text=text)


def finish(args, path, out_path, guard, rc):
    """Print the change report for a finished fix or polish run, if asked."""
    if not getattr(args, "explain", None):
        return rc
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            original = fh.read()
        with open(out_path, encoding="utf-8", errors="replace") as fh:
            final = fh.read()
    except OSError as e:
        print(f"[changes] cannot build the change report: {e}")
        return rc or 1
    rep = build(original, final, profile=_profile(args, path, original), guard=guard,
                freeze=guard.freeze)
    if args.explain == "json":
        print(json.dumps(dict(rep, file=path, out=out_path), ensure_ascii=False, indent=2))
    else:
        head = f"{os.path.basename(path)} -> {os.path.basename(out_path)}: "
        print(format_report(rep, head))
    return rc
