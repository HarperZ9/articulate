#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
articulate.bench -- an expected-findings regression over the shipped corpus.

Two checks, both about the rules and neither about who wrote a text:

  patterns  Each text in corpus/patterns/ must still raise every category that
            corpus/patterns/expect.json lists for it, under the profile listed
            there. A rule change that silently stops matching fails here.
  control   Each text in corpus/control/ must raise no blocking finding under
            every profile expect.json lists for the control set. These are
            public texts a reader would call plain; a rule change that starts
            blocking one of them fails here.

This benchmark sets no target on text from any source. It measures nothing about
fairness; the fairness harness (python -m articulate.fairness) does that on
labeled corpora.

Usage: python -m articulate.bench [corpus_dir]
Exit code is the number of failures (0 = every expectation held), for CI use.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CORPUS = os.path.normpath(os.path.join(HERE, "..", "..", "corpus"))


def _check(path, profile_name):
    from . import detector, profiles
    with open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    return detector.check_text(text, profile=profiles.load(profile_name))


def _categories(r):
    return {f["category"] for t in ("high", "medium", "low") for f in r[t]}


def run(corpus):
    """(rows, failures). Each row: (set, file, profile, ok, note)."""
    with open(os.path.join(corpus, "patterns", "expect.json"), encoding="utf-8") as fh:
        expect = json.load(fh)
    rows = []
    for name, spec in sorted(expect["patterns"].items()):
        r = _check(os.path.join(corpus, "patterns", name), spec["profile"])
        missing = sorted(set(spec["categories"]) - _categories(r))
        rows.append(("patterns", name, spec["profile"], not missing,
                     f"missing {missing}" if missing else f"{len(spec['categories'])} expected"))
    ctrl = os.path.join(corpus, "control")
    for name in sorted(os.listdir(ctrl)):
        if not name.endswith((".txt", ".md")):
            continue
        for prof in expect["control"]["profiles"]:
            r = _check(os.path.join(ctrl, name), prof)
            blocking = sorted({f["rule_id"] for t in ("high", "medium", "low")
                               for f in r[t] if f["gates"]})
            rows.append(("control", name, prof, not blocking,
                         f"blocks on {blocking}" if blocking else "no blocking finding"))
    return rows, sum(1 for row in rows if not row[3])


def main(argv):
    corpus = argv[0] if argv else DEFAULT_CORPUS
    rows, failures = run(corpus)
    print(f"[bench] corpus: {corpus}")
    for kind, name, prof, ok, note in rows:
        print(f"  {'ok  ' if ok else 'FAIL'} {kind:<8} {prof:<11} {name}: {note}")
    print(f"[bench] {len(rows)} expectation(s), {failures} failure(s)")
    return failures


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
