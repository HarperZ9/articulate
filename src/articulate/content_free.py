#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.content_free -- rule ids that carry no word of the text.

Two notes put words from the text into their rule id: the repeated-phrase note
(`ngram-repetition`) names the phrase and the repeated-opener note (`anaphora`)
names the opener. Every content-free output keys those two by category:
`check --content-free`, a `--redact drop` or `--redact hash` receipt, and a
fairness receipt. Every other rule id is fixed text from the rule tables.

Standard library only.
"""
from __future__ import annotations

TEXT_LABELS = frozenset({"ngram-repetition", "anaphora"})


def rule_id(f):
    """A finding's rule id, or its category when the rule id quotes the text."""
    return f["category"] if f["category"] in TEXT_LABELS else f["rule_id"]


def counts(findings):
    """Per-rule counts keyed by content-free rule id, in sorted order."""
    out = {}
    for f in findings:
        key = rule_id(f)
        out[key] = out.get(key, 0) + 1
    return dict(sorted(out.items()))
