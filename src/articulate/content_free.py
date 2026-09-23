#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.content_free -- rule ids that carry no word of the text.

Two notes put words from the text into their rule id: the repeated-phrase note
(`ngram-repetition`) names the phrase and the repeated-opener note (`anaphora`)
names the opener. A project terminology rule (`terminology/banned/<term>`) names
its term, and a finding means the text holds that term. Every content-free
output keys those by category: `check --content-free`, and a `--redact drop` or
`--redact hash` receipt. A fairness receipt keys the two notes the same way; no
fairness run reads a project config. Every other rule id is fixed text from the
rule tables.

Standard library only.
"""
from __future__ import annotations

TEXT_LABELS = frozenset({"ngram-repetition", "anaphora"})
# Categories whose rule id names a term from a project's own list.
PROJECT_LABELS = frozenset({"terminology"})


def rule_id(f):
    """A finding's rule id, or its category when the rule id quotes the text."""
    keyed = f["category"] in TEXT_LABELS or f["category"] in PROJECT_LABELS
    return f["category"] if keyed else f["rule_id"]


def counts(findings):
    """Per-rule counts keyed by content-free rule id, in sorted order."""
    out = {}
    for f in findings:
        key = rule_id(f)
        out[key] = out.get(key, 0) + 1
    return dict(sorted(out.items()))
