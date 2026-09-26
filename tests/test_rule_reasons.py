"""Every rule that can block a writer who never chose a house style carries a
reader-cost reason and a source. How often a model produces a pattern is never a
reason. A rule with no such reason lives in the house pack.

A test can check that a reason exists and is worded without an origin claim. It
cannot check that the reason is true. A second reader, neither the maintainer nor
a model, reviews each reason before a release relies on it.
"""
from articulate import detector, modes, rule_reasons

GATE_CAPABLE_EXTRA = {"em-dash", "emoji-structure", "contrast-pair"}


def _gate_capable():
    cats = set(GATE_CAPABLE_EXTRA)
    for table in (detector.HIGH, detector.MEDIUM, detector.REGISTER_JARGON):
        cats |= {cat for cat, _label, _rx in table}
    return cats


def test_every_gate_capable_rule_is_house_or_reasoned():
    missing = {c for c in _gate_capable()
               if not rule_reasons.is_house(c) and rule_reasons.reason_for(c) is None}
    assert not missing, sorted(missing)


def test_house_and_reasoned_do_not_overlap():
    assert not (set(rule_reasons.REASONS) & rule_reasons.HOUSE_CATEGORIES)


def test_every_reason_has_a_sentence_and_a_source():
    for cat, (reason, source) in rule_reasons.REASONS.items():
        assert len(reason.split()) >= 8 and reason.endswith("."), cat
        assert source.strip(), cat


def test_no_reason_is_a_model_frequency_reason():
    for cat, (reason, source) in rule_reasons.REASONS.items():
        low = f" {reason.lower()} "
        for word in rule_reasons.ORIGIN_WORDS:
            assert word not in low, (cat, word)


def test_every_reasoned_category_exists():
    known = detector.known_categories()
    assert set(rule_reasons.REASONS) <= known
    assert rule_reasons.HOUSE_CATEGORIES <= known


def test_no_mode_promotes_a_house_category():
    for mid in modes.names():
        m = modes.load(mid)
        if not m.get("house"):
            assert not (set(m["gate_promote"]) & rule_reasons.HOUSE_CATEGORIES), mid


def test_no_mode_requires_a_cadence_fix():
    # Sentence-length variance is what perplexity detectors read as burstiness.
    # No editing target may push it.
    for mid in modes.names():
        assert "cadence-uniform" not in modes.load(mid)["editor"]["require_fix"], mid
