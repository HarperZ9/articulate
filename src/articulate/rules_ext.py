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
defaults are part of the ruleset fingerprint. Standard library only.
"""
from __future__ import annotations

import re

from . import detector, invariants, terms

SEMVER = "1.0.0"
# name -> module. A pack module exposes NAME, CATEGORIES, OPTIONS (defaults),
# scan(text, prose, options, make) -> {"HIGH": [...], "MEDIUM": [...],
# "LOW": [...]}, and fingerprint() -> list of strings.
PACKS = {}


_TAG = re.compile(r"<[^<>\n]{1,400}>")


def mask_line(line):
    """Mask code, URLs and emails, tags, and TeX with equal-length spaces. The
    URL and tag patterns are bounded, so a long line of dotted tokens or of
    unclosed angle brackets stays linear."""
    for rx in (detector.INLINE_CODE, invariants.URL, _TAG, detector.TEX):
        line = rx.sub(detector._blank, line)
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
        if detector.FENCE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if in_fm:
            if i > 1 and raw.strip() == "---":
                in_fm = False
            continue
        yield i, start, raw, mask_line(raw)


def scan(text, lines, profile):
    """Findings by tier from the project terminology and the profile's packs."""
    found = {"HIGH": [], "MEDIUM": [], "LOW": []}
    term = profile.get("terminology")
    if term:
        for tier, items in terms.scan(prose_lines(lines), term, detector._mk).items():
            found[tier].extend(items)
    options = profile.get("options") or {}
    for name in profile.get("rule_packs", ()):
        pack = PACKS[name]
        opts = dict(pack.OPTIONS, **options.get(name, {}))
        for tier, items in pack.scan(text, list(prose_lines(lines)), opts,
                                     detector._mk).items():
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
    parts = [f"RULES_EXT={SEMVER}", f"TERMS={terms._KEYS!r}|{sorted(terms.SEVERITIES)}"]
    for name in sorted(PACKS):
        parts.append(f"PACK|{name}|{sorted(PACKS[name].OPTIONS.items())}")
        parts.extend(f"PACK|{name}|{p}" for p in PACKS[name].fingerprint())
    return parts
