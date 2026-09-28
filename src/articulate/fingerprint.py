#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.fingerprint -- the ruleset fingerprint a receipt pins, and the
closed set of category names. Standard library only.
"""
from .lexicon import (ADVERB, ANNOUNCEMENT, CLAIM_ANCHOR, EMOJI, EXISTENTIAL, EXPLETIVE, NEG,
                      NOMINAL, OPERATOR_AFTER, OPERATOR_BEFORE, PADDED_PREPOSITION,
                      PADDED_PURPOSE, PASSIVE, UNANCHORED_CLAIM, VAGUE_QUANT,
                      TOPIC_FRAME, TOPIC_FRAME_START, INTENSIFIER_BEFORE)
from .logical import ABBREVIATIONS
from .advisories import FRAGMENT_OPENER, PRONOUN_SUBJ, STOP4
from . import (aliases, cadence, citations, density, markup, quoting, rule_reasons, scan,
               sentence_notes)
from .gate import GATE_TIERS
from .rules_high import HIGH
from .rules_low import FICTION_SLOP, INJECTION, LOW, PHRASING_NOTES, REGISTER_JARGON
from .scan import MEDIUM

# 0.9.0: quotation pairing by direction, citation and sentence fixes, five rules
# scoped to their named pattern, four notes moved to LOW or the house pack, and
# the packs and project terms reading text with quotations blanked.
RULESET_SEMVER = "0.9.0"


def behavior_constants():
    """The scanner constants outside the rule tables that decide a finding, a
    cadence flag, a gate or a score. Read at call time, so a changed value is
    what gets hashed."""
    return {
        "SCAN_ALGO": scan.SCAN_ALGO,
        "SKIP_TABLE_SEP": scan.SKIP_TABLE_SEP,
        "RULE_GUARDS": sorted(scan.RULE_GUARDS),
        "DENSITY_MIN_WORDS": density.DENSITY_MIN_WORDS,
        "CADENCE_MIN_SENTENCES": cadence.CADENCE_MIN_SENTENCES,
        "CADENCE_MIN_WORDS": cadence.CADENCE_MIN_WORDS,
        "C2PA_MIN_SELECTORS": markup.C2PA_MIN_SELECTORS,
        "HOUSE_CATEGORIES": sorted(rule_reasons.HOUSE_CATEGORIES),
        "REASONS": sorted(rule_reasons.REASONS),
        "ALIASES": sorted(rule_reasons.ALIASES.items()),
        "PROFILE_KEY_ALIASES": sorted(aliases.PROFILE_KEY_ALIASES.items()),
        "CADENCE_CV_MAX": cadence.CADENCE_CV_MAX,
        "CADENCE_MEAN_MIN": cadence.CADENCE_MEAN_MIN,
        "OPENER_MIN_CONTENT": cadence.OPENER_MIN_CONTENT,
        "OPENER_RATIO_MAX": cadence.OPENER_RATIO_MAX,
    }


def _lexicon_parts():
    """The auxiliary regexes the scanner and advisories match with, then the
    sentence-start openers with their category and label, so a split or a
    relabel moves the fingerprint as a table change does."""
    parts = [f"X|{nm}|{rx.pattern}" for nm, rx in (
        ("EMOJI", EMOJI), ("VAGUE_QUANT", VAGUE_QUANT),
        ("EXPLETIVE", EXPLETIVE), ("EXISTENTIAL", EXISTENTIAL),
        ("NOMINAL", NOMINAL), ("NEG", NEG), ("PASSIVE", PASSIVE), ("ADVERB", ADVERB),
        ("FRAGMENT_OPENER", FRAGMENT_OPENER), ("PADDED_PURPOSE", PADDED_PURPOSE),
        ("UNANCHORED_CLAIM", UNANCHORED_CLAIM), ("CLAIM_ANCHOR", CLAIM_ANCHOR),
        ("ANNOUNCEMENT", ANNOUNCEMENT), ("PADDED_PREPOSITION", PADDED_PREPOSITION),
        ("TOPIC_FRAME", TOPIC_FRAME), ("TOPIC_FRAME_START", TOPIC_FRAME_START),
        ("INTENSIFIER_BEFORE", INTENSIFIER_BEFORE),
        ("OPERATOR_BEFORE", OPERATOR_BEFORE), ("OPERATOR_AFTER", OPERATOR_AFTER),
        ("AUTHORITY", citations.AUTHORITY), ("CITATION_MARKER", citations.CITATION_MARKER),
        ("OWN_EVIDENCE", citations.OWN_EVIDENCE), ("SPEAKER", quoting.SPEAKER),
        ("TEX_QUOTE", quoting.TEX_QUOTE), ("TEX_ENV", quoting.TEX_ENV),
        ("TEXTTT", quoting.TEXTTT), ("VERB_OPEN", quoting.VERB_OPEN),
        ("ABBREVIATIONS", ABBREVIATIONS))]
    parts.append(f"L|unsupported-authority|{citations.LABEL}")
    parts += _reading_parts()
    return parts + [f"S|{cat}|{label}|{rx.pattern}" for cat, label, rx in
                    sentence_notes.OPENERS + sentence_notes.PHRASE_NOTES]


# Every constant that decides which text the blocking rules read: the URL, tag,
# code, TeX and quotation masks, fenced lines, sentence ends and the citation
# abbreviations, which lines are headings and list items, and the quotation-mark
# pairing table (SCAN_ALGO 7). Read by module and name at call time, so an edited
# pattern moves the fingerprint (review C-6).
READING_PATTERNS = (
    ("masking", "URL_PATTERN"), ("masking", "TAG_PATTERN"), ("masking", "QUOTED_PATTERN"),
    ("markup", "INLINE_CODE"), ("markup", "TEX"), ("markup", "FENCE"),
    ("logical", "SENTENCE_END"), ("logical", "ABBREVIATIONS"),
    ("logical", "ABBREV_BEFORE_NUMBER"), ("logical", "ABBREV_BEFORE_NAME"),
    ("logical", "ABBREV_IN_PARENS"), ("logical", "_ORDERED"),
    ("lexicon", "HEADING"), ("lexicon", "BULLET"),
    ("quoting", "CSQUOTES"), ("quoting", "_TEX_COMMENT"),
)


def _reading_parts():
    import importlib
    parts = []
    for mod, name in READING_PATTERNS:
        value = getattr(importlib.import_module(f".{mod}", __package__), name)
        parts.append(f"R|{mod}.{name}|{getattr(value, 'pattern', value)}")
    parts.append(f"R|quoting.CSQUOTES_ARGS|{sorted(quoting.CSQUOTES_ARGS.items())}")
    from . import quotemarks
    return parts + quotemarks.table_parts()


def ruleset_fingerprint():
    """A stable hash of the detection ruleset. A receipt pins this, so a verdict
    can only be re-derived under the exact rules that produced it; a rule change
    moves the fingerprint and a replay reads Unverifiable and never silently
    disagreeing. This is what makes the verdict re-derivable and the issuer's
    identity non-load-bearing: anyone with the same text and fingerprint recomputes
    the same findings."""
    import hashlib
    # Sort every set/frozenset's contents: Python hash randomization makes their
    # repr order vary per process, which would make the fingerprint non-reproducible.
    gate = [(k, sorted(v)) for k, v in sorted(GATE_TIERS.items())]
    parts = [f"semver={RULESET_SEMVER}", f"gate={gate}"]
    for name, lst in (("HIGH", HIGH), ("MEDIUM", MEDIUM),
                      ("REGISTER_JARGON", REGISTER_JARGON), ("LOW", LOW),
                      ("PHRASING_NOTES", PHRASING_NOTES), ("FICTION_SLOP", FICTION_SLOP)):
        for cat, label, rx in lst:
            parts.append(f"{name}|{cat}|{label}|{rx.pattern}")
    parts += _lexicon_parts()
    parts.append(f"PRONOUN_SUBJ={sorted(PRONOUN_SUBJ)}|STOP4={sorted(STOP4)}")
    parts.append(f"BEHAVIOR={sorted(behavior_constants().items())}")
    # A receipt records a profile or mode name and re-derives by loading it, so the
    # profile, genre, and mode definitions are all part of the ruleset. Fold them in
    # (sorted JSON) so that editing a profile's keep-list or gate level, a genre field, or
    # a mode's gate_promote or gate level moves the fingerprint and an old receipt reads
    # Unverifiable, never a misleading Drift. A mode's gate_promote drives check_text's
    # gate directly, and a receipt can name a mode, so it must be pinned. INJECTION
    # is deliberately excluded: it never enters a check_text verdict.
    import json as _json

    from . import genres as _genres
    from . import modes as _modes
    from . import profiles as _profiles

    def _stable(o):
        # Sets have no stable JSON order across processes; sort them. Fail loud on
        # any other non-serializable type and never str() it unstably.
        if isinstance(o, (set, frozenset)):
            return sorted(o)
        raise TypeError(f"non-serializable ruleset value: {type(o).__name__}")

    from . import rules_ext as _rules_ext
    parts.extend(_rules_ext.fingerprint_parts())
    parts.append("PROFILES=" + _json.dumps(_profiles.PROFILES, sort_keys=True, default=_stable))
    parts.append("GENRES=" + _json.dumps(_genres.GENRES, sort_keys=True, default=_stable))
    parts.append("MODES=" + _json.dumps(_modes.MODES, sort_keys=True, default=_stable))
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
    return f"sha256:{digest[:16]}"


def known_categories():
    """Every category name the detector can emit, so a mode's gate_promote can be
    validated (fail closed on a typo) the way the flywheel `hard` tuple was."""
    cats = {"emoji", "emoji-structure", "em-dash", "vague-quantifier",
            "expletive-opener", "nominalization", "contrast-pair", "anaphora",
            "padded-purpose", "unanchored-claim", "existential-opener",
            "announcement", "padded-preposition", "unsupported-authority",
            "fragment-opener", "header-reflex", "list-reflex", "bold-density",
            "ngram-repetition", "paragraph-uniformity", "hedge-cluster"}
    for lst in (HIGH, MEDIUM, REGISTER_JARGON, LOW, PHRASING_NOTES, FICTION_SLOP,
                INJECTION):
        for cat, _label, _rx in lst:
            cats.add(cat)
    from . import rules_ext
    return frozenset(cats | rules_ext.categories())
