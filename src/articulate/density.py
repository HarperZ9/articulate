#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.density -- findings per 1,000 words, with an interval.

Density counts the findings that block under the profile in use and carry a
cited reader-cost reason (rule_reasons); house-pack findings never count. Two findings
of the same category whose spans overlap count once, so one phrase that two
patterns of a family both match is one finding, not two. The count carries an
exact Poisson interval, and density is shown only at DENSITY_MIN_WORDS words or
more, because a rate over a short text swings on a single finding. Per-rule
counts are always reported beside it and are the primary output.

Density is a summary of named findings. It is not a likelihood and it says
nothing about who or what wrote a text. Standard library only.
"""
from __future__ import annotations

from .fairness_stats import poisson_exact

DENSITY_MIN_WORDS = 250


def gating_findings(result):
    """The findings that block under the profile, de-duplicated by overlapping
    span within a category."""
    found = [f for t in ("high", "medium", "low") for f in result.get(t, ())
             if f.get("gates") and not f.get("house")]
    found.sort(key=lambda f: (f["category"], f.get("start", 0), f.get("end", 0)))
    kept, last = [], {}
    for f in found:
        prev = last.get(f["category"])
        if prev is not None and "start" in f and f["start"] < prev["end"]:
            prev["end"] = max(prev["end"], f["end"])
            continue
        entry = {"category": f["category"], "start": f.get("start", 0),
                 "end": f.get("end", 0)}
        last[f["category"]] = entry
        kept.append(entry)
    return kept


def density(result):
    """{count, words, per_1000, ci, shown} for a check_text result."""
    count = len(gating_findings(result))
    words = result.get("cadence", {}).get("words", 0) or 0
    lo, hi = poisson_exact(count)
    shown = words >= DENSITY_MIN_WORDS
    scale = 1000.0 / words if words else 0.0
    return {
        "count": count,
        "words": words,
        "per_1000": round(count * scale, 2) if shown else None,
        "ci": [round(lo * scale, 2), round(hi * scale, 2)] if shown else None,
        "shown": shown,
        "min_words": DENSITY_MIN_WORDS,
    }
