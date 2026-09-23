#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
articulate.invariants -- the surface facts a rewrite must keep.

Extracts the surface features of a text whose change usually changes what the
text says: code and math spans, URLs and emails, citations, quoted strings,
project freeze terms, numbers (with units, percentages, dates, times, and
versions), modal strength, scope qualifiers, negations, and named entities.

Each item is a dict with a `kind`, a normalized `key` that two texts are compared
on, the surface `text`, and its `start`/`end` offsets. Container kinds (code,
math, URL, citation, quote, freeze, number) claim their span first and mask it,
so a number inside a URL or a name inside a quote is counted once, as part of its
container.

These are surface proxies. A rewrite can keep every one of them and still change
what the text means, and a rewrite can change one of them and keep the meaning.
The meaning module states that limit beside every report. Standard library only.
"""
from __future__ import annotations

import bisect
import re

from . import quantities

KINDS = ("code", "math", "url", "citation", "quote", "freeze", "number",
         "modal", "scope", "negation", "entity")

INLINE_CODE = re.compile(r"``[^\n]{1,500}?``|`[^`\n]{1,500}`")
MATH = [
    re.compile(r"\$\$.{1,4000}?\$\$", re.S),
    re.compile(r"\\\[.{1,4000}?\\\]", re.S),
    re.compile(r"\\\(.{1,1000}?\\\)", re.S),
    re.compile(r"\\begin\{([a-z]{1,20}\*?)\}.{0,8000}?\\end\{\1\}", re.S),
]
# Inline $...$ counts as math only when its body carries TeX syntax, so a price
# pair such as "$5 and $10" is not read as one formula.
INLINE_MATH = re.compile(r"\$(?=[^\s$])(?:\\.|[^$\\\n]){1,300}(?<=\S)\$")
TEX_SIGN = re.compile(r"[\\^_{}=<>]")
URL = re.compile(r"\bhttps?://[^\s<>\"'\])]{1,2000}|\bwww\.[^\s<>\"'\])]{1,2000}"
                  r"|\b[\w.+-]{1,64}@[\w-]{1,63}(?:\.[\w-]{1,63}){1,8}\b")
_YEAR = r"(?:1[6-9]|20)\d{2}[a-z]?"
CITATION = re.compile(
    r"\[-?@[^\]\n]{1,200}\]"                               # pandoc [@key, p. 3]
    r"|\[\^[\w-]{1,40}\]"                                   # footnote [^1]
    r"|\[\d{1,4}(?:\s{0,2}[,\u2013-]\s{0,2}\d{1,4}){0,20}\]"  # numeric [1], [1-3]
    r"|\((?:(?:see|cf\.|e\.g\.),?\s{1,3})?[A-Z][\w'\-]{1,40}"
    r"(?:\s{1,3}et\s{1,3}al\.|\s{1,3}(?:and|&)\s{1,3}[A-Z][\w'\-]{1,40})?,?\s{1,3}"
    + _YEAR + r"(?:,\s{0,2}pp?\.\s{0,2}[\d\u2013-]{1,12})?(?:;[^()\n]{1,120})?\)"
    r"|\b[A-Z][\w'\-]{1,40}\s{1,3}et\s{1,3}al\.(?:\s{0,2}\(" + _YEAR + r"\))?"
    r"|\bdoi:\s{0,2}10\.\d{4,9}/[^\s\"<>]{1,200}|\b10\.\d{4,9}/[^\s\"<>]{1,200}"
    r"|\barXiv:\s{0,2}(?:\d{4}\.\d{4,5}|[a-z\-]{2,20}(?:\.[A-Z]{2})?/\d{7})(?:v\d{1,3})?"
    r"|\\cite[tp]?\*?(?:\[[^\]\n]{0,80}\])?\{[^}\n]{1,200}\}")
QUOTE = re.compile("\"[^\"\\n]{1,500}\"|\u201c[^\u201d\\n]{1,500}\u201d")
_TRAIL = ".,;:!?'\""

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


def _item(kind, key, text, start, end, **extra):
    rec = {"kind": kind, "key": key, "text": text, "start": start, "end": end}
    rec.update(extra)
    return rec


def fenced_blocks(text):
    """(start, end) of each fenced code block, fences included. An unclosed fence
    runs to the end of the text, as a Markdown renderer reads it."""
    out, pos, open_at, fence = [], 0, None, ""
    for line in text.splitlines(keepends=True):
        body = line.strip()
        if open_at is None and body.startswith(("```", "~~~")):
            open_at, fence = pos, body[0]
        elif open_at is not None and len(body) >= 3 and set(body) == {fence}:
            out.append((open_at, pos + len(line.rstrip("\r\n"))))
            open_at = None
        pos += len(line)
    if open_at is not None:
        out.append((open_at, len(text.rstrip("\r\n"))))
    return out


def freeze_pattern(freeze):
    """A regex for the freeze terms as whole words, longest first, or None."""
    terms = sorted({t for t in freeze if t and t.strip()}, key=len, reverse=True)
    if not terms:
        return None
    return re.compile(r"(?<!\w)(?:" + "|".join(re.escape(t) for t in terms) + r")(?!\w)")


def blockquotes(text):
    """(start, end) of each run of Markdown block-quote lines ('>' at line start)."""
    out, pos, open_at, last_end = [], 0, None, 0
    for line in text.splitlines(keepends=True):
        if line.lstrip(" ")[:1] == ">" and len(line) - len(line.lstrip(" ")) <= 3:
            open_at = pos if open_at is None else open_at
            last_end = pos + len(line.rstrip("\r\n"))
        elif open_at is not None:
            out.append((open_at, last_end))
            open_at = None
        pos += len(line)
    if open_at is not None:
        out.append((open_at, last_end))
    return out


def _rx_pass(rx, trim=True, keep=None):
    def run(masked):
        out = []
        for m in rx.finditer(masked):
            end = m.end()
            while trim and end > m.start() + 1 and masked[end - 1] in _TRAIL:
                end -= 1
            if keep is None or keep(m.group(0)):
                out.append((m.start(), end, None))
        return out
    return run


def container_passes(freeze=(), *, numbers=True, quotes=True, block_quotes=False,
                     tex=False):
    """The container passes in priority order: (kind, finder). A finder maps the
    current masked text to a list of (start, end, key-or-None). `tex` reads every
    inline $...$ as math, as a .tex file does; otherwise inline math needs TeX
    syntax in its body."""
    passes = [("code", lambda t: [(s, e, None) for s, e in fenced_blocks(t)])]
    if block_quotes:
        passes.append(("blockquote", lambda t: [(s, e, None) for s, e in blockquotes(t)]))
    passes.append(("code", _rx_pass(INLINE_CODE, trim=False)))
    passes += [("math", _rx_pass(rx, trim=False)) for rx in MATH]
    passes += [("math", _rx_pass(INLINE_MATH, trim=False,
                                 keep=None if tex else TEX_SIGN.search)),
               ("url", _rx_pass(URL)), ("citation", _rx_pass(CITATION))]
    if quotes:
        passes.append(("quote", _rx_pass(QUOTE, trim=False)))
    frx = freeze_pattern(freeze)
    if frx is not None:
        passes.append(("freeze", _rx_pass(frx, trim=False)))
    if numbers:
        passes.append(("number", quantities.find))
    return passes


def claim(text, passes):
    """Run the passes in order and return (claims, masked): claims is a list of
    (kind, start, end, key-or-None), and masked is the text with every claimed
    span blanked (newlines kept), so a later pass cannot match inside an earlier
    claim."""
    claims, chars, masked = [], list(text), text
    for kind, finder in passes:
        found = finder(masked)
        for start, end, key in found:
            claims.append((kind, start, end, key))
            for i in range(start, end):
                if chars[i] != "\n":
                    chars[i] = " "
        if found:
            masked = "".join(chars)
    return claims, masked


def _containers(text, freeze):
    claims, masked = claim(text, container_passes(freeze))
    items = [_item(kind, text[s:e] if key is None else key, text[s:e], s, e)
             for kind, s, e, key in claims]
    return items, masked


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


def _tokens(masked, freeze_keys):
    """The token-level kinds, read from the masked text."""
    items = []
    for m in _MODAL.finditer(masked):
        word = m.group(0)
        head = re.split(r"\s", word, maxsplit=1)[0].lower()
        cls = _MODAL_CLASS[head]
        key = cls + (":BCP14" if word in BCP14 else "")
        items.append(_item("modal", key, word, m.start(), m.end()))
    for m in _SCOPE.finditer(masked):
        key = _SCOPE_KEYS[m.lastindex - 1]
        items.append(_item("scope", key, m.group(0), m.start(), m.end()))
    for m in _NEGATION.finditer(masked):
        items.append(_item("negation", "negation", m.group(0), m.start(), m.end()))
    starts = [0] + [m.end() for m in re.finditer("\n", masked)]
    for m in _ENTITY.finditer(masked):
        word = m.group(0)
        key = re.sub(r"['\u2019]s$", "", word)
        if key in _NOT_ENTITY or key in freeze_keys:
            continue
        acronym = sum(c.isupper() for c in key) >= 2 or any(c.isdigit() for c in key)
        weak = _is_initial(masked, m.start(), starts) and not acronym
        items.append(_item("entity", key, word, m.start(), m.end(), weak=weak))
    return items


def extract(text, *, freeze=()):
    """Every surface invariant in `text`, in document order within each kind."""
    containers, masked = _containers(text, tuple(freeze))
    items = containers + _tokens(masked, set(freeze))
    items.sort(key=lambda i: (KINDS.index(i["kind"]), i["start"]))
    return items
