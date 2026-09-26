"""The ruleset fingerprint must move when scanner behavior moves.

Before this, the fingerprint hashed the rule tables and a few regexes. The
cadence floors, the texture weights, the word floor, the table-row skip and the
scanner's control flow sat outside it, so a receipt issued before a change to
any of them still replayed to Match. Each constant below is folded in, and the
golden findings test catches a control-flow change that no constant names.

These tests guard the replay contract. They measure nothing about fairness.
"""
import pytest

from articulate import cadence, detector, fingerprint, gate, scan

import test_golden_findings as golden

CONSTANTS = [
    (cadence, "CADENCE_MIN_SENTENCES", 3),
    (cadence, "CADENCE_CV_MAX", 0.9),
    (cadence, "CADENCE_MEAN_MIN", 2),
    (cadence, "OPENER_MIN_CONTENT", 2),
    (cadence, "OPENER_RATIO_MAX", 0.99),
    (gate, "MIN_WORDS_FOR_VERDICT", 3),
    (scan, "SKIP_TABLE_SEP", False),
    (scan, "SCAN_ALGO", 999),
]


@pytest.mark.parametrize("module,name,value", CONSTANTS)
def test_each_behavior_constant_moves_the_fingerprint(monkeypatch, module, name, value):
    before = detector.ruleset_fingerprint()
    monkeypatch.setattr(module, name, value)
    assert detector.ruleset_fingerprint() != before, name


def test_a_texture_weight_moves_the_fingerprint(monkeypatch):
    before = detector.ruleset_fingerprint()
    monkeypatch.setitem(cadence.TEXTURE_WEIGHTS, "uniform", 99)
    assert detector.ruleset_fingerprint() != before


def test_the_fingerprint_lists_every_behavior_constant():
    names = set(fingerprint.behavior_constants())
    for _module, name, _value in CONSTANTS:
        assert name in names, name


def test_a_constant_change_with_the_fingerprint_held_fails_the_golden_pin(monkeypatch):
    # The mutation check: hold the fingerprint at its pinned value and change
    # behavior underneath it. The golden digest must notice.
    pinned = detector.ruleset_fingerprint()
    base = golden.findings_digest()
    monkeypatch.setattr(cadence, "CADENCE_MIN_SENTENCES", 2)
    monkeypatch.setattr(cadence, "CADENCE_MEAN_MIN", 1)
    monkeypatch.setattr(detector, "ruleset_fingerprint", lambda: pinned)
    assert golden.findings_digest() != base
