#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.cadence -- sentence-length statistics. Reported only; no cadence
statistic blocks, scores a text or enters an editing target.
Standard library only.
"""
import re
from statistics import mean, pstdev

from .lexicon import OPENER_STOP
from . import markup

# Every constant that decides a cadence flag. The ruleset
# fingerprint folds them in, so changing one moves the fingerprint.
CADENCE_MIN_SENTENCES = 12     # fewer sentences than this: no cadence flag at all
CADENCE_MIN_WORDS = 200        # ... and fewer words than this: no cadence flag at all
CADENCE_CV_MAX = 0.45          # "uniform" needs a coefficient of variation below this
CADENCE_MEAN_MIN = 12          # ... and a mean sentence length at or above this
OPENER_MIN_CONTENT = 12        # content openers needed before opener variety is read
OPENER_RATIO_MAX = 0.6         # "repetitive openers" below this distinct-opener ratio

def cadence_stats(text: str) -> dict:
    sents = markup.split_sentences(text)
    words = [re.findall(r"\b\w+\b", s) for s in sents]
    counts = [len(w) for w in words if w]
    firsts = [w[0].lower() for w in words if w]
    if len(counts) < CADENCE_MIN_SENTENCES or sum(counts) < CADENCE_MIN_WORDS:
        return {"sentences": len(counts), "uniform": False, "repetitive_openers": False}
    mu = mean(counts)
    sd = pstdev(counts)
    cv = sd / mu if mu else 0.0
    # Distinct-opener ratio over CONTENT openers only. Everyone repeats "The",
    # "It", "You" at sentence start, so counting those flags good prose. The
    # pattern is reusing the same content word to open sentence after sentence.
    content = [f for f in firsts if f not in OPENER_STOP]
    opener_ratio = len(set(content)) / len(content) if content else 1.0
    return {
        "sentences": len(counts),
        "mean_len": round(mu, 1),
        "stdev": round(sd, 1),
        "cv": round(cv, 3),
        "opener_ratio": round(opener_ratio, 2),
        # A low coefficient of variation across many sentences: an even,
        # medium-length cadence. Reported only; it never blocks and never
        # enters an editing target.
        "uniform": cv < CADENCE_CV_MAX and mu >= CADENCE_MEAN_MIN,
        "repetitive_openers": (len(content) >= OPENER_MIN_CONTENT
                               and opener_ratio < OPENER_RATIO_MAX),
    }
