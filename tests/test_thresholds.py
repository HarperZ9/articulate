"""N3: no verdict about the text, and no word floor.

Before 0.7.0 a result carried `verdict` (flagged, clean, unverifiable) beside
the gate, and a 30-word floor made a short text read "unverifiable" when it had
no finding. "clean" meant clean writing, a claim the tool cannot make. Now the
gate (ok or blocked) is the only pass-or-block signal, `findings` says only
whether any HIGH or MEDIUM finding exists, and `words` is reported as a count.
"""
import articulate
from articulate import profiles, receipt

SHORT_CLEAN = "Thanks for the update. I will review it and reply tomorrow.\n"
SHORT_DEVICE = "We leverage synergy to unlock value.\n"
ENUMERATION = "Firstly, the survey is short. Secondly, it is cheap.\n"


def _v(text, prof="flavored"):
    return articulate.check_text(text, profile=profiles.load(prof))


def test_no_result_carries_a_verdict_or_a_floor():
    r = _v(SHORT_CLEAN)
    assert "verdict" not in r and "sufficient" not in r
    assert r["findings"] == "no_findings" and r["gate"] == "ok"
    assert r["words"] == 11


def test_a_short_finding_is_a_finding():
    r = _v(SHORT_DEVICE, "house")
    assert r["findings"] == "has_findings" and r["gate"] == "blocked"


def test_findings_and_gate_can_differ():
    # A MEDIUM finding that the profile does not gate: findings exist, gate ok.
    r = _v("It is important to note that the survey ran twice.\n", "flavored")
    assert r["findings"] == "has_findings" and r["gate"] == "ok"
    # The house-style enumeration reports at LOW outside the house pack.
    r2 = _v(ENUMERATION, "flavored")
    assert r2["findings"] == "no_findings" and r2["gate"] == "ok"


def test_a_short_receipt_replays_to_match():
    for text in (SHORT_CLEAN, SHORT_DEVICE):
        rec = receipt.make_receipt(text, "house")
        assert "verdict" not in rec
        assert receipt.verify_receipt(rec, text)[0] == "Match"
