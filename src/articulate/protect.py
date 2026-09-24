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
nonce drawn from the text's hash, U+2984. The nonce is chosen so it occurs
nowhere in the text. A placeholder-shaped string already in the document, or a
stray U+2983 or U+2984, is masked first as a span of its own ("literal"), so
it never reaches the model and cannot pass for a placeholder. `restore`
refuses the output, and the caller keeps the previous text, unless every
placeholder comes back exactly once and in order, and no stray, invented, or
mangled placeholder remains. Standard library only.
"""
from __future__ import annotations

import collections
import hashlib
import re

from . import invariants

OPEN, CLOSE = "⦃", "⦄"
LABELS = {"code": "CODE", "blockquote": "BLOCKQUOTE", "math": "MATH", "url": "URL",
          "citation": "CITE", "quote": "QUOTE", "freeze": "TERM", "literal": "LITERAL"}
PLACEHOLDER = re.compile("⦃([A-Z]{2,12})_(\\d{1,6})_([0-9a-f]{6})⦄")
# Anything in the document that could read as a placeholder: a bracketed run on
# one line, or a lone delimiter.
_LITERAL = re.compile("⦃[^⦃⦄\\n]{0,64}⦄|[⦃⦄]")
_NONCE_TRIES = 64
CONFIGURABLE = ("quotes", "blockquotes")


class ProtectError(ValueError):
    """The rewrite did not return the protected spans intact. `problems` lists
    each one: {"problem": ..., "placeholder": ..., "kind": ..., "text": ...}."""

    def __init__(self, message, problems):
        super().__init__(message)
        self.problems = problems


def _candidate(text, i):
    seed = text.encode("utf-8") + (b"" if i == 0 else b"\0%d" % i)
    return hashlib.sha256(seed).hexdigest()[:6]


def nonce_for(text):
    """Six hex characters from the text's hash, the first candidate that occurs
    nowhere in the text. A text can be built to hold its own first candidate;
    the next one comes from a salted hash. The literal pass already keeps such
    a text from colliding, so after a bounded number of tries the last
    candidate stands."""
    nonce = _candidate(text, 0)
    for i in range(1, _NONCE_TRIES):
        if nonce not in text:
            break
        nonce = _candidate(text, i)
    return nonce


def _literals(text):
    return [(m.start(), m.end(), None) for m in _LITERAL.finditer(text)]


def _outermost(claims):
    """The claims to mask, disjoint and in document order. A pass runs over the
    text with earlier claims blanked, so a later claim can enclose an earlier
    one: a quote around a code span, display math around a '>' line. The inner
    claim then travels inside the outer placeholder. A partial overlap widens the
    kept claim, so the layer protects more text and never less."""
    kept = []
    for kind, start, end, key in sorted(claims, key=lambda c: (c[1], -c[2])):
        if kept and start < kept[-1][2]:
            if end > kept[-1][2]:
                kept[-1] = kept[-1][:2] + (end, kept[-1][3])
            continue
        kept.append((kind, start, end, key))
    return kept


def mask(text, *, freeze=(), quotes=True, blockquotes=True, tex=False):
    """Return (masked, spans). Each span is a dict with its kind, placeholder,
    original text, and offsets, listed in document order. The spans never
    overlap, and restoring the masked text unchanged gives back `text` exactly.
    A masking that fails that check raises ProtectError and returns nothing."""
    passes = [("literal", _literals)] + invariants.container_passes(
        freeze, numbers=False, quotes=quotes, block_quotes=blockquotes, tex=tex)
    claims, _ = invariants.claim(text, passes)
    nonce = nonce_for(text)
    spans, parts, pos = [], [], 0
    for i, (kind, start, end, _key) in enumerate(_outermost(claims)):
        ph = f"{OPEN}{LABELS[kind]}_{i}_{nonce}{CLOSE}"
        spans.append({"kind": kind, "placeholder": ph, "text": text[start:end],
                      "start": start, "end": end})
        parts.append(text[pos:start])
        parts.append(ph)
        pos = end
    parts.append(text[pos:])
    masked = "".join(parts)
    if restore(masked, masked, spans) != text:
        raise ProtectError("masking did not round-trip", [_problem("round-trip")])
    return masked, spans


def _problem(kind, span=None, placeholder=None):
    rec = {"problem": kind, "placeholder": placeholder or (span or {}).get("placeholder")}
    if span:
        rec.update(kind=span["kind"], text=span["text"])
    return rec


def _placeholder_problems(found, spans):
    by_ph = {s["placeholder"]: s for s in spans}
    counts = collections.Counter(found)
    problems = []
    for s in spans:
        n = counts[s["placeholder"]]
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
