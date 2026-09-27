#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
articulate.pack_util -- shared helpers for the domain rule packs.

A pack receives the prose lines of a document as (line_no, offset, raw, masked)
tuples, with code, URLs, markup, and TeX masked to spaces. These helpers group
them into sentences and count words and syllables.

`sentences` joins wrapped lines of one paragraph and splits on sentence ends, so
a sentence that wraps across lines is one record. A blank line, a list item, a
heading, a quote, or a table row starts a new paragraph. Each record keeps the
line and the in-line offsets where it starts, which is where a finding anchors.

`paragraph_hits` runs a pattern over each paragraph read as one line, the way
the core checks read logical lines, so a phrase with a line break inside it
matches as it would unwrapped. The finding anchors on the line where the match
starts.

`syllables` counts runs of vowels after dropping a silent ending (-e, -ed, -es,
with the usual exceptions). It miscounts some words: "created" reads as 2 and
"poem" as 1, where a dictionary gives 3 and 2. Any readability score built on it
is an estimate. Standard library only.
"""
from __future__ import annotations

import bisect
import re

WORD =re.compile(r"[A-Za-z0-9]+(?:['’\-][A-Za-z0-9]+)*")
_SENT_END = re.compile(r"(?<=[.!?])[\"')\]”’]*\s+")
_BLOCK = re.compile(r"^\s{0,3}(?:[-*+]\s|\d{1,3}[.)]\s|#{1,6}\s|>|\|)")
_LEAD = re.compile(r"^\s{0,3}(?:[-*+]\s+|\d{1,3}[.)]\s+|#{1,6}\s+|>\s*)")


def words(text):
    return WORD.findall(text)


def _drop_silent_ending(w):
    if re.search(r"[^aeiouy]le$", w):           # table, people: the -le is a syllable
        return w
    if w.endswith("ed"):                          # jumped is one; created keeps -ted
        return w if re.search(r"[td]ed$", w) else w[:-2]
    if w.endswith("es"):                          # makes is one; boxes keeps -xes
        return w if re.search(r"(?:[sxzcg]|ch|sh)es$", w) else w[:-2]
    if w.endswith("e") and not w.endswith(("ee", "ye")):
        return w[:-1]
    return w


def syllables(word):
    """Estimated syllables in one word: runs of vowels after dropping a silent
    ending. Never less than one for a word with a letter."""
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    if len(w) <= 3:
        return 1
    w = re.sub(r"^y", "", _drop_silent_ending(w))
    return max(1, len(re.findall(r"[aeiouy]+", w)))


def _paragraphs(prose):
    """Groups of consecutive prose lines that form one paragraph."""
    group = []
    for rec in prose:
        body = rec[3].strip()
        if not body or _BLOCK.match(rec[3]):
            if group:
                yield group
            group = [rec] if body else []
            if body.startswith("#"):          # a heading stands alone
                yield group
                group = []
        else:
            group.append(rec)
    if group:
        yield group


class LineMatch:
    """A match over a paragraph, placed on the line where it starts. start() and
    end() are offsets in that line; end() stops at the line's end when the match
    wraps. group() is the matched text, and before() and after() are the
    characters around it in the paragraph."""
    __slots__ = ("_m", "_start", "_end")

    def __init__(self, m, start, end):
        self._m, self._start, self._end = m, start, end

    def start(self):
        return self._start

    def end(self):
        return self._end

    def group(self, i=0):
        return self._m.group(i)

    def before(self):
        return self._m.string[self._m.start() - 1:self._m.start()]

    def after(self):
        return self._m.string[self._m.end():self._m.end() + 1]


def _runs(prose):
    """Paragraphs as runs of consecutive lines. A skipped fence or front-matter
    line between two prose lines ends a run, as it ends a logical line."""
    for group in _paragraphs(prose):
        run = []
        for rec in group:
            if run and rec[0] != run[-1][0] + 1:
                yield run
                run = []
            run.append(rec)
        if run:
            yield run


def paragraph_hits(prose, rx):
    """(line_no, offset, raw, LineMatch) for each match of rx over each
    paragraph, with its line breaks read as spaces. Masking keeps each line's
    length, so an index in the joined text maps back to its line."""
    for run in _runs(prose):
        text, starts, owners = "", [], []
        for line_no, off, raw, masked in run:
            starts.append(len(text))
            owners.append((line_no, off, raw))
            text += masked.replace("\r", " ").replace("\n", " ")
        for m in rx.finditer(text):
            i = bisect.bisect_right(starts, m.start()) - 1
            line_no, off, raw = owners[i]
            width = len(raw.rstrip("\r\n"))
            start = m.start() - starts[i]
            yield line_no, off, raw, LineMatch(m, start, max(start, min(m.end() - starts[i],
                                                                        width)))


def sentences(prose):
    """Sentence records:{"text", "line", "offset", "raw", "start", "end",
    "block_start"} where line/offset/raw locate the first line of the sentence,
    start/end are in-line offsets on that line for a finding, and block_start is
    True for the first sentence of a list item, heading, or paragraph."""
    out = []
    for group in _paragraphs(prose):
        joined, owners = "", []
        for line_no, off, raw, masked in group:
            lead = len(_LEAD.match(masked).group(0)) if _LEAD.match(masked) else 0
            piece = masked.rstrip("\r\n")
            owners.append((len(joined), line_no, off, raw, lead))
            joined += piece + " "
        pos = 0
        for m in list(_SENT_END.finditer(joined)) + [None]:
            end = m.start() if m else len(joined)
            chunk = joined[pos:end]
            if chunk.strip():
                out.append(_record(chunk, pos, owners, block_start=(pos == 0)))
            if m is None:
                break
            pos = m.end()
    return out


def _record(chunk, pos, owners, block_start):
    lead_ws = len(chunk) - len(chunk.lstrip())
    start_abs = pos + lead_ws
    owner = [o for o in owners if o[0] <= start_abs][-1]
    base, line_no, off, raw, lead = owner
    start = max(start_abs - base, lead)
    line_text = raw.rstrip("\r\n")
    end = min(len(line_text), start + len(chunk.strip()))
    return {"text": chunk.strip(), "line": line_no, "offset": off, "raw": raw,
            "start": start, "end": max(end, start), "block_start": block_start}


def finding(make, sent, category, label, start=None, end=None):
    """A finding anchored on a sentence (or on start/end within its first line)."""
    s = sent["start"] if start is None else start
    e = sent["end"] if end is None else end
    return make(sent["line"], sent["offset"], category, label, s, e, sent["raw"],
                sent["raw"].strip()[:100])


def empty():
    return {"HIGH": [], "MEDIUM": [], "LOW": []}
