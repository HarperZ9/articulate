#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.fingerprint -- the ruleset fingerprint a receipt pins, and the
closed set of category names. Standard library only.
"""
from .lexicon import (ADVERB, EMOJI, EXPLETIVE, NEG, NOMINAL, PASSIVE, SOFT,
                      VAGUE_QUANT)
from .advisories import FRAGMENT_OPENER, PRONOUN_SUBJ, STOP4
from . import aliases, cadence, density, markup, rule_reasons, scan
from .gate import GATE_TIERS
from .rules_high import HIGH
from .rules_low import FICTION_SLOP, INJECTION, LOW, REGISTER_JARGON
from .scan import MEDIUM

RULESET_SEMVER = "0.7.0"


def behavior_constants():
    """The scanner constants outside the rule tables that decide a finding, a
    cadence flag, a gate or a score. Read at call time, so a changed value is
    what gets hashed."""
    return {
        "SCAN_ALGO": scan.SCAN_ALGO,
        "SKIP_TABLE_SEP": scan.SKIP_TABLE_SEP,
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
                      ("FICTION_SLOP", FICTION_SLOP)):
        for cat, label, rx in lst:
            parts.append(f"{name}|{cat}|{label}|{rx.pattern}")
    for nm, rx in (("EMOJI", EMOJI), ("VAGUE_QUANT", VAGUE_QUANT),
                   ("EXPLETIVE", EXPLETIVE), ("NOMINAL", NOMINAL), ("NEG", NEG),
                   ("SOFT", SOFT), ("PASSIVE", PASSIVE), ("ADVERB", ADVERB),
                   ("FRAGMENT_OPENER", FRAGMENT_OPENER)):
        parts.append(f"X|{nm}|{rx.pattern}")
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
            "fragment-opener", "header-reflex", "list-reflex", "bold-density",
            "ngram-repetition", "paragraph-uniformity", "hedge-cluster"}
    for lst in (HIGH, MEDIUM, REGISTER_JARGON, LOW, FICTION_SLOP, INJECTION):
        for cat, _label, _rx in lst:
            cats.add(cat)
    return frozenset(cats)
