#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.fingerprint -- the ruleset fingerprint a receipt pins, and the
closed set of category names. Standard library only.
"""
from .lexicon import (ADVERB, EMOJI, EXPLETIVE, NEG, NOMINAL, PASSIVE, SOFT,
                      VAGUE_QUANT)
from .advisories import FRAGMENT_OPENER, PRONOUN_SUBJ, STOP4
from .gate import GATE_TIERS
from .rules_high import HIGH
from .rules_low import FICTION_SLOP, INJECTION, LOW, REGISTER_JARGON
from .scan import MEDIUM

RULESET_SEMVER = "0.5.1"


def ruleset_fingerprint():
    """A stable hash of the detection ruleset. A receipt pins this, so a verdict
    can only be re-derived under the exact rules that produced it; a rule change
    moves the fingerprint and a replay reads Unverifiable rather than silently
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
    # A receipt records a profile or mode name and re-derives by loading it, so the
    # profile, genre, and mode definitions are all part of the ruleset. Fold them in
    # (sorted JSON) so that editing a profile's keep-list or slop, a genre field, or
    # a mode's gate_promote/slop moves the fingerprint and an old receipt reads
    # Unverifiable, not a misleading Drift. A mode's gate_promote drives check_text's
    # gate directly, and a receipt can name a mode, so it must be pinned. INJECTION
    # is deliberately excluded: it never enters a check_text verdict.
    import json as _json

    from . import genres as _genres
    from . import modes as _modes
    from . import profiles as _profiles

    def _stable(o):
        # Sets have no stable JSON order across processes; sort them. Fail loud on
        # any other non-serializable type rather than str()-ing it unstably.
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
    cats = {"emoji", "em-dash", "vague-quantifier", "expletive-opener",
            "nominalization", "contrast-pair"}
    for lst in (HIGH, MEDIUM, REGISTER_JARGON, LOW, FICTION_SLOP, INJECTION):
        for cat, _label, _rx in lst:
            cats.add(cat)
    return frozenset(cats)
