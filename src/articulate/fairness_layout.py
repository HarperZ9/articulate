#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.fairness_layout -- the layouts G4 compares a document under.

G4 asks whether findings move when the same words are laid out differently. A
layout keeps the document's structure: its paragraphs and its Markdown blocks.

  rewrap          one sentence per line inside each paragraph, with the blank
                  lines between paragraphs kept
  hardwrap        each paragraph hard-wrapped at 60 columns, breaking at hyphens
  rewrap_joined   the rewrap before ruleset 0.9.0: every newline read as a space,
                  so all paragraphs join into one. Reported, never gated

Joining paragraphs is a change of structure. In CommonMark a blank line ends a
paragraph and no quotation pairs across it; the joined rewrap let a quotation
left open in one paragraph pair with a mark in the next, and joined a paragraph
with no closing punctuation to the next sentence. Neither layout starts a line
with a list, heading, block quote, table or fence marker: Markdown reads such a
line as a new block, so the wrapped text would be a different document. The
break moves back one word instead, or the line joins the one before it.

Standard library only.
"""
from __future__ import annotations

import re
import textwrap

_SENT = re.compile(r"(?<=[.!?])\s+")
_PARA = re.compile(r"\n\s*\n")
# A line Markdown reads as the start of a new block: a list item, a heading, a
# block quote, a table row, a code fence, or a thematic break or setext
# underline.
BLOCK_MARKER = re.compile(r"^\s*(?:(?:[-*+]|\d+[.)]|#{1,6}|>|\|)(?:\s|$)|```|~~~"
                          r"|(?:[-=_*]\s*){3,}$)")


def _paragraphs(text):
    return [p.replace("\n", " ") for p in _PARA.split(text) if p.strip()]


def _keep_blocks(lines):
    """Join each line that would open a new block onto the line before it."""
    out = []
    for line in lines:
        if out and BLOCK_MARKER.match(line):
            out[-1] = out[-1] + " " + line
        else:
            out.append(line)
    return out


def _sentences(para):
    return [s.strip() for s in _SENT.split(para) if s.strip()]


def rewrap(text):
    """The same words, one sentence per line, paragraph by paragraph."""
    paras = ["\n".join(_keep_blocks(_sentences(p))) for p in _paragraphs(text)]
    return "\n\n".join(p for p in paras if p) + "\n"


def rewrap_joined(text):
    """The rewrap before ruleset 0.9.0, which joined every paragraph into one.
    The harness reports how many documents it changes and never gates on it."""
    return "\n".join(_sentences(text.replace("\n", " "))) + "\n"


def _fill(para, width):
    """textwrap.fill, with the break moved back one word wherever a wrapped line
    would open a new block; a line with no earlier break joins the one before."""
    lines = textwrap.wrap(para, width, break_long_words=False)
    i = 1
    while i < len(lines):
        if BLOCK_MARKER.match(lines[i]):
            head, _sep, last = lines[i - 1].rpartition(" ")
            if head and not BLOCK_MARKER.match(last + " " + lines[i]):
                lines[i - 1], lines[i] = head, last + " " + lines[i]
            else:
                lines[i - 1] = lines[i - 1] + " " + lines.pop(i)
            continue
        i += 1
    return "\n".join(lines)


def hardwrap(text, width=60):
    """The same words hard-wrapped at `width` columns, breaking at hyphens too,
    paragraph by paragraph."""
    return "\n\n".join(_fill(p, width) for p in _paragraphs(text)) + "\n"
