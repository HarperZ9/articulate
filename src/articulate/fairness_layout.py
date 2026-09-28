#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.fairness_layout -- the layouts G4 compares a document under.

G4 asks whether findings move when the same words are laid out differently. A
layout keeps the document's structure: its paragraphs and its Markdown blocks,
as the scanner reads them (articulate.logical.units).

  rewrap          one sentence per line inside each paragraph and list item,
                  with the blank lines between blocks kept
  hardwrap        each paragraph and list item hard-wrapped at 60 columns,
                  breaking at hyphens too
  rewrap_joined   the rewrap before ruleset 0.9.0: every newline read as a space,
                  so all paragraphs join into one. Reported, never gated

Joining paragraphs is a change of structure. In CommonMark a blank line ends a
paragraph and no quotation pairs across it; the joined rewrap let a quotation
left open in one paragraph pair with a mark in the next, and joined a paragraph
with no closing punctuation to the next sentence. A list item, heading, table
row or block quote starts its own block with no blank line before it, so the
layouts re-break only paragraphs and list items and keep every other line as it
is: headings, table rows, rules, block quotes, fenced code and frontmatter.
Inside a paragraph no laid-out line opens a new block (a list, heading, block
quote, table or fence marker at its start): the break moves back one word, or
the line joins the one before it. Every break also joins back as the scanner
joins lines, with a space, or with none after a hyphen between two letters, so
the scanner reads the same words.

Standard library only.
"""
from __future__ import annotations

import re
import textwrap

from .logical import line_kinds, units

_SENT = re.compile(r"(?<=[.!?])\s+")
# A line Markdown reads as the start of a new block: a list item, a heading, a
# block quote, a table row, a code fence, or a thematic break or setext
# underline.
BLOCK_MARKER = re.compile(r"^\s*(?:(?:[-*+]|\d+[.)]|#{1,6}|>|\|)(?:\s|$)|```|~~~"
                          r"|(?:[-=_*]\s*){3,}$)")
# The logical lines a layout re-breaks. Every other line is kept as it is.
_FLOW = ("prose", "bullet")


def _structure(text):
    """The document in order: ("flow", text) for each paragraph or list item the
    scanner reads as one logical line, ("keep", line) for every other line, and
    ("blank", "") for a run of blank lines between blocks."""
    lines = text.splitlines(keepends=True)
    flow = {u.first_line: u for u in units(lines) if u.kind in _FLOW}
    out, covered = [], set()
    for n, (raw, kind) in enumerate(zip(lines, line_kinds(lines)), 1):
        if n in covered:
            continue
        if n in flow:
            covered.update(piece[2] for piece in flow[n].pieces)
            out.append(("flow", flow[n].text))
        elif kind == "blank":
            if out and out[-1][0] != "blank":
                out.append(("blank", ""))
        else:
            out.append(("keep", raw.rstrip("\r\n")))
    return out


def _bare_join(t, end, start):
    """True when the scanner joins a line that ends at `end` to one that starts
    at `start` with no space: a hyphen after a letter, then a letter
    (articulate.logical.Unit.add)."""
    return (end > 1 and t[end - 1] == "-" and t[end - 2].isalpha()
            and t[start:start + 1].isalpha())


def _exact(t, end, start):
    """True when the break between t[:end] and t[start:] joins back to t: a
    space where the text had whitespace, none where it had none."""
    return _bare_join(t, end, start) == (end == start)


def _opens_block(t, prev, cur):
    """True when the line t[cur] after the line t[prev] would open a new block."""
    line = t[cur[0]:cur[1]]
    return bool(BLOCK_MARKER.match(line)) or line_kinds([t[prev[0]:prev[1]], line])[1] != "prose"


def _move_back(t, prev, cur):
    """(prev, cur) with the last word of `prev` moved to the start of `cur`, or
    None when no break there keeps the lines apart and exact."""
    head = t[prev[0]:prev[1]].rstrip()
    k = max(head.rfind(" "), head.rfind("\t"))
    if k <= 0:
        return None
    head_end = prev[0] + len(head[:k].rstrip())
    new_prev, new_cur = (prev[0], head_end), (prev[0] + k + 1, cur[1])
    if head_end <= prev[0] or _opens_block(t, new_prev, new_cur) \
            or not _exact(t, head_end, new_cur[0]):
        return None
    return new_prev, new_cur


def _settle(t, spans, move_back):
    """Make every break between the line spans of `t` keep the block and join
    back exactly. A line that would open a block moves the break back one word
    when `move_back`; otherwise, or when the break would not join back, the two
    lines join."""
    spans = list(spans)
    i = 1
    while i < len(spans):
        prev, cur = spans[i - 1], spans[i]
        if _opens_block(t, prev, cur):
            moved = _move_back(t, prev, cur) if move_back else None
            if moved:
                spans[i - 1], spans[i] = moved
                i += 1
                continue
        elif _exact(t, prev[1], cur[0]):
            i += 1
            continue
        spans[i - 1:i + 1] = [(prev[0], cur[1])]
    return spans


def _sentence_spans(t):
    spans, pos = [], 0
    for m in _SENT.finditer(t):
        spans.append((pos, m.start()))
        pos = m.end()
    spans.append((pos, len(t)))
    return _settle(t, [(s, e) for s, e in spans if t[s:e].strip()], move_back=False)


def _wrap_spans(t, width):
    lines = textwrap.wrap(t, width, break_long_words=False, expand_tabs=False,
                          replace_whitespace=False)
    spans, pos = [], 0
    for line in lines:
        start = t.index(line, pos)
        spans.append((start, start + len(line)))
        pos = start + len(line)
    return _settle(t, spans, move_back=True)


def _layout(text, spans_of):
    out = []
    for kind, value in _structure(text):
        if kind == "flow":
            out.extend(value[s:e] for s, e in spans_of(value))
        else:
            out.append(value)
    while out and not out[-1]:
        out.pop()
    return "\n".join(out) + "\n"


def rewrap(text):
    """The same words, one sentence per line, inside each paragraph and list
    item."""
    return _layout(text, _sentence_spans)


def rewrap_joined(text):
    """The rewrap before ruleset 0.9.0, which joined every paragraph into one.
    The harness reports how many documents it changes and never gates on it."""
    return "\n".join(s.strip() for s in _SENT.split(text.replace("\n", " "))
                     if s.strip()) + "\n"


def hardwrap(text, width=60):
    """The same words hard-wrapped at `width` columns, breaking at hyphens too,
    inside each paragraph and list item."""
    return _layout(text, lambda t: _wrap_spans(t, width))
