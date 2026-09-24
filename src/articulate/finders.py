#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
articulate.finders -- span finders for the container kinds that a plain regex
gets wrong.

A finder maps a text to a list of (start, end, key-or-None) spans, the shape
articulate.invariants expects from a container pass. The protected-span layer
and the meaning guard share these finders, so both read a span the same way.

`url_spans` applies the GitHub rule for a link's end. A URL may hold brackets,
as in https://en.wikipedia.org/wiki/Mercury_(planet), so the run takes ')' and
']' and then drops the trailing ones that close nothing inside the URL. The
closing bracket of a Markdown link and trailing punctuation stay prose, and so
does a numeric or pandoc citation written right after a URL ("docs[1]").

Each finder runs in linear time on any input. Standard library only.
"""
from __future__ import annotations

import re

TRAIL = ".,;:!?'\""
# A URL run stops at whitespace, an angle bracket, or a quote mark. It takes
# brackets; url_spans trims the unbalanced ones. The e-mail alternative keeps its
# bounded parts, which keeps it linear on a long run of dotted words.
URL_RUN = re.compile(r"\bhttps?://[^\s<>\"']+|\bwww\.[^\s<>\"']+"
                     r"|\b[\w.+-]{1,64}@[\w-]{1,63}(?:\.[\w-]{1,63}){1,8}\b")
_CITE_TAIL = re.compile(r"\[(?:\d{1,4}(?:[,–-]\d{1,4}){0,20}"
                        r"|-?@[^\[\]()\s]{1,200}|\^[\w-]{1,40})\]")
_CLOSER = {")": "(", "]": "["}


def _url_end(s, start, end):
    """The end of the URL in s[start:end] once trailing punctuation, unbalanced
    closing brackets, and a trailing citation are dropped. Each step removes at
    least one character, and the bracket counts are kept as running totals, so
    the trim is linear in the run's length."""
    opened = {c: s.count(o, start, end) for c, o in _CLOSER.items()}
    closed = {c: s.count(c, start, end) for c in _CLOSER}
    while end > start + 1:
        c = s[end - 1]
        if c in TRAIL:
            end -= 1
        elif c in _CLOSER and closed[c] > opened[c]:
            closed[c] -= 1
            end -= 1
        elif c == "]":
            i = s.rfind("[", start, end)
            if i <= start or not _CITE_TAIL.fullmatch(s, i, end):
                break
            opened[c] -= 1
            closed[c] -= 1
            end = i
        else:
            break
    return end


def url_spans(text):
    """URLs and e-mail addresses, as (start, end, None)."""
    out = []
    for m in URL_RUN.finditer(text):
        end = _url_end(text, m.start(), m.end())
        out.append((m.start(), end, None))
    return out
