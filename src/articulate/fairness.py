#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.fairness -- the standing fairness harness.

Runs the deterministic checker over the documents a manifest lists (see
fairness_corpora), under every profile and mode a writer can land on without
choosing it, and writes a content-free receipt, schema articulate/fairness/v1.
The receipt records block rates by group with intervals in both directions,
per-rule rates and skew states, density distributions, a layout check and the
pre-registered gates G1 to G7 (fairness_gates, fairness/PREREG.md).

  python -m articulate.fairness MANIFEST [--out RECEIPT]
  python -m articulate.fairness --release-check DIR

The release check reads DIR/<fingerprint>.json for the current ruleset and
fails when it is missing, fails a gate, or omits a bound profile. A failure
blocks a ruleset release. It never blocks a user's run.

Standard library only. No network. The harness never stores or prints text.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

from . import density as density_mod
from . import fairness_corpora as corpora
from . import fairness_gates as G
from . import modes, profiles
from .fingerprint import ruleset_fingerprint
from .gate import check_text
from .scan import SCAN_ALGO

SCHEMA = "articulate/fairness/v1"
DOES_NOT_PROVE = (
    "This receipt shows how these rules behave on these corpora. It says nothing "
    "about who or what wrote any text, and nothing about any group trait as a cause "
    "of a difference. It covers only the groups, genres and profiles it lists.")
_SENT = re.compile(r"(?<=[.!?])\s+")


def house_profiles():
    """Profiles a writer or project chooses on purpose. Measured and published,
    never release-gated."""
    return tuple(getattr(profiles, "HOUSE_PROFILES", ()))


def bound_profiles():
    """Every profile a default or a path rule can resolve to, and every mode that
    can gate (F9). House profiles are left out; they are measured separately."""
    names = {profiles.DEFAULT} | {name for _rx, name in profiles.PATH_RULES}
    for mid in modes.names():
        m = modes.load(mid)
        if m["gate_level"] != "off" or m.get("gate_promote"):
            names.add(mid)
    return sorted(n for n in names if n not in house_profiles())


def load_any(name):
    return modes.load(name) if name in modes.MODES else profiles.load(name)


def config_key(prof):
    """The fields the checker reads. Profiles with the same key behave the same."""
    keys = ("gate_level", "keep", "gate_promote", "unit", "structural_classify",
            "dialogue_exempt", "quote_exempt_all", "fiction_slop", "suppress_categories",
            "house")
    return json.dumps({k: prof.get(k) for k in keys}, sort_keys=True, default=list)


def measure(text, prof):
    """Per-document numbers under one profile. No text leaves this function."""
    r = check_text(text, profile=prof)
    rules = {}
    gated = set()
    for t in ("high", "medium", "low"):
        for f in r[t]:
            key = f"{f['tier']}|{f['rule_id']}"
            rules[key] = rules.get(key, 0) + 1
            if f.get("gates"):
                gated.add(key)
    dens = density_mod.density(r)
    words = dens["words"]
    return {"blocked": r["gate"] == "blocked", "words": words, "rules": rules,
            "gated": gated, "density_count": dens["count"],
            "density": dens["count"] / words * 1000 if words else None,
            "uniform": bool(r["cadence"].get("uniform")),
            "hm": {k: v for k, v in rules.items() if not k.startswith("LOW|")}}


def rewrap(text):
    """The same words, one sentence per line."""
    return "\n".join(s.strip() for s in _SENT.split(text.replace("\n", " ")) if s.strip()) + "\n"


def _layout_applies(prof):
    return prof.get("unit", "sentence") != "line" and not prof.get("structural_classify")


def _collect(man, base, configs):
    """measurements[config][set] = [doc measurement], plus layout changes."""
    meas = {k: {} for k in configs}
    layout = {k: 0 for k in configs}
    for row, text in corpora.load_documents(man, base):
        wrapped = rewrap(text)
        for key, prof in configs.items():
            m = measure(text, prof)
            m.update({"key": row.get("key"), "score": row.get("score"),
                      "prompt": row.get("prompt")})
            meas[key].setdefault(row["set"], []).append(m)
            if _layout_applies(prof):
                w = measure(wrapped, prof)
                if (w["hm"], w["density_count"], w["words"]) != (
                        m["hm"], m["density_count"], m["words"]):
                    layout[key] += 1
    return meas, layout


def _for_config(man, sets, names, cadence_gates):
    out = {"profiles": names, "comparisons": {}, "g7": {}, "pairs": {}}
    for c in man.get("comparisons", []):
        prot, ref = sets.get(c["protected"], []), sets.get(c["reference"], [])
        if not prot or not ref:
            continue
        rules = set().union(*(d["gated"] for d in prot + ref))
        out["comparisons"][c["name"]] = {
            "dimension": c.get("dimension"), "design": c["design"],
            "g1": G.g1(prot, ref), "g2": G.g2(prot, ref, rules, c["design"]),
            "g5": G.g5(prot, ref, cadence_gates)}
    human = {s for c in man.get("comparisons", []) for s in (c["protected"], c["reference"])}
    for s in sorted(human):
        if sets.get(s):
            out["g7"][s] = G.g7(sets[s])
    for p in man.get("pairs", []):
        if sets.get(p["a"]) and sets.get(p["b"]):
            out["pairs"][p["name"]] = G.g3(sets[p["a"]], sets[p["b"]])
    return out


def _gate_summary(results, bound):
    def over(fn):
        return all(fn(v) for k, v in results.items() if set(v["profiles"]) & set(bound))
    g1 = over(lambda v: all(c["g1"]["pass"] for c in v["comparisons"].values()))
    g2 = over(lambda v: all(r["pass"] for c in v["comparisons"].values()
                            for r in c["g2"].values()))
    g4 = over(lambda v: v["g4"]["changed"] == 0)
    g5 = over(lambda v: all(c["g5"]["pass"] is not False for c in v["comparisons"].values()))
    g7 = [s for v in results.values() if set(v["profiles"]) & set(bound)
          for s, x in v["g7"].items() if x["review"]]
    return {"G1": g1, "G2": g2, "G3": "report only", "G4": g4, "G5": g5,
            "G6": G.G6_NOT_RUN["state"], "G7_review": sorted(set(g7)),
            "release_ok": g1 and g2 and g4 and g5}


def run(manifest_path, names=None, cadence_gates=False):
    man, man_hash = corpora.load_manifest(manifest_path)
    base = os.path.join(os.path.dirname(os.path.abspath(manifest_path)), man.get("root", "."))
    bound = bound_profiles()
    names = names or (bound + list(house_profiles()))
    configs, members = {}, {}
    for n in names:
        prof = load_any(n)
        key = config_key(prof)
        configs.setdefault(key, prof)
        members.setdefault(key, []).append(n)
    meas, layout = _collect(man, base, configs)
    results = {}
    for i, (key, sets) in enumerate(sorted(meas.items(), key=lambda kv: members[kv[0]])):
        res = _for_config(man, sets, members[key], cadence_gates)
        res["g4"] = {"changed": layout[key], "applies": _layout_applies(configs[key])}
        results[f"config-{i}"] = res
    return {
        "schema": SCHEMA, "ruleset_version": ruleset_fingerprint(), "scan_algo": SCAN_ALGO,
        "manifest_sha256": man_hash, "python": sys.version.split()[0],
        "corpora": man.get("corpora"), "bound_profiles": bound,
        "house_profiles": list(house_profiles()), "measured_profiles": sorted(names),
        "thresholds": G.THRESHOLDS, "bootstrap": {"b": 2000, "seed": G.S.SEED},
        "g6": G.G6_NOT_RUN, "results": results,
        "gates": _gate_summary(results, bound), "does_not_prove": DOES_NOT_PROVE,
    }


def release_check(directory):
    """(ok, reasons) for the committed receipt of the current ruleset."""
    fp = ruleset_fingerprint()
    path = os.path.join(directory, fp.replace(":", "-") + ".json")
    if not os.path.isfile(path):
        return False, [f"no fairness receipt for {fp} at {path}"]
    with open(path, encoding="utf-8") as fh:
        rec = json.load(fh)
    reasons = []
    if rec.get("schema") != SCHEMA or rec.get("ruleset_version") != fp:
        reasons.append("receipt schema or ruleset does not match")
    missing = set(bound_profiles()) - set(rec.get("measured_profiles", []))
    if missing:
        reasons.append(f"receipt omits bound profiles: {sorted(missing)}")
    if not rec.get("gates", {}).get("release_ok"):
        reasons.append(f"a release gate fails: {rec.get('gates')}")
    return not reasons, reasons


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m articulate.fairness",
                                 description="Measure the checker on labeled corpora.")
    ap.add_argument("manifest", nargs="?")
    ap.add_argument("--out", default=None, help="write the receipt here")
    ap.add_argument("--release-check", metavar="DIR", default=None)
    args = ap.parse_args(argv)
    if args.release_check:
        ok, reasons = release_check(args.release_check)
        print("[fairness] release check " + ("passed" if ok else "failed: " + "; ".join(reasons)))
        return 0 if ok else 1
    if not args.manifest:
        ap.print_help()
        return 2
    try:
        rec = run(args.manifest)
    except corpora.CorpusError as e:
        print(f"[fairness] {e}", file=sys.stderr)
        return 2
    blob = json.dumps(rec, indent=1, sort_keys=True, default=list)
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(blob + "\n")
    print(f"[fairness] {rec['ruleset_version']}: gates {json.dumps(rec['gates'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
