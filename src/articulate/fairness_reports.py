#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.fairness_reports -- G1 readings that are reported and never gate.

  writer_cluster     the raw block-rate gap with a percentile bootstrap that
                     resamples writers, not texts, when the documents name their
                     writer. Texts by one writer are not independent, so the
                     text-level interval is too narrow when writers contribute
                     several texts.
  length_quintiles   the gap within word-count quintiles of the two arms
                     pooled, and the Mantel-Haenszel gap over them with a Sato
                     interval. A document is blocked by any one blocking
                     finding, so a longer text has more chances, and a length
                     difference between groups can drive the raw gap.

Neither changes a gate (fairness/PREREG.md). Both hold counts and rates only:
no quintile cut point is stored, since a cut point is one document's length.

Standard library only.
"""
from __future__ import annotations

import bisect

from . import fairness_stats as S

B = 2000


def _pct(x):
    return None if x is None or x != x else round(100 * x, 1)


def writer_cluster(prot, ref):
    """The cluster-bootstrap reading, or None when no document names a writer.
    A document with no writer is a cluster of its own."""
    if not any(d.get("writer") is not None for d in prot + ref):
        return None

    def rows(docs, arm):
        return [((arm, d["writer"]) if d.get("writer") is not None else (arm, "#", i),
                 int(bool(d["blocked"]))) for i, d in enumerate(docs)]

    p, r = rows(prot, "p"), rows(ref, "r")
    est, (lo, hi) = S.cluster_boot_diff(p, r, b=B)
    return {"writers": [len({c for c, _y in p}), len({c for c, _y in r})],
            "diff": _pct(est), "ci": [_pct(lo), _pct(hi)], "b": B, "seed": S.SEED,
            "gates": False}


def length_quintiles(prot, ref):
    """The gap within each word-count quintile, and pooled over the quintiles,
    or None when the arms hold fewer than five documents in all or a document
    carries no word count."""
    if any(d.get("words") is None for d in prot + ref):
        return None
    words = sorted(d["words"] for d in prot + ref)
    n = len(words)
    if n < 5:
        return None
    cuts = [words[(k * n) // 5] for k in range(1, 5)]

    def counts(docs, q):
        inside = [d for d in docs if bisect.bisect_right(cuts, d["words"]) == q]
        return [sum(bool(d["blocked"]) for d in inside), len(inside)]

    bins, strata = [], []
    for q in range(5):
        kp, np_ = counts(prot, q)
        kr, nr = counts(ref, q)
        diff = kp / np_ - kr / nr if np_ and nr else None
        bins.append({"protected": [kp, np_], "reference": [kr, nr], "diff": _pct(diff)})
        strata.append((kp, np_, kr, nr))
    pooled = S.stratified_diff(strata)
    return {"bins": bins, "diff": _pct(pooled[0]) if pooled else None,
            "ci": [_pct(pooled[1][0]), _pct(pooled[1][1])] if pooled else None,
            "gates": False}
