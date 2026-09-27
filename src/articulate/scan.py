#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.scan -- the core scanner over a document's lines.
Standard library only.
"""
from .advisories import (document_advisories, find_anaphora_runs,
                         find_contrast_pairs, find_fragment_openers)
from .binary import binary_reason
from .cadence import cadence_stats
import re

from .lexicon import ADVERB, EMOJI, PASSIVE, WORD
from .logical import line_kinds, sentences, units
from .markup import (ALLOW_EXEMPT_CATEGORIES, _rid, allowed, classify_fountain,
                     mask_c2pa, mask_quotes, read_allowlist, strip_markup)
from .quoting import mask_code, mask_direct, mask_lines, quoted_lines
from .rule_reasons import resolve_all
from .rules_high import HIGH, RENDERED, SELF_DESCRIPTION
from .sentence_notes import OPENERS as _OPENERS  # noqa: F401  (the fingerprint reads it)
from .sentence_notes import sentence_passes
from .rules_low import FICTION_SLOP, LOW, REGISTER_JARGON
from .rules_medium_register import MEDIUM_REGISTER
from .rules_medium_structure import MEDIUM_STRUCTURE

MEDIUM = MEDIUM_REGISTER + MEDIUM_STRUCTURE

# Bump SCAN_ALGO on any change to the scanner's control flow (what a line is,
# which pass runs on it, how many hits a rule may return). The fingerprint folds
# it in, so a receipt issued under the old flow reads Unverifiable, not Match.
#   1  one re.search per rule per physical line
#   2  logical lines (a paragraph joined, with an offset map), every match
#      counted, line-start rules run at every sentence start
#   3  a period after a common abbreviation (et al., e.g., i.e., Fig.) no longer
#      ends a sentence
#   4  a line that ends in a hyphen after a letter joins the next line with no
#      space, so a hard wrap inside "state-of-the-art" reads as one word
#   5  a sentence pass adds LOW notes for "in order to" and for "state of the
#      art" in a sentence with no number, year or citation marker
#   6  every phrasing rule reads the text with quotations blanked (direct
#      quotes, block quotes, LaTeX quote environments); the self-description
#      rule also skips tables, transcripts, verbatim and code spans; the
#      rendered-document rules still read every character; unsupported-authority
#      is a sentence rule that reads citation markers on the raw sentence
SCAN_ALGO = 6
# A Markdown table delimiter row is structure, never an em-dash.
SKIP_TABLE_SEP = True


def scan(path: str):
    """Read a file and scan it. Findings: (line, cat, label, snippet)."""
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError:
        return [], [], [], {}
    if binary_reason(data, name=path):
        return [], [], [], {}
    return scan_lines(data.decode("utf-8", errors="replace").splitlines(keepends=True))


_START = re.compile(r"^(?:\(\?[a-zA-Z]+\))?\^")


def _split(table):
    """(inline rules, sentence-start rules). A rule whose pattern opens with ^
    reads the start of a sentence; the rest read the whole logical line."""
    inline = [r for r in table if not _START.match(r[2].pattern)]
    start = [r for r in table if _START.match(r[2].pattern)]
    return inline, start


HIGH_RENDERED = _split([r for r in HIGH if (r[0], r[1]) in RENDERED])
HIGH_SELF = _split([r for r in HIGH if r[1] == SELF_DESCRIPTION])
HIGH_INLINE, HIGH_START = _split([r for r in HIGH if (r[0], r[1]) not in RENDERED
                                  and r[1] != SELF_DESCRIPTION])
MEDIUM_INLINE, MEDIUM_START = _split(MEDIUM)
LOW_INLINE, LOW_START = _split(LOW)


class _Scan:
    """Mutable state for one scan: the findings, the allowlist and the counts."""

    def __init__(self, lines, extra_allow, genre, roles=None):
        self.genre = genre
        self.block, self.shown = quoted_lines(lines, line_kinds(lines, roles))
        self.allow = read_allowlist(lines) | {a.lower() for a in extra_allow}
        self.high, self.medium, self.low = [], [], []
        self.prose, self.words, self.adv, self.passive = [], 0, 0, 0
        self.doc = "".join(lines)

    def add(self, dest, unit, cat, label, s, e, exempt=False, text=None):
        """Record a match at [s, e) of the unit's text, unless the allowlist
        keeps it. `text` is the masked text the match came from."""
        body = text if text is not None else unit.text
        if not exempt and allowed(body[s:e], self.allow):
            return
        start, end, line, end_line = unit.span(s, e)
        line_start = self.doc.rfind("\n", 0, start) + 1
        snip = unit.text.strip()
        if len(snip) > 100:
            snip = unit.text[max(0, s - 30):max(0, s - 30) + 100].strip()
        dest.append({"line": line, "end_line": end_line, "col": start - line_start + 1,
                     "start": start, "end": end, "category": cat, "label": label,
                     "match": self.doc[start:end], "snippet": snip,
                     "rule_id": _rid(cat, label)})

    def table(self, dest, unit, text, inline, start):
        for cat, label, rx in inline:
            for m in rx.finditer(text):
                self.add(dest, unit, cat, label, m.start(), m.end(),
                         cat in ALLOW_EXEMPT_CATEGORIES, text)
        for s, e in sentences(text):
            for cat, label, rx in start:
                m = rx.search(text[s:e])
                if m:
                    self.add(dest, unit, cat, label, s + m.start(), s + m.end(),
                             cat in ALLOW_EXEMPT_CATEGORIES, text)


def _raw_passes(sc, unit):
    """Emoji and the LOW formatting advisories read the raw text: markup matters."""
    raw = mask_quotes(unit.text) if sc.genre.get("quote_exempt_all") else unit.text
    for n, me in enumerate(EMOJI.finditer(raw)):
        sc.add(sc.low, unit, "emoji", "emoji in text", me.start(), me.end(), True)
        # Emoji as structure: in a heading, beside a bullet, or opening the line.
        if n == 0 and (unit.kind in ("heading", "bullet") or not raw[:me.start()].strip()):
            sc.add(sc.medium, unit, "emoji-structure",
                   "emoji as heading / bullet / status marker", me.start(), me.end(), True)
    sc.table(sc.low, unit, raw, LOW_INLINE, LOW_START)


def _device_passes(sc, unit, count_text, quoted, chat):
    """`quoted` has every quotation blanked; `chat` also blanks what a document
    shows as data. The rendered-document rules read `word`, unmasked."""
    word = strip_markup(unit.text)
    for m in re.finditer("---", quoted):   # three hyphens mid-line read as an em-dash
        sc.add(sc.high, unit, "em-dash", "em-dash (---)", m.start(), m.end(), True)
    sc.table(sc.high, unit, word, *HIGH_RENDERED)
    sc.table(sc.high, unit, chat, *HIGH_SELF)
    sc.table(sc.high, unit, quoted, HIGH_INLINE, HIGH_START)
    sc.table(sc.medium, unit, quoted, MEDIUM_INLINE, MEDIUM_START)
    for cat, label, rx in REGISTER_JARGON:   # a hit to fix; allowlist to keep
        for m in rx.finditer(quoted):
            sc.add(sc.medium, unit, cat, label, m.start(), m.end(), text=quoted)
    sentence_passes(sc, unit, quoted, unit.text)
    # Counts for the cadence and rate statistics. A kept term of art does not count.
    sc.words += len(WORD.findall(count_text))
    sc.adv += len(ADVERB.findall(count_text))
    sc.passive += len(PASSIVE.findall(count_text))
    if unit.kind in ("prose", "quote"):
        sc.prose.append(count_text)


def _scan_unit(sc, unit):
    g = sc.genre
    word_text = strip_markup(unit.text)          # the fiction lexicon reads the words
    if g.get("fiction_slop") and unit.role in ("prose", "dialogue"):
        for cat, label, rx in FICTION_SLOP:
            for m in rx.finditer(word_text):
                sc.add(sc.low, unit, cat, label, m.start(), m.end(), text=word_text)
    if unit.role not in ("prose", "action"):     # screenplay dialogue keeps its voice
        return
    _raw_passes(sc, unit)
    if unit.kind == "hr" or (unit.kind == "tablesep" and SKIP_TABLE_SEP):
        return
    masked = g.get("dialogue_exempt") or g.get("quote_exempt_all")
    count_text = mask_quotes(word_text) if masked else word_text
    quoted = mask_lines(unit, mask_direct(word_text, unit.text), sc.block)
    chat = mask_lines(unit, strip_markup(mask_code(unit.text)), sc.shown)
    chat = mask_direct(mask_lines(unit, chat, sc.block), unit.text)
    _device_passes(sc, unit, count_text, quoted, chat)


_BLANK = re.compile(r"[^\r\n]")


def _document_passes(sc, lines, suppress):
    if "contrast-pair" not in suppress:
        cp_lines = [_BLANK.sub(" ", ln) if i in sc.block else mask_direct(ln)
                    for i, ln in enumerate(lines, 1)]
        sc.medium.extend(find_contrast_pairs(cp_lines))
    # Report-only advisories with a minimum-size guard each (LOW).
    if "anaphora" not in suppress:
        sc.low.extend(find_anaphora_runs(lines))
    if "fragment-opener" not in suppress:
        sc.low.extend(find_fragment_openers(lines))
    sc.low.extend(document_advisories(lines, sc.words))


def scan_lines(lines, extra_allow=(), *, genre=None):
    """Core scanner over a list of raw lines. Shared by scan(path) and
    check_text(text), so the engine never needs the filesystem.

    `genre` is an optional dict of genre-layer options (from a genre profile or
    mode): `unit` ("sentence" default, or "line" for verse), `structural_classify`
    ("fountain" for screenplay), `dialogue_exempt`/`quote_exempt_all` for masking
    quoted speech, `fiction_slop` to run the report-only fiction lexicon, and
    `suppress_categories` to drop categories that name craft technique in a genre.

    A paragraph is read as one logical line (see articulate.logical), so a finding
    does not depend on where the writer broke lines. Verse and screenplay keep
    their physical lines."""
    genre = genre or {}
    joined = "".join(lines)
    masked = mask_c2pa(joined)
    if masked != joined:           # a C2PA text credential is never prose
        lines = masked.splitlines(keepends=True)
    fountain = genre.get("structural_classify") == "fountain"
    suppress = set(resolve_all(genre.get("suppress_categories", ())))
    roles = classify_fountain(lines) if fountain else None
    join = genre.get("unit", "sentence") != "line" and not fountain
    sc = _Scan(lines, extra_allow, genre, roles)
    for unit in units(lines, join=join, roles=roles):
        _scan_unit(sc, unit)
    _document_passes(sc, lines, suppress)
    doc = _cadence(sc, genre)
    high, medium, low = sc.high, sc.medium, sc.low
    if suppress:
        high = [f for f in high if f["category"] not in suppress]
        medium = [f for f in medium if f["category"] not in suppress]
        low = [f for f in low if f["category"] not in suppress]
    return high, medium, low, doc


def _cadence(sc, genre):
    doc = cadence_stats(" ".join(sc.prose))
    w = sc.words
    doc.update({"words": w,
                "adverb_rate": round(sc.adv / w * 100, 1) if w else 0,
                "passive_rate": round(sc.passive / w * 100, 1) if w else 0})
    # Verse is measured by the line. A punctuation-free stanza would otherwise
    # read as one long uniform "sentence", so the cadence signal is dropped.
    if genre.get("unit", "sentence") == "line":
        doc["uniform"] = False
        doc["repetitive_openers"] = False
    return doc
