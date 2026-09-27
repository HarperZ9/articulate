#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.quotemarks -- which quotation marks pair, in linear time.

A quotation is its source's words, so the phrasing rules read the text with each
quotation blanked. A mark that is not a quotation mark must open nothing: an
inch mark (6" tall), an apostrophe typed as a backtick or as a curly single
quote (didn`t, it’s), or an autocorrected year (‘90s). When such a mark paired
with the next mark in the paragraph, the writer's own prose between them went
unread, and a layout that merged two paragraphs moved the pair.

Rules (SCAN_ALGO 7):

- Each family of marks has one open quotation at a time, and a line break
  resets every family. Families: straight double quotes; curly double quotes
  with the German low opener („) and the Swedish same-mark style (”…”); curly
  single quotes with the German low opener (‚); guillemets in both directions
  («…» and »…«); single guillemets; CJK corner brackets.
- A mark whose glyph names its direction opens or closes by its glyph. A second
  opener before a closer replaces the first, which was never closed and blanks
  nothing.
- A straight double quote, a Swedish ”, a curly ‘ and a guillemet read in the
  reverse direction open only in opening position: at a line start or after a
  space, an opening bracket, a dash, a slash, a comma, a colon or a semicolon,
  and before a character that is not a space. A straight quote closes after any
  character that is not a space, so a quote after a digit closes an open
  quotation ("top 10") and opens none (6" tall).
- A curly ‘ before a digit or after a letter is an apostrophe (‘90s, rock‘n).
  A curly ’ between two letters is an apostrophe (it’s) and closes nothing.
- A mark that finds no closer before the line ends blanks nothing.

Straight single quotes are never read as quotation marks: an apostrophe would
open a false span. Standard library only.
"""
from __future__ import annotations

import re

DQ = chr(0x22)            # straight double quote
LDQ, RDQ = chr(0x201C), chr(0x201D)
LOW_DQ = chr(0x201E)      # German and Polish opening mark
LSQ, RSQ = chr(0x2018), chr(0x2019)
LOW_SQ = chr(0x201A)
LGUIL, RGUIL = chr(0xAB), chr(0xBB)
LSGUIL, RSGUIL = chr(0x2039), chr(0x203A)
LCORNER, RCORNER = chr(0x300C), chr(0x300D)
LWCORNER, RWCORNER = chr(0x300E), chr(0x300F)

# family -> {opening mark: the marks that close it}. A mark listed as a closer
# of the open quotation closes it before it is read as an opener.
FAMILIES = {
    "straight": {DQ: DQ},
    "double": {LDQ: RDQ, LOW_DQ: LDQ + RDQ, RDQ: RDQ},
    "single": {LSQ: RSQ, LOW_SQ: LSQ + RSQ},
    "guillemet": {LGUIL: RGUIL, RGUIL: LGUIL},
    "single-guillemet": {LSGUIL: RSGUIL, RSGUIL: LSGUIL},
    "corner": {LCORNER: RCORNER, LWCORNER: RWCORNER},
}
# Openers that need opening position: their glyph does not name a direction,
# or it doubles as an apostrophe or as a closer in another style.
POSITIONAL = frozenset((DQ, RDQ, LSQ, RGUIL, RSGUIL))
OPEN_AFTER = frozenset("([{<-/,:;" + chr(0x2013) + chr(0x2014))
MARKS = frozenset(c for fam in FAMILIES.values()
                  for opener, closers in fam.items() for c in opener + closers)
FAMILY_OF = {c: name for name, fam in FAMILIES.items()
             for opener, closers in fam.items() for c in opener + closers}
_MARK_OR_BREAK = re.compile("[" + re.escape("".join(sorted(MARKS)) + chr(10)) + "]")


def _opening_position(line, i):
    before = line[i - 1] if i else " "
    after = line[i + 1] if i + 1 < len(line) else " "
    return (before.isspace() or before in OPEN_AFTER) and not after.isspace()


def _between_letters(line, i):
    return 0 < i < len(line) - 1 and line[i - 1].isalpha() and line[i + 1].isalpha()


def _closes(line, i, mark, pending):
    """True when the mark at i closes the open quotation `pending`."""
    if mark not in pending[1]:
        return False
    if mark == DQ:
        return not line[i - 1].isspace()
    # it’s: a curly apostrophe inside a word closes nothing.
    return not (mark == RSQ and _between_letters(line, i))


def _opens(line, i, mark, family):
    if mark not in FAMILIES[family]:
        return False
    if mark == LSQ:
        # ‘90s and rock‘n: an apostrophe before a digit or after a letter.
        after = line[i + 1] if i + 1 < len(line) else " "
        if after.isdigit() or (i and line[i - 1].isalpha()):
            return False
    return mark not in POSITIONAL or _opening_position(line, i)


def quote_spans(line):
    """(start, end) of every quotation in `line`, sorted, overlaps merged. One
    pass over the marks; each is read once."""
    spans, pending = [], {}
    for m in _MARK_OR_BREAK.finditer(line):
        i, mark = m.start(), m.group()
        if mark == chr(10):
            pending.clear()
            continue
        family = FAMILY_OF[mark]
        open_q = pending.get(family)
        if open_q is not None and _closes(line, i, mark, open_q):
            spans.append((open_q[0], i + 1))
            del pending[family]
        elif _opens(line, i, mark, family):
            pending[family] = (i, FAMILIES[family][mark])
    return _merge(spans)


def _merge(spans):
    merged = []
    for s, e in sorted(spans):
        if merged and s < merged[-1][1]:
            merged[-1] = (merged[-1][0], max(e, merged[-1][1]))
        else:
            merged.append((s, e))
    return merged


def table_parts():
    """The pairing table and position rules as text, for the ruleset fingerprint."""
    parts = [f"Q|{name}|{opener}|{closers}" for name, fam in sorted(FAMILIES.items())
             for opener, closers in sorted(fam.items())]
    return parts + ["Q|positional|" + "".join(sorted(POSITIONAL)),
                    "Q|open-after|" + "".join(sorted(OPEN_AFTER))]
