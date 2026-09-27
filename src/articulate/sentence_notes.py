#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.sentence_notes -- the rules that read one sentence at a time.

A sentence is the unit here, so a wrap cannot split or merge a finding. Every
rule reads the sentence with quotations blanked (articulate.quoting); the
citation anchors of `unsupported-authority` read the raw sentence at the same
offsets.

Standard library only.
"""
from .citations import CITATION_MARKER, unanchored_appeals
from .citations import LABEL as AUTHORITY_LABEL
from .lexicon import (ANNOUNCEMENT, CLAIM_ANCHOR, DIGIT, EXISTENTIAL, EXPLETIVE, NOMINAL,
                      OPERATOR_AFTER, OPERATOR_BEFORE, PADDED_PREPOSITION, PADDED_PURPOSE,
                      UNANCHORED_CLAIM, VAGUE_QUANT)
from .logical import sentences

# Sentence-start openers. The first is a default LOW note; the second is a house
# note (rule_reasons.HOUSE_CATEGORIES). Neither blocks. A pattern with a group
# reports the group's span.
OPENERS = (
    ("expletive-opener", "empty opener (it is important / worth)", EXPLETIVE),
    ("existential-opener", "existential opener (there is / there are)", EXISTENTIAL),
)
# LOW notes on phrases that usage guides accept in some uses. None blocks.
PHRASE_NOTES = (
    ("padded-purpose", "padded purpose (in order to)", PADDED_PURPOSE),
    ("announcement", "announces what the text will do (in this essay, we will explore)",
     ANNOUNCEMENT),
)


def _marker_after(raw, e):
    """True when a citation marker sits right after the sentence's closing
    period, as a Chicago note or a LaTeX cite often does (SCAN_ALGO 7)."""
    i = e + 1 if raw.startswith("~", e) else e
    return CITATION_MARKER.match(raw, i) is not None


def sentence_passes(sc, unit, text, raw):
    """Run the per-sentence rules over `text` (masked) with `raw` beside it."""
    for s, e in sentences(text):
        sent = text[s:e]
        after = _marker_after(raw, e)
        if not DIGIT.search(sent):
            for mq in VAGUE_QUANT.finditer(sent):
                sc.add(sc.low, unit, "vague-quantifier", "vague quantifier, no number given",
                       s + mq.start(), s + mq.end(), text=text)
        _openers(sc, unit, s, sent)
        _phrase_notes(sc, unit, text, s, sent, raw[s:e], after)
        for a, b in ([] if after else unanchored_appeals(sent, raw[s:e])):
            sc.add(sc.medium, unit, "unsupported-authority", AUTHORITY_LABEL,
                   s + a, s + b, text=text)
        noms = list(NOMINAL.finditer(sent))
        if len(noms) >= 4:
            sc.add(sc.low, unit, "nominalization", f"{len(noms)} nominalizations in one sentence",
                   s + noms[0].start(), s + noms[0].end(), True)


def _openers(sc, unit, s, sent):
    lead = len(sent) - len(sent.lstrip())
    for cat, label, rx in OPENERS:
        m = rx.match(sent.lstrip())
        if m:
            a, b = m.span(1) if rx.groups else m.span()
            sc.add(sc.low, unit, cat, label, s + lead + a, s + lead + b, True)


def _phrase_notes(sc, unit, text, s, sent, raw_sent, marker_after):
    """"in order to", an announcement, "with respect to" outside its operator
    sense, and "state of the art" in a sentence with no number, year or
    citation. The anchors are read on the raw sentence, since the masks blank a
    URL and a LaTeX cite, and a marker right after the period counts."""
    for cat, label, rx in PHRASE_NOTES:
        for m in rx.finditer(sent):
            sc.add(sc.low, unit, cat, label, s + m.start(), s + m.end(), text=text)
    for m in PADDED_PREPOSITION.finditer(sent):
        # The word before is read from a short tail, so a long run stays linear.
        before = sent[max(0, m.start() - 40):m.start()]
        if OPERATOR_BEFORE.search(before) or OPERATOR_AFTER.match(sent, m.end()):
            continue
        sc.add(sc.low, unit, "padded-preposition", "padded preposition (with respect to)",
               s + m.start(), s + m.end(), text=text)
    anchored = (marker_after or CLAIM_ANCHOR.search(raw_sent)
                or CITATION_MARKER.search(raw_sent))
    if not anchored:
        for m in UNANCHORED_CLAIM.finditer(sent):
            sc.add(sc.low, unit, "unanchored-claim",
                   "unanchored claim (state of the art, no comparison named)",
                   s + m.start(), s + m.end(), text=text)
