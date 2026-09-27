"""Synthetic fairness receipts built from a committed one, for the release-check tests.

The release check compares each stored gate flag with the stored numbers
(articulate.fairness_verify), so a receipt made to pass must have numbers that
pass. `all_pass` sets them: equal zero block counts in both arms, a zero gap
with its own Newcombe interval, "not skewed" G2 states and no layout change.
Nothing here measures any group.
"""
import copy

from articulate import fairness, fairness_stats


def _pct(x):
    return round(100 * x, 1)


def all_pass(rec):
    """A copy of `rec` whose every G1, G2 and G4 row passes, numbers included."""
    rec = copy.deepcopy(rec)
    for v in rec["results"].values():
        v["g4"]["changed"] = 0
        for c in v["comparisons"].values():
            g1 = c["g1"]
            np_, nr = g1["protected"][1], g1["reference"][1]
            d, (lo, hi) = fairness_stats.newcombe(0, np_, 0, nr)
            g1.update(protected=[0, np_], reference=[0, nr], diff=_pct(d),
                      ci=[_pct(lo), _pct(hi)], reverse_diff=_pct(-d),
                      reverse_ci=[_pct(-hi), _pct(-lo)])
            g1["pass"] = True
            for k in ("banded_diff", "matched_diff"):
                if k in g1:
                    g1[k] = 0.0
            for row in c["g2"].values():
                for k in row:
                    if k.startswith("toward_"):
                        row[k]["state"] = "not skewed"
                row["pass"] = True
    return rec


def as_ruleset(rec, fp):
    """A copy of `rec` under ruleset `fp`, with its gate summary recomputed."""
    rec = copy.deepcopy(rec)
    rec["ruleset_version"] = fp
    rec["gates"] = fairness._gate_summary(rec["results"], fairness.bound_profiles())
    return rec
