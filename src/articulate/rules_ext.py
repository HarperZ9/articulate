#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
articulate.rules_ext -- rules that run after the core scan.

The core detector reads every document with one ruleset. Two kinds of rules
depend on where the document lives or what it is:

  project terminology  banned and preferred terms from `.articulate.json`
                       (articulate.terms).
  domain rule packs    deterministic rules for one kind of writing, switched on
                       by a profile's `rule_packs` field.

`scan(text, lines, profile)` returns their findings by tier, and check_text adds
them before it computes the gate, so they show in check, SARIF, the LSP server,
receipts, and per-span verdicts like any other finding. Their patterns and
defaults are part of the ruleset fingerprint.

A quotation is its source's words, so both kinds read the prose with every
quotation blanked, found as the core phrasing rules find it (quotation_columns).
The UI-string pack is the exception: in a string file the quotes delimit the
interface text it checks (READS_QUOTES). Standard library only.
"""
from __future__ import annotations

import re

from . import invariants, masking, quoting, terms
from .logical import line_kinds, units
from .markup import FENCE, TEX, _blank, _mk, strip_markup

# 1.1.0: the packs and project terms read a paragraph as one line (pack_util
# .paragraph_hits), as the core checks read logical lines.
# 1.2.0 (ruleset 0.9.0): they read the prose with quotations blanked.
SEMVER = "1.2.0"
# name -> module. A pack module exposes NAME, CATEGORIES, OPTIONS (defaults),
# scan(text, prose, options, make) -> {"HIGH": [...], "MEDIUM": [...],
# "LOW": [...]}, and fingerprint() -> list of strings. READS_QUOTES = True
# gives it the prose with quotations kept. WHOLE_PROSE = True also passes
# `whole=`, the prose with quotations kept, for a fact about the document (the
# BCP 14 declaration) that a quotation can state.
PACKS = {}


_TAG = re.compile(r"<[^<>\n]{1,400}>")


def mask_line(line):
    """Mask code, URLs and emails, tags, and TeX with equal-length spaces. The
    URL and tag patterns are bounded, so a long line of dotted tokens or of
    unclosed angle brackets stays linear."""
    line = masking.mask_code(line)
    for rx in (invariants.URL, _TAG, TEX):
        line = rx.sub(_blank, line)
    return line


def prose_lines(lines):
    """(line_no, offset, raw, masked) for each prose line: fenced code and YAML
    frontmatter are skipped, and code, URLs, tags, and TeX are masked with
    equal-length spaces so offsets stay valid in the raw line."""
    in_fence = False
    in_fm = bool(lines) and lines[0].strip() == "---"
    off = 0
    for i, raw in enumerate(lines, 1):
        start, off = off, off + len(raw)
        if FENCE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if in_fm:
            if i > 1 and raw.strip() == "---":
                in_fm = False
            continue
        yield i, start, raw, mask_line(raw)


def quotation_columns(lines):
    """{line number: [(start, end), ...]}: the quoted text on each line, found
    as the core phrasing rules find it. Direct quotations are paired over each
    paragraph read as one logical line (articulate.quotemarks, LaTeX ``...'',
    csquotes), so a quotation wrapped inside its paragraph is one quotation.
    Markdown block quote lines and the lines of a LaTeX quote environment are
    quoted whole."""
    starts = [0]
    for raw in lines:
        starts.append(starts[-1] + len(raw))
    block, _shown = quoting.quoted_lines(lines, line_kinds(lines))
    cols = {n: [(0, len(lines[n - 1]))] for n in block}
    for u in units(lines):
        for s, e in quoting.direct_spans(strip_markup(u.text), u.text):
            for log_start, doc_start, line_no, length in u.pieces:
                lo, hi = max(s, log_start), min(e, log_start + length)
                if lo < hi:
                    col = doc_start - starts[line_no - 1] - log_start
                    cols.setdefault(line_no, []).append((col + lo, col + hi))
    return cols


def _unquoted(prose, cols):
    """The prose records with every quoted column blanked. A newline stays."""
    out = []
    for line_no, off, raw, masked in prose:
        spans = cols.get(line_no)
        if spans:
            chars = list(masked)
            for s, e in spans:
                for k in range(s, min(e, len(chars))):
                    if chars[k] not in "\r\n":
                        chars[k] = " "
            masked = "".join(chars)
        out.append((line_no, off, raw, masked))
    return out


def scan(text, lines, profile):
    """Findings by tier from the project terminology and the profile's packs."""
    found = {"HIGH": [], "MEDIUM": [], "LOW": []}
    term = profile.get("terminology")
    names = profile.get("rule_packs", ())
    if not term and not names:
        return found["HIGH"], found["MEDIUM"], found["LOW"]
    whole = list(prose_lines(lines))
    prose = _unquoted(whole, quotation_columns(lines))
    if term:
        for tier, items in terms.scan(prose, term, _mk).items():
            found[tier].extend(items)
    options = profile.get("options") or {}
    for name in names:
        pack = PACKS[name]
        opts = dict(pack.OPTIONS, **options.get(name, {}))
        reads = whole if getattr(pack, "READS_QUOTES", False) else prose
        extra = {"whole": whole} if getattr(pack, "WHOLE_PROSE", False) else {}
        for tier, items in pack.scan(text, list(reads), opts, _mk, **extra).items():
            found[tier].extend(items)
    return found["HIGH"], found["MEDIUM"], found["LOW"]


def categories():
    cats = {"terminology"}
    for pack in PACKS.values():
        cats |= set(pack.CATEGORIES)
    return cats


def option_defaults():
    return {name: dict(pack.OPTIONS) for name, pack in PACKS.items() if pack.OPTIONS}


def option_choices():
    """{pack: {option: allowed values}} for options that take a fixed set."""
    return {name: dict(getattr(pack, "CHOICES", {})) for name, pack in PACKS.items()}


def _register():
    from . import pack_bcp14, pack_controlled, pack_plain, pack_review, pack_ux
    for pack in (pack_ux, pack_review, pack_plain, pack_bcp14, pack_controlled):
        PACKS[pack.NAME] = pack


_register()


def fingerprint_parts():
    """The strings that pin these rules in the ruleset fingerprint."""
    # Sort every set: a set's repr follows the per-process hash seed, and the
    # fingerprint must be the same in every process that recomputes it.
    keys = sorted((kind, sorted(names)) for kind, names in terms._KEYS.items())
    parts = [f"RULES_EXT={SEMVER}", f"TERMS={keys!r}|{sorted(terms.SEVERITIES)}"]
    for name in sorted(PACKS):
        pack = PACKS[name]
        parts.append(f"PACK|{name}|{sorted(pack.OPTIONS.items())}")
        parts.append(f"PACK|{name}|quotes={bool(getattr(pack, 'READS_QUOTES', False))}"
                     f"|whole={bool(getattr(pack, 'WHOLE_PROSE', False))}")
        parts.extend(f"PACK|{name}|{p}" for p in PACKS[name].fingerprint())
    return parts
