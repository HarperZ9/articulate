#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.fairness_stats -- interval arithmetic for the fairness harness.

Ported from the research audit's audit_stats.py, with one change: every
bootstrap draws an index as int(rng.random() * n). Python promises the same
random() sequence for a seed across versions, and makes no such promise for
randrange, so the old draw could give a different interval on a newer Python.

  wilson          95% Wilson score interval for a proportion
  newcombe        95% Newcombe hybrid-score interval for p1 - p2 (method 10)
  stratified_diff a difference of proportions pooled over strata (score bands)
                  with Cochran-Mantel-Haenszel weights, plus a Newcombe-style
                  interval built from the pooled counts
  boot2           percentile bootstrap for a statistic of two independent samples
  mcnemar_exact   two-sided exact McNemar p-value from the discordant counts
  poisson_exact   exact (Garwood) 95% interval for a Poisson count
  min_detectable  the smallest difference an arm of this size can tell from zero

Standard library only.
"""
from __future__ import annotations

import math
import random

B = 10000
SEED = 20260925
Z = 1.959963984540054


def wilson(k, n):
    """(low, high) of the 95% Wilson interval for k successes in n trials."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + Z * Z / n
    centre = (p + Z * Z / (2 * n)) / den
    half = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / den
    return (max(0.0, centre - half), min(1.0, centre + half))


def newcombe(k1, n1, k2, n2):
    """(p1 - p2, (low, high)) with the Newcombe hybrid-score interval."""
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1)
    l2, u2 = wilson(k2, n2)
    d = p1 - p2
    lo = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return d, (lo, hi)


def stratified_diff(strata):
    """strata: list of (k1, n1, k2, n2), one per score band. Returns the
    CMH-weighted difference and an interval from the pooled Newcombe limits
    scaled to the weighted estimate, or None when no stratum has both arms."""
    usable = [s for s in strata if s[1] and s[3]]
    if not usable:
        return None
    weights = [(n1 * n2) / (n1 + n2) for _k1, n1, _k2, n2 in usable]
    total = sum(weights)
    d = sum(w * (k1 / n1 - k2 / n2) for w, (k1, n1, k2, n2) in zip(weights, usable)) / total
    k1 = sum(s[0] for s in usable)
    n1 = sum(s[1] for s in usable)
    k2 = sum(s[2] for s in usable)
    n2 = sum(s[3] for s in usable)
    pooled, (lo, hi) = newcombe(k1, n1, k2, n2)
    return d, (d - (pooled - lo), d + (hi - pooled))


def _draw(rng, xs):
    n = len(xs)
    return [xs[int(rng.random() * n)] for _ in range(n)]


def percentile(vals, a=0.025):
    """Percentile interval over finite and infinite values; None is dropped."""
    vals = sorted(v for v in vals if v is not None and not (isinstance(v, float)
                                                            and math.isnan(v)))
    if not vals:
        return (float("nan"), float("nan"))
    return (vals[int(a * (len(vals) - 1))], vals[int((1 - a) * (len(vals) - 1))])


def boot2(xs, ys, stat, seed=SEED, b=B):
    """(stat(xs, ys), (low, high)): each sample resampled on its own."""
    rng = random.Random(seed)
    out = [stat(_draw(rng, xs), _draw(rng, ys)) for _ in range(b)]
    return stat(xs, ys), percentile(out)


def mcnemar_exact(b, c):
    """Two-sided exact binomial test on the discordant pair counts b and c."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def _chi2_quantile(p, df):
    """Quantile of the chi-square distribution by bisection on the regularized
    lower incomplete gamma function. Enough precision for a 95% interval."""
    lo, hi = 0.0, max(10.0, df * 10.0)
    for _ in range(200):
        mid = (lo + hi) / 2
        if _gamma_p(df / 2.0, mid / 2.0) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _gamma_p(a, x):
    """Regularized lower incomplete gamma P(a, x), by series or continued fraction."""
    if x <= 0:
        return 0.0
    if x < a + 1:
        term = total = 1.0 / a
        ap = a
        for _ in range(1000):
            ap += 1
            term *= x / ap
            total += term
            if abs(term) < abs(total) * 1e-15:
                break
        return total * math.exp(-x + a * math.log(x) - math.lgamma(a))
    return 1.0 - _gamma_q_cf(a, x)


def _gamma_q_cf(a, x):
    tiny = 1e-300
    b = x + 1 - a
    c = 1 / tiny
    d = 1 / b
    h = d
    for i in range(1, 1000):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        d = tiny if abs(d) < tiny else d
        c = b + an / c
        c = tiny if abs(c) < tiny else c
        d = 1 / d
        delta = d * c
        h *= delta
        if abs(delta - 1) < 1e-15:
            break
    return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


def poisson_exact(k):
    """(low, high) exact 95% interval for a Poisson count k (Garwood 1936)."""
    lo = 0.0 if k == 0 else _chi2_quantile(0.025, 2 * k) / 2
    hi = _chi2_quantile(0.975, 2 * (k + 1)) / 2
    return lo, hi


def min_detectable(n1, n2, k2):
    """The smallest excess block rate in the first arm whose Newcombe 95% interval
    would exclude zero, holding the second arm at its observed count k2. It
    uses the same interval the gap is reported with, so it holds near a zero
    rate, where a normal approximation does not. It states power and reports no
    result; nan when no count up to n1 would do."""
    if not n1 or not n2:
        return float("nan")
    for k1 in range(0, n1 + 1):
        d, (lo, _hi) = newcombe(k1, n1, k2, n2)
        if d > 0 and lo > 0:
            return d
    return float("nan")


def median(xs):
    xs = sorted(xs)
    if not xs:
        return float("nan")
    m = len(xs) // 2
    return xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2
