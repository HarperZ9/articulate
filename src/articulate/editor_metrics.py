#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.editor_metrics -- what a rewrite did to vocabulary and rhythm.

Perplexity detectors read plain vocabulary and even sentence lengths as signs of
a model, and the documented way to lower their score is fancier words and more
varied sentences. An editor that drifted that way would be an evasion tool,
whatever its prompts say. These measures let the fairness harness check (gate
G6) that accepted rewrites do not raise either on average, by group.

They are measurements for the evaluation harness. They are never an editing
target, never enter an accept decision and never appear in a receipt.
Standard library only.
"""
from __future__ import annotations

import re
from statistics import mean, pstdev

TOKEN = re.compile(r"[a-z']+")
SENT = re.compile(r"(?<=[.!?])\s+")
WORD = re.compile(r"\b\w+\b")


def vocabulary(text):
    """(mean letters per word, share of words with 7 or more letters)."""
    letters = [len(t.replace("'", "")) for t in TOKEN.findall(text.lower())]
    if not letters:
        return 0.0, 0.0
    return mean(letters), sum(1 for n in letters if n >= 7) / len(letters)


def sentence_length_sd(text):
    counts = [len(WORD.findall(s)) for s in SENT.split(text.replace("\n", " ")) if s.strip()]
    return pstdev(counts) if len(counts) > 1 else 0.0


def rewrite_delta(before, after):
    """How a rewrite moved the three measures. Positive means the rewrite raised it."""
    wl0, long0 = vocabulary(before)
    wl1, long1 = vocabulary(after)
    return {"mean_word_length": round(wl1 - wl0, 4),
            "long_word_share": round(long1 - long0, 4),
            "sentence_length_sd": round(sentence_length_sd(after) - sentence_length_sd(before), 4)}
