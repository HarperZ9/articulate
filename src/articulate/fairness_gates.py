#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.fairness_gates -- the pre-registered gates G1 to G7.

Each function takes per-document measurements (see fairness.measure) for two
sets and returns a plain dict for the receipt. Thresholds live in THRESHOLDS
and in fairness/PREREG.md, and a test pins that the two agree.

  G1  block-rate gap, two-sided, raw and within score bands
  G2  per-rule skew in four states: skewed, not skewed, bounded, inconclusive
  G3  paired rewrites (report only; it concerns origin, so it never gates)
  G4  layout invariance (computed in fairness.py, which owns the rewrap)
  G5  cadence (report only while no cadence signal gates)
  G6  editor behavior by group (needs a model run; reported as not run)
  G7  absolute block rate on human text

Standard library only.
"""
from __future__ import annotations

from . import fairness_stats as S

THRESHOLDS = {
    "g1_point": 0.05,          # |block-rate difference| at most 5.0 points
    "g1_ci": 0.10,             # both 95% limits within 10.0 points ...
    "g1_ci_min_n": 500,        # ... when both arms hold at least 500 documents
    "g2_min_docs": 5,          # a skew call needs this many documents in the higher arm
    "g2_ratio": 2.0,           # pooled per-1,000-word ratio that counts as skew
    "g2_bounded_share": 0.02,  # "bounded": fires on at most 2% of documents per arm
    "g5_ratio": 2.0,           # cadence: protected rate at most twice the reference
    "g5_diff_hi": 0.05,        # ... or a difference whose upper limit is at most 5 points
    "g7_review": 0.10,         # absolute block rate on human text that opens a review
}


def _pct(x):
    return None if x is None else round(100 * x, 1)


def g1(prot, ref):
    """Block-rate gap for one comparison under one profile."""
    t = THRESHOLDS
    kp, np_ = sum(d["blocked"] for d in prot), len(prot)
    kr, nr = sum(d["blocked"] for d in ref), len(ref)
    d, (lo, hi) = S.newcombe(kp, np_, kr, nr)
    ok = abs(d) <= t["g1_point"]
    if np_ >= t["g1_ci_min_n"] and nr >= t["g1_ci_min_n"]:
        ok = ok and -t["g1_ci"] <= lo and hi <= t["g1_ci"]
    out = {"protected": [kp, np_], "reference": [kr, nr],
           "diff": _pct(d), "ci": [_pct(lo), _pct(hi)],
           "reverse_diff": _pct(-d), "reverse_ci": [_pct(-hi), _pct(-lo)],
           "min_detectable": _pct(S.min_detectable(np_, nr, max(kp + kr, 1) / (np_ + nr))),
           "pass": ok}
    bands = sorted({x.get("score") for x in prot + ref if x.get("score") is not None})
    if bands:
        strata = [(sum(x["blocked"] for x in prot if x.get("score") == b),
                   sum(1 for x in prot if x.get("score") == b),
                   sum(x["blocked"] for x in ref if x.get("score") == b),
                   sum(1 for x in ref if x.get("score") == b)) for b in bands]
        st = S.stratified_diff(strata)
        if st is not None:
            out["banded_diff"] = _pct(st[0])
            out["banded_ci"] = [_pct(st[1][0]), _pct(st[1][1])]
            out["pass"] = ok and abs(st[0]) <= t["g1_point"]
    dp = [x["density"] for x in prot if x["density"] is not None]
    dr = [x["density"] for x in ref if x["density"] is not None]
    if dp and dr:
        est, (dlo, dhi) = S.boot2(dp, dr, lambda a, b: S.median(a) - S.median(b), b=2000)
        out["density_median_diff"] = [round(est, 2), [round(dlo, 2), round(dhi, 2)]]
    return out


def _pooled(docs, rule):
    words = sum(d["words"] for d in docs)
    hits = sum(d["rules"].get(rule, 0) for d in docs)
    return hits / words * 1000 if words else 0.0


def _ratio(a_docs, b_docs, rule):
    ra, rb = _pooled(a_docs, rule), _pooled(b_docs, rule)
    if rb == 0:
        return float("inf") if ra > 0 else None
    return ra / rb


_G2_CACHE = {}


def fmt(v):
    """A ratio for the receipt: rounded, "inf" for an unbounded one, None if undefined."""
    if v is None or v != v:
        return None
    return "inf" if v == float("inf") else round(v, 2)


def _ratio_ci(hi_docs, lo_docs, rule):
    key = (rule, tuple((d["words"], d["rules"].get(rule, 0)) for d in hi_docs),
           tuple((d["words"], d["rules"].get(rule, 0)) for d in lo_docs))
    if key not in _G2_CACHE:
        _G2_CACHE[key] = S.boot2(hi_docs, lo_docs, lambda a, b: _ratio(a, b, rule), b=2000)
    return _G2_CACHE[key]


def g2_state(hi_docs, lo_docs, rule):
    """The skew state of one rule, in the direction hi over lo."""
    t = THRESHOLDS
    fired_hi = sum(1 for d in hi_docs if d["rules"].get(rule))
    fired_lo = sum(1 for d in lo_docs if d["rules"].get(rule))
    est, (lo, hi) = _ratio_ci(hi_docs, lo_docs, rule)
    share = max(fired_hi / len(hi_docs), fired_lo / len(lo_docs))
    if fired_hi + fired_lo == 0:
        state = "bounded"
    elif (fired_hi >= t["g2_min_docs"] and est is not None and est >= t["g2_ratio"]
          and lo is not None and lo > 1):
        state = "skewed"
    elif hi is not None and hi == hi and hi < t["g2_ratio"]:
        state = "not skewed"
    elif share <= t["g2_bounded_share"]:
        state = "bounded"
    else:
        state = "inconclusive"
    return {"docs": [fired_hi, fired_lo],
            "per_1000": [round(_pooled(hi_docs, rule), 3), round(_pooled(lo_docs, rule), 3)],
            "ratio": fmt(est), "ci": [fmt(lo), fmt(hi)], "state": state}


def g2(prot, ref, rules, design):
    """Per-rule states. Matched-prompt pairs are read both ways; a proxy pair
    only in the protected direction."""
    out = {}
    for rule in sorted(rules):
        row = {"toward_protected": g2_state(prot, ref, rule)}
        if design == "matched":
            row["toward_reference"] = g2_state(ref, prot, rule)
        states = [v["state"] for v in row.values()]
        row["pass"] = not any(s in ("skewed", "inconclusive") for s in states)
        out[rule] = row
    return out


def g3(a_docs, b_docs):
    """Paired rewrites: the same text before and after a rewrite. Report only."""
    by = {d.get("key"): d for d in b_docs}
    pairs = [(d, by[d.get("key")]) for d in a_docs if d.get("key") in by]
    b = sum(1 for p, q in pairs if p["blocked"] and not q["blocked"])
    c = sum(1 for p, q in pairs if q["blocked"] and not p["blocked"])
    return {"pairs": len(pairs), "original_only": b, "rewrite_only": c,
            "mcnemar_p": round(S.mcnemar_exact(b, c), 4), "gates": False}


def g5(prot, ref, cadence_gates):
    t = THRESHOLDS
    kp, np_ = sum(d["uniform"] for d in prot), len(prot)
    kr, nr = sum(d["uniform"] for d in ref), len(ref)
    d, (lo, hi) = S.newcombe(kp, np_, kr, nr)
    rate_ok = kp / np_ <= t["g5_ratio"] * (kr / nr) if nr else True
    ok = rate_ok or hi <= t["g5_diff_hi"]
    return {"uniform": [[kp, np_], [kr, nr]], "diff": _pct(d), "ci": [_pct(lo), _pct(hi)],
            "gates": bool(cadence_gates), "pass": ok if cadence_gates else None}


def g7(docs):
    k, n = sum(d["blocked"] for d in docs), len(docs)
    lo, hi = S.wilson(k, n)
    rate = k / n if n else 0.0
    return {"blocked": [k, n], "rate": _pct(rate), "ci": [_pct(lo), _pct(hi)],
            "review": rate > THRESHOLDS["g7_review"]}


G6_NOT_RUN = {"state": "not run",
              "reason": "G6 needs editor runs through a model backend on every arm; "
                        "the local harness does not call a model"}
