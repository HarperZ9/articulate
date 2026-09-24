#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
articulate.lexical -- the word-level invariants: modal strength, scope words,
negations, and named entities.

`tokens(masked, freeze_keys)` reads them from a text whose containers (code,
math, URLs, citations, quotes, freeze terms, numbers) articulate.invariants has
already blanked, so a word inside a container is counted once, as part of it.
Each item has the shape of an invariants item: `kind`, a normalized `key`, the
surface `text`, and its `start` and `end` offsets. Standard library only.
"""
from __future__ import annotations

import bisect
import re

_MODAL = re.compile(
    r"(?i)\b(?:(must|shall|should|may|might|can|could)(?=n['\u2019]t\b|not\b|\b)"
    r"|(sha)(?=n['\u2019]t\b)|(required|recommended|optional)\b"
    r"|(ought\s{1,3}to|ha(?:ve|s|d)\s{1,3}to|needs?\s{1,3}to)\b)")
_MODAL_CLASS = {"must": "required", "shall": "required", "sha": "required",
                "required": "required", "have": "required", "has": "required",
                "had": "required", "need": "required", "needs": "required",
                "should": "recommended", "recommended": "recommended",
                "ought": "recommended", "may": "optional", "might": "optional",
                "can": "optional", "could": "optional", "optional": "optional"}
BCP14 = frozenset({"MUST", "SHALL", "SHOULD", "MAY", "REQUIRED", "RECOMMENDED",
                   "OPTIONAL"})
_SCOPE = re.compile(
    r"(?i)\b(?:(only|solely|exclusively)|(unless)|(except)"
    r"|(at\s{1,3}least|no\s{1,3}(?:fewer|less)\s{1,3}than|a\s{1,3}minimum\s{1,3}of)"
    r"|(at\s{1,3}most|no\s{1,3}more\s{1,3}than|a\s{1,3}maximum\s{1,3}of"
    r"|up\s{1,3}to(?=\s{1,3}[\d$]))|(always)|(exactly))\b")
_SCOPE_KEYS = ("only", "unless", "except", "at-least", "at-most", "always", "exactly")
_NEGATION = re.compile(r"(?i)\b(?:not|never|none|nothing|nobody|nowhere|without"
                       r"|neither|nor|cannot)\b|\bno\b(?!\.\s?\d)|n['\u2019]t\b")
_ENTITY = re.compile(r"\b[A-Z][A-Za-z0-9]{0,40}(?:[.+\-][A-Za-z0-9]{1,40}){0,4}"
                     r"(?:['\u2019]s)?\b")
_NOT_ENTITY = BCP14 | {"I", "NOT"}
_LEAD_MARKUP = re.compile(r"(?:^|\s)(?:[-+*]|\d{1,3}[.)])$")


def item(kind, key, text, start, end, **extra):
    """One invariant record."""
    rec = {"kind": kind, "key": key, "text": text, "start": start, "end": end}
    rec.update(extra)
    return rec


def _is_initial(masked, pos, starts):
    """True when a token opens a sentence or a block: the start of a line after a
    blank or a sentence end, or right after '.', '!', '?', or ':'. It reads a
    bounded window before the token, so a long single-line input stays linear."""
    k = bisect.bisect_right(starts, pos) - 1
    line_start = starts[k]
    lo = max(line_start, pos - 160)
    raw = masked[lo:pos]
    prefix = _LEAD_MARKUP.sub("", raw.rstrip(" \t*_#>([\"'\u201c\u2018|~")).rstrip()
    if prefix:
        return prefix[-1] in ".!?:"
    if k == 0 or raw.strip() or lo > line_start:
        return True
    last_line = masked[starts[k - 1]:line_start].strip()
    # A wrapped prose line continues the sentence above it; a blank line, a
    # sentence end, a heading, or a table row above starts a new block.
    return (not last_line or last_line[-1] in ".!?:"
            or last_line.startswith(("#", "|", "```", "~~~")))


def tokens(masked, freeze_keys):
    """The word-level items, read from the masked text."""
    items = []
    for m in _MODAL.finditer(masked):
        word = m.group(0)
        head = re.split(r"\s", word, maxsplit=1)[0].lower()
        cls = _MODAL_CLASS[head]
        key = cls + (":BCP14" if word in BCP14 else "")
        items.append(item("modal", key, word, m.start(), m.end()))
    for m in _SCOPE.finditer(masked):
        key = _SCOPE_KEYS[m.lastindex - 1]
        items.append(item("scope", key, m.group(0), m.start(), m.end()))
    for m in _NEGATION.finditer(masked):
        items.append(item("negation", "negation", m.group(0), m.start(), m.end()))
    starts = [0] + [m.end() for m in re.finditer("\n", masked)]
    for m in _ENTITY.finditer(masked):
        word = m.group(0)
        key = re.sub(r"['\u2019]s$", "", word)
        if key in _NOT_ENTITY or key in freeze_keys:
            continue
        acronym = sum(c.isupper() for c in key) >= 2 or any(c.isdigit() for c in key)
        weak = _is_initial(masked, m.start(), starts) and not acronym
        items.append(item("entity", key, word, m.start(), m.end(), weak=weak))
    return items
