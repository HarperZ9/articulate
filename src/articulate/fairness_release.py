#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.fairness_release -- the release check on a committed fairness receipt.

It reads DIR/<fingerprint>.json for the current ruleset. It fails when the
receipt is missing, was run on a manifest not listed in RELEASE_MANIFESTS,
leaves out a required comparison or a bound profile, or when the gates
recomputed from the receipt's own rows fail or disagree with its stored summary.
The stored `release_ok` is never trusted on its own.

A maintainer can record an override for one exact ruleset in
DIR/<fingerprint>.override.json, with a reason and who decided. The check then
passes, prints the reason and still lists every failure. No override exists in
this repository; creating one is a maintainer decision.

Standard library only.
"""
from __future__ import annotations

import json
import os

from . import fairness as F
from .fingerprint import ruleset_fingerprint

# The manifests a release receipt may come from, and the comparisons it must
# hold. fairness/PREREG.md lists the same values, and a test pins that they agree.
RELEASE_MANIFESTS = (
    "sha256:71ab34e241bd4315f81d4f0fefcd47eb4538c918b9584cebbca1ca848b73404a",  # Liang et al. v1.0.0
)
REQUIRED_COMPARISONS = ("toefl-vs-abstracts", "toefl-vs-college")


def _receipt_problems(rec, fp):
    reasons = []
    if rec.get("schema") != F.SCHEMA or rec.get("ruleset_version") != fp:
        reasons.append("receipt schema or ruleset does not match")
    if rec.get("manifest_sha256") not in RELEASE_MANIFESTS:
        reasons.append(f"manifest {rec.get('manifest_sha256')} is not a release manifest")
    missing = set(F.bound_profiles()) - set(rec.get("measured_profiles", []))
    if missing:
        reasons.append(f"receipt omits bound profiles: {sorted(missing)}")
    results = rec.get("results") or {}
    for key, v in results.items():
        if set(v.get("profiles", ())) & set(F.bound_profiles()):
            absent = set(REQUIRED_COMPARISONS) - set(v.get("comparisons", {}))
            if absent:
                reasons.append(f"{key} lacks required comparisons {sorted(absent)}")
    recomputed = F._gate_summary(results, F.bound_profiles())
    stored = rec.get("gates", {})
    if {k: stored.get(k) for k in recomputed} != recomputed:
        reasons.append("the stored gate summary differs from the one its rows give")
    if not recomputed["release_ok"]:
        reasons.append(f"a release gate fails: {recomputed}")
    return reasons


def _override(directory, fp):
    """The recorded reason when a maintainer overrides a failing gate for this
    exact ruleset, else None."""
    path = os.path.join(directory, fp.replace(":", "-") + ".override.json")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        o = json.load(fh)
    ok = o.get("ruleset_version") == fp and str(o.get("reason", "")).strip() \
        and str(o.get("decided_by", "")).strip()
    return f"{o['reason']} (decided by {o['decided_by']})" if ok else None


def release_check(directory):
    """(ok, reasons) for the committed receipt of the current ruleset. The gates
    are recomputed from the receipt's rows; the stored boolean is never trusted."""
    fp = ruleset_fingerprint()
    path = os.path.join(directory, fp.replace(":", "-") + ".json")
    if not os.path.isfile(path):
        return False, [f"no fairness receipt for {fp} at {path}"]
    with open(path, encoding="utf-8") as fh:
        rec = json.load(fh)
    try:
        reasons = _receipt_problems(rec, fp)
    except (KeyError, TypeError, AttributeError) as err:
        reasons = [f"malformed receipt ({type(err).__name__})"]
    if reasons:
        why = _override(directory, fp)
        if why:
            return True, [f"override recorded: {why}"] + reasons
    return not reasons, reasons
