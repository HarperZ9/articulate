#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.cli_output -- how `articulate check` and `score` print and export.

Console lines, SARIF 2.1.0 and the content-free redaction. Every export carries
the does-not-prove line: in the JSON result, in each SARIF rule's help text
(which GitHub code scanning shows beside a result), and once at the end of the
`score` and `--spans` console output. Standard library only.
"""
from __future__ import annotations

from .rule_reasons import reason_for
from .tool_text import DOES_NOT_PROVE

_SARIF_LEVEL = {"HIGH": "error", "MEDIUM": "warning", "LOW": "note"}


def _pkgver():
    try:
        from . import __version__
        return __version__
    except Exception:  # noqa: BLE001
        return "0.0.0"


def redact(r):
    """Strip the content-bearing fields from a result, so no export path carries a
    verbatim substring or the exact offsets and length that reconstruct it under
    --content-free. Keeps only line, rule_id, tier and category per finding."""
    def strip(f):
        # A label enumerates a closed-vocabulary rule's candidate words, so drop it
        # and report the category alone.
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


def _help(f):
    reason = reason_for(f["category"])
    why = (f"Reader cost: {reason[0]} Source: {reason[1]}." if reason
           else "House style: gated only by a house profile." if f.get("house")
           else "Reported for review; it never blocks under a default profile.")
    return {"text": f"{why} {DOES_NOT_PROVE}",
            "markdown": f"{why}\n\n_{DOES_NOT_PROVE}_"}


def _region(f):
    # Exact offsets when present, else a line-only locator for a content-free run,
    # so the export never leaks the match length or position.
    if all(k in f for k in ("col", "start", "end")):
        return {"startLine": f["line"], "startColumn": f["col"],
                "endColumn": f["col"] + (f["end"] - f["start"]),
                "charOffset": f["start"], "charLength": f["end"] - f["start"]}
    return {"startLine": f["line"]}


def to_sarif(results):
    """SARIF 2.1.0 from check results. GitHub code scanning, Azure DevOps and
    reviewdog ingest this for inline pull request annotations."""
    rules, out = {}, []
    for r in results:
        uri = "stdin" if r["file"] == "<stdin>" else r["file"].replace("\\", "/")
        for f in r["high"] + r["medium"] + r.get("low", []):
            rid = f["rule_id"]
            desc = f.get("label") or f["category"]      # category only when redacted
            rules.setdefault(rid, {"id": rid, "name": f["category"],
                                   "shortDescription": {"text": desc},
                                   "help": _help(f)})
            msg = f"{desc}: {f['match']!r}" if f.get("match") is not None else desc
            out.append({
                "ruleId": rid,
                "level": _SARIF_LEVEL.get(f["tier"], "note"),
                "message": {"text": msg},
                "locations": [{"physicalLocation": {
                    "artifactLocation": {"uri": uri}, "region": _region(f)}}],
                "properties": {"profile": r.get("profile"), "tier": f["tier"],
                               "blocks": bool(f.get("gates")),
                               "house": bool(f.get("house"))},
            })
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{"tool": {"driver": {
            "name": "Articulate", "version": _pkgver(),
            "informationUri": "https://github.com/HarperZ9/articulate",
            "rules": list(rules.values())}},
            "results": out}],
    }


def _tag(f):
    return f"{f['tier']} {f['category']}" + (", house style" if f.get("house") else "")


def print_check(name, pname, r, verbose):
    n = r["counts"]
    state = ("no findings" if r["findings"] == "no_findings"
             else f"{n['high']} high, {n['medium']} medium")
    print(f"[articulate] {name} [{pname}]: {state}, {n['low']} low, gate {r['gate']}")
    # A LOW finding that a profile promotes blocks, so it always prints.
    for f in r["high"] + r["medium"] + [f for f in r["low"] if f.get("gates")]:
        print(f"  L{f['line']} [{_tag(f)}] {f.get('label', f['category'])}: {f.get('snippet', '')}")
    if verbose:
        for f in (f for f in r["low"] if not f.get("gates")):
            print(f"  L{f['line']} [{_tag(f)}] "
                  f"{f.get('label', f['category'])}: {f.get('snippet', '')}")
    if r["gate"] == "blocked":
        print(f"  {DOES_NOT_PROVE}")


def print_spans(name, pname, blocks):
    """Per-paragraph counts by rule, in document order. No per-paragraph gate and
    no label: the gate belongs to the document."""
    print(f"[articulate] {name} [{pname}]: {len(blocks)} paragraph(s)")
    for b in blocks:
        c = b["counts"]
        rules = ", ".join(f"{k} x{v}" for k, v in b["rule_counts"].items()) or "no findings"
        print(f"  L{b['start_line']}-{b['end_line']} ({c['high']}H/{c['medium']}M/"
              f"{c['low']}L): {rules}")
    print(f"[articulate] {DOES_NOT_PROVE}")


def print_score(name, pname, r):
    d = r["density"]
    dens = (f"density {d['per_1000']} per 1,000 words [{d['ci'][0]}, {d['ci'][1]}]"
            if d["shown"] else f"density not shown under {d['min_words']} words")
    print(f"[articulate] {name} [{pname}]: gate {r['gate']}, {r['words']} words, {dens}")
    for rule, n in r["rule_counts"].items():
        print(f"  {n:>4}  {rule}")
