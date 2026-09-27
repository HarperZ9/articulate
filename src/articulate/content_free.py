#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.content_free -- rule ids that carry no word of the text.

Two notes put words from the text into their rule id: the repeated-phrase note
(`ngram-repetition`) names the phrase and the repeated-opener note (`anaphora`)
names the opener. A project terminology rule (`terminology/banned/<term>`) names
its term, and a finding means the text holds that term. A domain rule pack's
label can quote the matched words or give their counts (`bcp14-mixed-case`,
`plain-long-sentence`), and a rule id is built from its label. Every
content-free output keys all of those by category: `check --content-free`, a
`--redact drop` or `--redact hash` receipt, and a fairness receipt. Every other
rule id is fixed text from the rule tables.

Standard library only.
"""
from __future__ import annotations

from functools import lru_cache

TEXT_LABELS = frozenset({"ngram-repetition", "anaphora"})
# Categories whose rule id names a term from a project's own list.
PROJECT_LABELS = frozenset({"terminology"})


@lru_cache(maxsize=1)
def pack_labels():
    """Every domain rule-pack category (articulate.rules_ext)."""
    from . import rules_ext
    return frozenset(rules_ext.categories()) - PROJECT_LABELS


def keyed(category):
    """True when a content-free output keys this category by category."""
    return category in TEXT_LABELS or category in PROJECT_LABELS or category in pack_labels()


def rule_id(f):
    """A finding's rule id, or its category when the rule id can carry the text."""
    return f["category"] if keyed(f["category"]) else f["rule_id"]


def counts(findings):
    """Per-rule counts keyed by content-free rule id, in sorted order."""
    out = {}
    for f in findings:
        key = rule_id(f)
        out[key] = out.get(key, 0) + 1
    return dict(sorted(out.items()))
