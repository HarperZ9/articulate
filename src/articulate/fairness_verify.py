#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.fairness_verify -- is a committed fairness receipt the one its own
numbers and its pin say it is?

- A stored gate flag must not claim more than the stored numbers allow. G1's
  raw gap and interval are recomputed from the stored counts and must equal the
  stored values. A G1 row stored as passing fails the check when its raw gap,
  its raw interval (at 500 or more documents per arm) or a within-group gap lies
  outside the G1 line. A G2 row stored as passing fails the check when one of
  its stored states is skewed or inconclusive. G4 has no flag: the gate summary
  reads the stored count of changed documents.
- What it cannot recompute without the documents, it trusts: each stored G2
  state, each within-group gap and each count of changed documents. A pin is
  what binds those numbers to a receipt.
- SHA256SUMS in the receipt folder pins receipts by their bytes, in the format
  `sha256sum -c SHA256SUMS` reads. When the file exists, every receipt the
  release check reads must be listed there with the same digest.

Standard library only.
"""
from __future__ import annotations

import hashlib
import os

from . import fairness_gates as G
from . import fairness_stats as S

PINS = "SHA256SUMS"
_FAILING_STATES = ("skewed", "inconclusive")


def _pct(x):
    return round(100 * x, 1)


def _g1_problem(where, g1):
    """A problem line when a stored G1 row disagrees with its own numbers."""
    kp, np_ = g1["protected"]
    kr, nr = g1["reference"]
    d, (lo, hi) = S.newcombe(kp, np_, kr, nr)
    if g1["diff"] != _pct(d) or list(g1["ci"]) != [_pct(lo), _pct(hi)]:
        return f"{where}: the stored G1 gap or interval differs from its own counts"
    if not g1["pass"]:
        return None
    t = G.THRESHOLDS
    bad = abs(d) > t["g1_point"]
    if np_ >= t["g1_ci_min_n"] and nr >= t["g1_ci_min_n"]:
        bad = bad or lo < -t["g1_ci"] or hi > t["g1_ci"]
    # A within-group gap is stored rounded to 0.1 point, so only a value that
    # rounds above the line is known to lie outside it.
    line = 100 * t["g1_point"]
    bad = bad or any(abs(g1[k]) > line for k in ("banded_diff", "matched_diff")
                     if g1.get(k) is not None)
    return f"{where}: G1 is stored as passing and its own numbers fail" if bad else None


def _g2_problems(where, g2):
    out = []
    for rule, row in g2.items():
        states = [v["state"] for k, v in row.items() if k.startswith("toward_")]
        if row["pass"] and any(s in _FAILING_STATES for s in states):
            out.append(f"{where}: G2 {rule} is stored as passing with a failing state")
    return out


def flag_problems(rec):
    """Every stored G1 or G2 flag in a receipt that claims more than its stored
    numbers allow. An empty list means the flags agree with the numbers."""
    out = []
    for key, v in sorted((rec.get("results") or {}).items()):
        for name, c in sorted(v.get("comparisons", {}).items()):
            where = f"{key} {name}"
            problem = _g1_problem(where, c["g1"])
            if problem:
                out.append(problem)
            out += _g2_problems(where, c["g2"])
    return out


def read_pins(directory):
    """{file name: digest} from DIR/SHA256SUMS, or None when there is no such file."""
    path = os.path.join(directory, PINS)
    if not os.path.isfile(path):
        return None
    pins = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            parts = line.split(None, 1)
            if len(parts) == 2:
                pins[parts[1].strip().lstrip("*")] = parts[0].lower()
    return pins


def pin_problem(directory, name, pins):
    """A problem line when pins exist and this receipt is unlisted or differs."""
    if pins is None:
        return None
    if name not in pins:
        return f"{name} is not pinned in {PINS}"
    with open(os.path.join(directory, name), "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    return None if digest == pins[name] else f"{name} does not match its pin in {PINS}"
