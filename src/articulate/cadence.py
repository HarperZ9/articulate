#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.cadence -- sentence-length statistics and the texture score.
Standard library only.
"""
import re
from statistics import mean, pstdev

from .lexicon import OPENER_STOP
from .markup import split_sentences


def texture_score(n_hard, n_soft, doc, words):
    """A graded 0-100 estimate of machine texture, accumulating weak evidence.
    Separate from the clean/flagged device gate: this never changes "clean",
    it is an extra detection signal for benchmarking and for a graded read.
    Regex cannot see token probability, so device-clean AI can still score low;
    that is an honest ceiling, not a bug."""
    if words < 30:
        return 0, False
    per = 100.0 / words
    score = (n_hard * per) * 8.0 + (n_soft * per) * 4.5
    if doc.get("uniform"):
        score += 10
    if doc.get("repetitive_openers"):
        score += 10
    # Orwell/Williams structural excess, above a threshold so ordinary prose
    # (which carries some adverbs and some passive) is not penalized.
    score += max(0.0, doc.get("adverb_rate", 0) - 4.0) * 1.2
    score += max(0.0, doc.get("passive_rate", 0) - 3.0) * 1.5
    score = int(min(100, round(score)))
    return score, score >= 30


def cadence_stats(text: str) -> dict:
    sents = split_sentences(text)
    words = [re.findall(r"\b\w+\b", s) for s in sents]
    counts = [len(w) for w in words if w]
    firsts = [w[0].lower() for w in words if w]
    if len(counts) < 8:
        return {"sentences": len(counts), "uniform": False, "repetitive_openers": False}
    mu = mean(counts)
    sd = pstdev(counts)
    cv = sd / mu if mu else 0.0
    # Distinct-opener ratio over CONTENT openers only. Everyone repeats "The",
    # "It", "You" at sentence start, so counting those flags good prose. The real
    # tell is reusing the same content word to open sentence after sentence.
    content = [f for f in firsts if f not in OPENER_STOP]
    opener_ratio = len(set(content)) / len(content) if content else 1.0
    return {
        "sentences": len(counts),
        "mean_len": round(mu, 1),
        "stdev": round(sd, 1),
        "cv": round(cv, 3),
        "opener_ratio": round(opener_ratio, 2),
        # A low coefficient of variation across many sentences reads as the
        # even, medium-length cadence typical of unedited model prose.
        "uniform": cv < 0.45 and mu >= 12,
        "repetitive_openers": len(content) >= 12 and opener_ratio < 0.6,
    }
