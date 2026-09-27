#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.fairness_release -- the release check on committed fairness receipts.

The gate is scoped to ruleset changes. `fairness/published-ruleset.json` names
the package version, fingerprint and receipts of the last published ruleset. A
commit after each release updates it; the release commit never does.

- When the current fingerprint equals the published one and the record names an
  earlier package version than the one being built, nothing the gates measure
  has changed. The check passes and says the gates were not re-run. A record
  that names the version being built cannot vouch for the release that wrote
  it, so the gates run.
- A changed ruleset needs one receipt DIR/<fingerprint>*.json from every
  manifest in REQUIREMENTS, and no second receipt from the same manifest. Each
  must hold every bound profile and the comparisons listed for its manifest,
  its stored flags must agree with its stored numbers (fairness_verify), and
  every gate recomputed from its own rows must pass. The stored `release_ok` is
  never trusted on its own. When DIR/SHA256SUMS exists, each receipt must match
  its pin there.
- A confirmatory manifest confirms only the ruleset it was pre-registered for
  (CONFIRMATORY). A changed ruleset with no confirmatory receipt fails a gate.
- A maintainer can record an override for one exact ruleset in
  DIR/<fingerprint>.override.json, with a reason and who decided. It excuses
  failing gates only, never a malformed receipt, and only when no gate row
  fails in the new receipt that did not fail in the published ruleset's
  receipt, a row the old receipt lacked included. The comparison base must be a
  sound receipt of the published ruleset itself. The check prints the
  comparison beside the reason.

Standard library only.
"""
from __future__ import annotations

import json
import os
import re

from . import fairness as F
from .fairness_regress import compare, gate_rows
from .fairness_verify import flag_problems, pin_problem, read_pins
from .fingerprint import ruleset_fingerprint

# The manifests a release needs a receipt from, each with the comparisons its
# receipt must hold. fairness/PREREG.md lists the same values, and a test pins
# that they agree.
REQUIREMENTS = {
    # Liang et al. (2023) v1.0.0 build: exploratory, the gates were tuned on it.
    "sha256:71ab34e241bd4315f81d4f0fefcd47eb4538c918b9584cebbca1ca848b73404a":
        ("toefl-vs-abstracts", "toefl-vs-college"),
    # PERSUADE 2.0 training file, fairness/manifests/persuade-2.0.json. It is
    # confirmatory for sha256:46e1485cd2c98caa only (CONFIRMATORY); for any other
    # ruleset its receipt is exploratory, since its outcome is known.
    "sha256:8de8a1e6414e18f03730156ef6c4e8c87dc2f68fe73f0549d42cf4ea0788b4c3":
        ("persuade-ell-vs-non-ell",),
}
RELEASE_MANIFESTS = tuple(REQUIREMENTS)
# Each confirmatory manifest and the one ruleset its pre-registration bound it
# to. fairness/PREREG.md (amendment of 27 September 2026) holds the same map,
# and a test pins that they agree.
CONFIRMATORY = {
    "sha256:8de8a1e6414e18f03730156ef6c4e8c87dc2f68fe73f0549d42cf4ea0788b4c3":
        "sha256:46e1485cd2c98caa",
}
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
            required = REQUIREMENTS.get(rec.get("manifest_sha256"), ())
            absent = set(required) - set(v.get("comparisons", {}))
            if absent:
                reasons.append(f"{key} lacks required comparisons {sorted(absent)}")
    reasons += flag_problems(rec)
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
    found, first, problems, pins = {}, {}, [], read_pins(directory)
    for n in names:
        try:
            rec = _load(os.path.join(directory, n))
        except (OSError, ValueError) as err:
            problems.append(f"{n} cannot be read ({type(err).__name__})")
            continue
        problems += [p for p in (pin_problem(directory, n, pins),) if p]
        man = rec.get("manifest_sha256") if isinstance(rec, dict) else None
        if man in found:
            # Reading only one of two would let a name decide which one counts.
            problems.append(f"two receipts for {fp} from manifest {man}: {first[man]} and {n}")
            continue
        found[man], first[man] = rec, n
    for man in RELEASE_MANIFESTS:
        if man not in found:
            problems.append(f"no fairness receipt for {fp} from release manifest {man}")
    return found, problems


def _published(directory, path):
    """The published-ruleset record, or None when it is absent."""
    path = path or os.path.join(os.path.dirname(os.path.abspath(directory)),
                                "published-ruleset.json")
    return _load(path) if os.path.isfile(path) else None


def _building_version():
    """The package version this check runs for: the one being built."""
    from . import __version__
    return __version__


def _version(v):
    nums = re.findall(r"\d+", str(v or ""))
    return tuple(int(x) for x in nums[:3]) if len(nums) >= 3 else None


def _earlier(published, building):
    """True only when both versions read as X.Y.Z and the published one is lower."""
    a, b = _version(published), _version(building)
    return a is not None and b is not None and a < b


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


def _confirmation(found, fp):
    """A gate failure when no receipt of this ruleset comes from a manifest that
    was pre-registered to confirm it."""
    if any(CONFIRMATORY.get(man) == fp for man in found):
        return []
    bound = ", ".join(f"{m[:19]} confirms {v}" for m, v in sorted(CONFIRMATORY.items()))
    return [f"no confirmatory receipt for {fp} ({bound or 'no confirmatory manifest'}); "
            "a changed ruleset needs a held-out corpus named in a dated PREREG "
            "amendment before its first reading"]


def _base_receipt(directory, pub, man, pins):
    """(receipt, None) for the published ruleset's own receipt from this
    manifest, or (None, reason) when there is no sound one to compare with."""
    olds = []
    for n in pub.get("receipts", ()):
        path = os.path.join(directory, n)
        try:
            r = _load(path) if os.path.isfile(path) else None
        except (OSError, ValueError):
            return None, f"published receipt {n} cannot be read"
        if isinstance(r, dict) and r.get("manifest_sha256") == man:
            olds.append((n, r))
    if not olds:
        return None, f"no published receipt from manifest {man} to compare with"
    if len(olds) > 1:
        return None, f"the published record lists more than one receipt from manifest {man}"
    n, r = olds[0]
    if r.get("schema") != F.SCHEMA or r.get("ruleset_version") != pub.get("ruleset_version"):
        return None, (f"published receipt {n} ran under {r.get('ruleset_version')}, not the "
                      f"published ruleset {pub.get('ruleset_version')}")
    problems = [p for p in (pin_problem(directory, n, pins),) if p] + flag_problems(r)
    if problems:
        return None, f"published receipt {n} cannot serve as a comparison: {problems[0]}"
    return r, None


def _judge_override(directory, pub, found, why, fp):
    """(accepted, lines) for an override: refused without a sound receipt of the
    published ruleset to compare with, or when a gate row fails now that did not
    fail there."""
    if pub is None:
        return False, [f"override refused: {why}; no published ruleset record to "
                       "compare with"]
    if pub.get("ruleset_version") == fp:
        return False, [f"override refused: {why}; the published record names the "
                       "ruleset being released, so there is no earlier ruleset to compare with"]
    pins = read_pins(directory)
    lines, regressed = [], False
    for man, rec in found.items():
        base, problem = _base_receipt(directory, pub, man, pins)
        if problem:
            lines.append(problem)
            regressed = True
            continue
        line, bad = compare(gate_rows(base), gate_rows(rec))
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
    notes = []
    if pub and pub.get("ruleset_version") == fp:
        if _earlier(pub.get("package_version"), _building_version()):
            return True, [f"ruleset unchanged since {pub.get('package_version')} ({fp}); "
                          "gates not re-run"]
        notes.append(f"the published record names {fp} under package "
                     f"{pub.get('package_version')}, not an earlier release than "
                     f"{_building_version()}; a record cannot vouch for the release "
                     "that writes it, so the gates run")
    found, structural, gates = _check_receipts(directory, fp)
    if found:
        gates += _confirmation(found, fp)
    if structural or not gates:
        return not (structural or gates), notes + structural + gates
    why = _override(directory, fp)
    if not why:
        return False, notes + gates
    ok, lines = _judge_override(directory, pub, found, why, fp)
    return ok, notes + lines + gates
