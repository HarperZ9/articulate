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

The release check reads DIR/<fingerprint>.json for the current ruleset. It
fails when the receipt is missing, was run on a manifest not listed in
RELEASE_MANIFESTS, leaves out a required comparison or a bound profile, or when
the gates recomputed from its own rows fail or disagree with the stored
summary. A failure blocks every package release, since each release ships the
ruleset. It never blocks a user's run. A maintainer can record an override in
DIR/<fingerprint>.override.json with a stated reason; the check then passes and
prints that reason.

Standard library only. No network. The harness never stores or prints text.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import textwrap

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
    r = check_text(text, profile=prof, house_notes=True, cadence_detail=True)
    rules = {}
    gated, house = set(), set()
    for t in ("high", "medium", "low"):
        for f in r[t]:
            key = f"{f['tier']}|{f['rule_id']}"
            rules[key] = rules.get(key, 0) + 1
            if f.get("gates"):
                gated.add(key)
            if f.get("house"):
                house.add(key)
    dens = density_mod.density(r)
    words = dens["words"]
    return {"blocked": r["gate"] == "blocked", "words": words, "rules": rules,
            "gated": gated, "house_rules": house, "density_count": dens["count"],
            "density": dens["count"] / words * 1000 if words else None,
            "uniform": bool(r["cadence"].get("uniform")),
            "hm": {k: v for k, v in rules.items() if not k.startswith("LOW|")}}


def rewrap(text):
    """The same words, one sentence per line."""
    return "\n".join(s.strip() for s in _SENT.split(text.replace("\n", " ")) if s.strip()) + "\n"


def hardwrap(text, width=60):
    """The same words hard-wrapped at `width` columns, breaking at hyphens too."""
    paras = [p.replace("\n", " ") for p in re.split(r"\n\s*\n", text) if p.strip()]
    return "\n\n".join(textwrap.fill(p, width, break_long_words=False) for p in paras) + "\n"


def _layout_changed(text, m, prof):
    for variant in (rewrap(text), hardwrap(text)):
        w = measure(variant, prof)
        if (w["hm"], w["density_count"], w["words"]) != (m["hm"], m["density_count"],
                                                        m["words"]):
            return True
    return False


def _layout_applies(prof):
    return prof.get("unit", "sentence") != "line" and not prof.get("structural_classify")


def _collect(man, base, configs):
    """measurements[config][set] = [doc measurement], plus layout changes."""
    meas = {k: {} for k in configs}
    layout = {k: 0 for k in configs}
    for row, text in corpora.load_documents(man, base):
        for key, prof in configs.items():
            m = measure(text, prof)
            m.update({"key": row.get("key"), "score": row.get("score"),
                      "prompt": row.get("prompt")})
            meas[key].setdefault(row["set"], []).append(m)
            if _layout_applies(prof) and _layout_changed(text, m, prof):
                layout[key] += 1
    return meas, layout


def _for_config(man, sets, names, cadence_gates, notes=False):
    out = {"profiles": names, "comparisons": {}, "skipped": [], "g7": {}, "pairs": {}}
    for c in man.get("comparisons", []):
        prot, ref = sets.get(c["protected"], []), sets.get(c["reference"], [])
        if not prot or not ref:
            # A comparison with an empty arm is a failure, never a silent pass.
            out["skipped"].append(c["name"])
            continue
        rules = set().union(*(d["gated"] for d in prot + ref))
        row = {"dimension": c.get("dimension"), "design": c["design"],
               "g1": G.g1(prot, ref), "g2": G.g2(prot, ref, rules, c["design"]),
               "g5": G.g5(prot, ref, cadence_gates)}
        if notes:
            row["g8"] = G.g8(prot, ref)
        out["comparisons"][c["name"]] = row
    human = {s for c in man.get("comparisons", []) for s in (c["protected"], c["reference"])}
    for s in sorted(human):
        if sets.get(s):
            out["g7"][s] = G.g7(sets[s])
    for p in man.get("pairs", []):
        if sets.get(p["a"]) and sets.get(p["b"]):
            out["pairs"][p["name"]] = G.g3(sets[p["a"]], sets[p["b"]])
    return out


def _evaluated(v):
    """A bound config must evaluate at least one comparison and skip none."""
    return bool(v["comparisons"]) and not v.get("skipped")


def _gate_summary(results, bound):
    rows = [v for v in results.values() if set(v["profiles"]) & set(bound)]

    def over(fn):
        return bool(rows) and all(fn(v) for v in rows)
    g1 = over(lambda v: _evaluated(v) and all(c["g1"]["pass"]
                                              for c in v["comparisons"].values()))
    g2 = over(lambda v: _evaluated(v) and all(r["pass"] for c in v["comparisons"].values()
                                              for r in c["g2"].values()))
    g4 = over(lambda v: v["g4"]["changed"] == 0)
    g5 = over(lambda v: all(c["g5"]["pass"] is not False for c in v["comparisons"].values()))
    g7 = [s for v in results.values() if set(v["profiles"]) & set(bound)
          for s, x in v["g7"].items() if x["review"]]
    return {"G1": g1, "G2": g2, "G3": "report only", "G4": g4, "G5": g5,
            "G6": G.G6_NOT_RUN["state"], "G7_review": sorted(set(g7)),
            "G8": "report only", "release_ok": g1 and g2 and g4 and g5}


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
        notes = bool({profiles.DEFAULT, *house_profiles()} & set(members[key]))
        res = _for_config(man, sets, members[key], cadence_gates, notes)
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
    """(ok, reasons) for the committed receipt of the current ruleset. See
    fairness_release."""
    from .fairness_release import release_check as check
    return check(directory)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m articulate.fairness",
                                 description="Measure the checker on labeled corpora.")
    ap.add_argument("manifest", nargs="?")
    ap.add_argument("--out", default=None, help="write the receipt here")
    ap.add_argument("--release-check", metavar="DIR", default=None)
    args = ap.parse_args(argv)
    if args.release_check:
        ok, reasons = release_check(args.release_check)
        print("[fairness] release check " + ("passed" if ok else "failed")
              + (": " + "; ".join(reasons) if reasons else ""))
        return 0 if ok else 1
    if not args.manifest:
        ap.print_help()
        return 2
    try:
        rec = run(args.manifest)
    except (corpora.CorpusError, OSError, ValueError) as e:
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
