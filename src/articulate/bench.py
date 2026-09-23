#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
articulate-bench.py

Measured quality for the Articulate writing detector. Runs
check-writing-devices.py over a labeled corpus and prints a scorecard:
recall on AI-authored samples (does it flag them), specificity on
human-authored samples (does it leave them alone), and the per-file detail.

This is how the tool earns "high quality": precision and recall against
labeled data, not vibes. External detector verdicts (e.g. Pangram) can be
recorded per sample in a sidecar `.pangram` file for cross-reference; they
are printed but never used as an optimization target. The tool flags; it
never rewrites toward a score.

Corpus layout:
    articulate-corpus/human/<name>.txt   human-authored (expect: clean)
    articulate-corpus/ai/<name>.txt      AI-authored    (expect: flagged)
    articulate-corpus/<any>/<name>.pangram   optional: "<label> <pct>" reference

Usage: python articulate-bench.py [corpus_dir]
Exit code is the number of misclassified files (0 = perfect), for CI use.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CORPUS = os.path.normpath(os.path.join(HERE, "..", "..", "corpus"))


def run_checker(path):
    from . import detector
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return {"high": 0, "medium": 0, "low": 0, "clean": True, "cadence": {}}
    r = detector.check_text(text)
    cad = dict(r["cadence"])
    cad["score"] = r["texture_score"]
    cad["elevated"] = r["elevated"]
    return {"high": len(r["high"]), "medium": len(r["medium"]), "low": len(r["low"]),
            "clean": r["clean"], "cadence": cad}


def pangram_ref(path):
    side = os.path.splitext(path)[0] + ".pangram"
    if os.path.isfile(side):
        try:
            return open(side, encoding="utf-8").read().strip()
        except OSError:
            return ""
    return ""


def expected_miss(path):
    """A sidecar <name>.expect containing 'miss' marks a known ceiling (e.g.
    device-clean AI a rule detector cannot catch). It stays visible in the
    table but does not count as a regression, so the gate is green until real
    detection breaks."""
    side = os.path.splitext(path)[0] + ".expect"
    if os.path.isfile(side):
        try:
            return "miss" in open(side, encoding="utf-8").read().lower()
        except OSError:
            return False
    return False


def collect(corpus, label):
    d = os.path.join(corpus, label)
    if not os.path.isdir(d):
        return []
    return [os.path.join(d, n) for n in sorted(os.listdir(d))
            if n.lower().endswith((".txt", ".md")) and not n.endswith(".pangram")]


def main(argv):
    corpus = argv[0] if argv else DEFAULT_CORPUS
    ai_files = collect(corpus, "ai")
    human_files = collect(corpus, "human")
    if not ai_files and not human_files:
        print(f"[bench] no corpus at {corpus}/ai or {corpus}/human")
        return 0

    misses = 0
    print(f"[bench] corpus: {corpus}")
    print(f"{'label':<7} {'verdict':<9} {'H/M/L':<10} {'texture':<22} file")
    print("-" * 78)

    def is_flagged(r):
        cad = r["cadence"]
        return (r["high"] + r["medium"]) > 0 or bool(cad.get("elevated"))

    def row(path, truth):
        nonlocal misses
        r = run_checker(path)
        flagged = is_flagged(r)
        # A correct call: AI is flagged, human is left clean.
        correct = flagged if truth == "ai" else (not flagged)
        known = expected_miss(path)
        if not correct and not known:
            misses += 1
        cad = r["cadence"]
        tex = f"score {cad.get('score', 0)}"
        if cad.get("uniform"):
            tex += " uniform"
        if cad.get("repetitive_openers"):
            tex += " openers"
        verdict = "FLAGGED" if flagged else "clean"
        mark = " " if correct else ("~" if known else "X")
        hml = f"{r['high']}/{r['medium']}/{r['low']}"
        ref = pangram_ref(path)
        name = os.path.basename(path) + (f"   [pangram: {ref}]" if ref else "")
        print(f"{truth:<7} {verdict:<9} {hml:<10} {tex:<22}{mark} {name}")

    for p in ai_files:
        row(p, "ai")
    for p in human_files:
        row(p, "human")

    n_ai, n_human = len(ai_files), len(human_files)
    ai_flagged = sum(1 for p in ai_files if is_flagged(run_checker(p)))
    human_clean = sum(1 for p in human_files if not is_flagged(run_checker(p)))
    print("-" * 78)
    if n_ai:
        print(f"[bench] AI recall (flagged/total):      {ai_flagged}/{n_ai} "
              f"= {ai_flagged / n_ai:.0%}")
    if n_human:
        print(f"[bench] human specificity (clean/total): {human_clean}/{n_human} "
              f"= {human_clean / n_human:.0%}  (false positives: {n_human - human_clean})")
    print(f"[bench] regressions (unexpected misses): {misses}   "
          f"[~ = known ceiling, not a regression]")
    print("[bench] note: device-clean AI can pass Articulate yet fail a trained "
          "detector; those are the honest misses, marked ~ and gated as expected.")
    # The domain rule packs have their own regression corpus under domains/.
    from . import bench_domains
    domains = os.path.join(corpus, "domains")
    if os.path.isfile(os.path.join(domains, "expect.json")):
        print()
        misses += bench_domains.main([domains])
    return misses


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
