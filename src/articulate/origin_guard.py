#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.origin_guard -- keep the editor's own commentary free of guesses
about who or what wrote a text.

The judge and the quality scorer ask a hosted model for commentary. The prompt
tells it to say nothing about a text's origin, and a prompt cannot guarantee
that. This module removes, from the model's commentary only, each line that
makes such a guess, and says how many it removed. Quoted material (the model
quoting the document) is ignored when a line is tested, so a document that
discusses these topics keeps its quotes. A rewrite of the writer's own text is
never filtered: it is the writer's content.

A pattern list misses paraphrase; this narrows the risk and does not remove it.
Standard library only.
"""
from __future__ import annotations

import re

_QUOTED = re.compile(r"\"[^\"\n]*\"|“[^”\n]*”|'[^'\n]{3,}'")
_SUBJECT = r"(?:an?\s+)?(?:ai|a\.i\.|machine|(?:large\s+)?language\s+model|llm|chat\s*gpt|gpt|bot|chatbot)"
ORIGIN_GUESS = re.compile(
    r"(?i)\b(?:ai|machine|model|llm|bot)[- ](?:generated|written|authored|produced)\b"
    r"|\b(?:written|generated|produced|authored|drafted)\s+(?:by|with)\s+" + _SUBJECT + r"\b"
    r"|\b(?:reads?|sounds?|feels?|looks?|seems?)\s+(?:like|as\s+if|as\s+though)\s+"
    r"(?:it\s+(?:was|were)\s+)?(?:written|generated|produced)\s+by\b"
    r"|\b(?:reads?|sounds?|feels?|looks?|seems?)\s+(?:like\s+)?" + _SUBJECT + r"\b"
    r"|\b(?:human|person)[- ](?:written|authored)\b|\bnot\s+(?:written\s+by\s+)?a\s+human\b"
    r"|\b(?:ai|machine)[- ]?(?:detector|detection)\b|\bhallmarks?\s+of\s+" + _SUBJECT)


def strip_origin_guesses(text):
    """(text, removed): the commentary with every line that guesses at the
    text's origin removed, and how many lines went."""
    kept, removed = [], 0
    for line in (text or "").splitlines(keepends=True):
        if ORIGIN_GUESS.search(_QUOTED.sub(" ", line)):
            removed += 1
            continue
        kept.append(line)
    return "".join(kept), removed


def note(removed):
    """The line printed when commentary was removed, or an empty string."""
    if not removed:
        return ""
    return (f"[articulate] removed {removed} line(s) of editor commentary that guessed at "
            "who or what wrote the text; that is not a question the editor answers.")


def clean_notes(notes):
    """A list of short model notes with origin guesses dropped."""
    return [n for n in (notes or []) if not ORIGIN_GUESS.search(_QUOTED.sub(" ", str(n)))]
