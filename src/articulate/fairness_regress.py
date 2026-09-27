#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.fairness_regress -- gate rows of a fairness receipt, and the
comparison an override must pass.

A gate row is one gate under one profile, and for G1, G2 and G5 one comparison:
"G1 essay toefl-vs-abstracts". Rows come from the receipt's own results and its
own list of bound profiles, so a receipt from an older ruleset reads the same
way. A comparison a profile skipped counts as a failing G1 and G2 row.

Standard library only.
"""
from __future__ import annotations


def _comparison_rows(p, name, c):
    return {
        f"G1 {p} {name}": bool(c["g1"]["pass"]),
        f"G2 {p} {name}": all(r["pass"] for r in c["g2"].values()),
        f"G5 {p} {name}": c["g5"]["pass"] is not False,
    }


def gate_rows(rec):
    """{row name: passes} for every bound profile in a receipt."""
    bound = set(rec.get("bound_profiles") or ())
    rows = {}
    for v in (rec.get("results") or {}).values():
        for p in (x for x in v.get("profiles", ()) if not bound or x in bound):
            rows[f"G4 {p}"] = v["g4"]["changed"] == 0
            for name, c in v.get("comparisons", {}).items():
                rows.update(_comparison_rows(p, name, c))
            for name in v.get("skipped", ()):
                rows[f"G1 {p} {name}"] = rows[f"G2 {p} {name}"] = False
    return rows


def compare(old, new, show=12):
    """(summary line, regressed rows). A row regresses when it passes in `old`
    and fails, or is missing, in `new`, and when it fails in `new` and `old`
    lacks it: a newly bound profile that fails sends writers to a failing gate
    the published ruleset did not have."""
    dropped = sorted(k for k, ok in old.items() if ok and not new.get(k, False))
    added = [k for k in new if k not in old]
    added_failing = sorted(k for k in added if not new[k])
    regressed = dropped + added_failing
    fixed = sum(1 for k, ok in old.items() if not ok and new.get(k, False))
    both = sum(1 for k, ok in old.items() if ok and new.get(k, False))
    still = sum(1 for k, ok in old.items() if not ok and k in new and not new[k])
    line = (f"{both} rows pass in both, {fixed} fail before and pass now, "
            f"{still} fail in both, {len(dropped)} pass before and fail now, "
            f"{len(added)} new rows ({len(added_failing)} failing)")
    if regressed:
        more = f" and {len(regressed) - show} more" if len(regressed) > show else ""
        line += ": " + ", ".join(regressed[:show]) + more
    return line, regressed
