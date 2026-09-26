#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.fairness_release -- the release check on committed fairness receipts.

The gate is scoped to ruleset changes. `fairness/published-ruleset.json` names
the fingerprint of the last published ruleset and its receipts; the release
commit updates it.

- When the current fingerprint equals the published one, nothing the gates
  measure has changed. The check passes and says the gates were not re-run.
- A changed ruleset needs a receipt DIR/<fingerprint>*.json from every manifest
  in RELEASE_MANIFESTS. Each must hold every bound profile and required
  comparison, and every gate recomputed from its own rows must pass. The stored
  `release_ok` is never trusted on its own.
- A maintainer can record an override for one exact ruleset in
  DIR/<fingerprint>.override.json, with a reason and who decided. It excuses
  failing gates only, never a malformed receipt, and only when no gate row that
  passes in the published ruleset's receipt fails in the new one. The check
  prints that comparison beside the reason.

Standard library only.
"""
from __future__ import annotations

import json
import os

from . import fairness as F
from .fairness_regress import compare, gate_rows
from .fingerprint import ruleset_fingerprint

# The manifests a release receipt may come from, and the comparisons it must
# hold. fairness/PREREG.md lists the same values, and a test pins that they agree.
RELEASE_MANIFESTS = (
    "sha256:71ab34e241bd4315f81d4f0fefcd47eb4538c918b9584cebbca1ca848b73404a",  # Liang et al. v1.0.0
)
REQUIRED_COMPARISONS = ("toefl-vs-abstracts", "toefl-vs-college")
GATE_FAILS = "a release gate fails"


def _receipt_problems(rec, fp):
    """(structural problems, gate failures) for one receipt."""
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
    gates = [] if recomputed["release_ok"] else [f"{GATE_FAILS}: {recomputed}"]
    return reasons, gates


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _receipts(directory, fp):
    """{manifest: receipt} for the receipts of this ruleset, plus problems."""
    stem = fp.replace(":", "-")
    names = sorted(n for n in os.listdir(directory) if n.startswith(stem)
                   and n.endswith(".json") and not n.endswith(".override.json")) \
        if os.path.isdir(directory) else []
    if not names:
        return {}, [f"no fairness receipt for {fp} at {os.path.join(directory, stem + '.json')}"]
    found, problems = {}, []
    for n in names:
        rec = _load(os.path.join(directory, n))
        man = rec.get("manifest_sha256") if isinstance(rec, dict) else None
        found.setdefault(man, rec)
    for man in RELEASE_MANIFESTS:
        if man not in found:
            problems.append(f"no fairness receipt for {fp} from release manifest {man}")
    return found, problems


def _published(directory, path):
    """The published-ruleset record, or None when it is absent."""
    path = path or os.path.join(os.path.dirname(os.path.abspath(directory)),
                                "published-ruleset.json")
    return _load(path) if os.path.isfile(path) else None


def _override(directory, fp):
    """The recorded reason when a maintainer overrides a failing gate for this
    exact ruleset, else None."""
    path = os.path.join(directory, fp.replace(":", "-") + ".override.json")
    if not os.path.isfile(path):
        return None
    o = _load(path)
    ok = o.get("ruleset_version") == fp and str(o.get("reason", "")).strip() \
        and str(o.get("decided_by", "")).strip()
    return f"{o['reason']} (decided by {o['decided_by']})" if ok else None


def _check_receipts(directory, fp):
    """(receipts by manifest, structural problems, gate failures)."""
    found, structural = _receipts(directory, fp)
    gates = []
    for man, rec in found.items():
        try:
            s, g = _receipt_problems(rec, fp)
        except (KeyError, TypeError, AttributeError) as err:
            s, g = [f"malformed receipt ({type(err).__name__})"], []
        structural += s
        gates += g
    return found, structural, gates


def _judge_override(directory, pub, found, why):
    """(accepted, lines) for an override: refused without a published receipt to
    compare with, or when a gate row that passed there fails now."""
    if pub is None:
        return False, [f"override refused: {why}; no published ruleset record to "
                       "compare with"]
    lines, regressed = [], False
    for man, rec in found.items():
        old = [r for r in (_load(os.path.join(directory, n)) for n in pub.get("receipts", ())
                           if os.path.isfile(os.path.join(directory, n)))
               if r.get("manifest_sha256") == man]
        if not old:
            lines.append(f"no published receipt from manifest {man} to compare with")
            regressed = True
            continue
        line, bad = compare(gate_rows(old[0]), gate_rows(rec))
        lines.append(f"comparison with the published ruleset {pub.get('package_version')} "
                     f"({pub.get('ruleset_version')}) on manifest {man[:19]}: {line}")
        regressed = regressed or bool(bad)
    head = "override refused" if regressed else "override recorded"
    return not regressed, [f"{head}: {why}"] + lines


def release_check(directory, published=None):
    """(ok, lines) for the current ruleset. `published` is the path of the
    published-ruleset record; by default it sits beside DIR."""
    fp = ruleset_fingerprint()
    pub = _published(directory, published)
    if pub and pub.get("ruleset_version") == fp:
        return True, [f"ruleset unchanged since {pub.get('package_version')} ({fp}); "
                      "gates not re-run"]
    found, structural, gates = _check_receipts(directory, fp)
    if structural or not gates:
        return not (structural or gates), structural + gates
    why = _override(directory, fp)
    if not why:
        return False, gates
    ok, lines = _judge_override(directory, pub, found, why)
    return ok, lines + gates
