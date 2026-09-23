#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
articulate.protect -- protected spans a rewrite never sees.

Before any model rewrite, `mask` replaces each protected span with a numbered
placeholder, in document order. The model rewrites the prose around the
placeholders and never sees what they stand for. `restore` then checks the
model's output and splices each span back byte for byte.

Protected by default: fenced and inline code, math, URLs and emails, citations,
block quotes, quoted material, and freeze terms. Block quotes and quoted material
can be switched off, for a document where the quotes are the author's own prose.

A placeholder reads like this: U+2983, a kind label, an index, a six-character
nonce drawn from the text's hash, U+2984. The nonce ties the placeholders to one
text, so a document that happens to contain a similar string cannot collide with
them. `restore` refuses the output, and the caller keeps the previous text,
unless every placeholder comes back exactly once and in order, and no stray,
invented, or mangled placeholder remains. Standard library only.
"""
from __future__ import annotations

import hashlib
import re

from . import invariants

OPEN, CLOSE = "⦃", "⦄"
LABELS = {"code": "CODE", "blockquote": "BLOCKQUOTE", "math": "MATH", "url": "URL",
          "citation": "CITE", "quote": "QUOTE", "freeze": "TERM"}
PLACEHOLDER = re.compile("⦃([A-Z]{2,12})_(\\d{1,6})_([0-9a-f]{6})⦄")
CONFIGURABLE = ("quotes", "blockquotes")


class ProtectError(ValueError):
    """The rewrite did not return the protected spans intact. `problems` lists
    each one: {"problem": ..., "placeholder": ..., "kind": ..., "text": ...}."""

    def __init__(self, message, problems):
        super().__init__(message)
        self.problems = problems


def nonce_for(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:6]


def mask(text, *, freeze=(), quotes=True, blockquotes=True, tex=False):
    """Return (masked, spans). Each span is a dict with its kind, placeholder,
    original text, and offsets, listed in document order."""
    passes = invariants.container_passes(freeze, numbers=False, quotes=quotes,
                                         block_quotes=blockquotes, tex=tex)
    claims, _ = invariants.claim(text, passes)
    claims.sort(key=lambda c: c[1])
    nonce = nonce_for(text)
    spans, parts, pos = [], [], 0
    for i, (kind, start, end, _key) in enumerate(claims):
        ph = f"{OPEN}{LABELS[kind]}_{i}_{nonce}{CLOSE}"
        spans.append({"kind": kind, "placeholder": ph, "text": text[start:end],
                      "start": start, "end": end})
        parts.append(text[pos:start])
        parts.append(ph)
        pos = end
    parts.append(text[pos:])
    return "".join(parts), spans


def _problem(kind, span=None, placeholder=None):
    rec = {"problem": kind, "placeholder": placeholder or (span or {}).get("placeholder")}
    if span:
        rec.update(kind=span["kind"], text=span["text"])
    return rec


def _placeholder_problems(found, spans):
    by_ph = {s["placeholder"]: s for s in spans}
    problems = []
    for s in spans:
        n = found.count(s["placeholder"])
        if n == 0:
            problems.append(_problem("missing", s))
        elif n > 1:
            problems.append(_problem("duplicated", s))
    for ph in dict.fromkeys(found):
        if ph not in by_ph:
            problems.append(_problem("invented", placeholder=ph))
    if not problems and found != [s["placeholder"] for s in spans]:
        problems.append(_problem("out-of-order", placeholder=" ".join(found)))
    return problems


def _residue_problems(output, masked, spans):
    """A placeholder the model mangled (a lost bracket, an edited nonce) leaves
    delimiter characters or the nonce behind in the prose. Compare against the
    prose that went in, so a document that uses these characters itself is fine."""
    rest_out, rest_in = PLACEHOLDER.sub("", output), PLACEHOLDER.sub("", masked)
    marks = [c for c in (OPEN, CLOSE) if rest_out.count(c) > rest_in.count(c)]
    nonce = spans[0]["placeholder"].rsplit("_", 1)[1][:-1] if spans else None
    if nonce and rest_out.count(nonce) > rest_in.count(nonce):
        marks.append(nonce)
    return [_problem("mangled", placeholder=m) for m in marks]


def restore(output, masked, spans):
    """Splice the protected spans back into `output`, byte for byte. Raise
    ProtectError unless every placeholder of `masked` appears exactly once, in
    order, and nothing placeholder-like is left over."""
    found = [m.group(0) for m in PLACEHOLDER.finditer(output)]
    problems = _placeholder_problems(found, spans) + _residue_problems(output, masked, spans)
    if problems:
        raise ProtectError(describe(problems), problems)
    table = {s["placeholder"]: s["text"] for s in spans}
    return PLACEHOLDER.sub(lambda m: table[m.group(0)], output)


def describe(problems, limit=5):
    """A one-line summary for a refusal message."""
    parts = []
    for p in problems[:limit]:
        what = f" {p['kind']} {p['text'][:40]!r}" if p.get("text") is not None else ""
        parts.append(f"{p['problem']} placeholder{what}")
    if len(problems) > limit:
        parts.append(f"and {len(problems) - limit} more")
    return "; ".join(parts)
