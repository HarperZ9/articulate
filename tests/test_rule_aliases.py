"""Rule ids that carried an origin word were renamed. The old ids stay readable
for one minor version wherever a user names a category: a mode's gate_promote,
a genre's suppress_categories and a profile dict passed to check_text.

These tests guard the alias contract. They measure nothing about fairness.
"""
import articulate
from articulate import detector, modes, rule_reasons

OLD_TO_NEW = {
    "assistant-residue": "chat-interface-text",
    "assistant-closer": "closing-boilerplate",
    "email-tell": "email-stock-phrase",
    "blog-tell": "blog-stock-phrase",
    "fiction-slop-lexicon": "fiction-stock-phrase",
    "register-word": "inflated-word",
    "filler-intensifier": "intensifier",
}


def test_every_old_id_resolves_to_a_known_new_id():
    assert rule_reasons.ALIASES == OLD_TO_NEW
    known = detector.known_categories()
    for old, new in OLD_TO_NEW.items():
        assert rule_reasons.resolve_category(old) == new
        assert new in known and old not in known


def test_gate_promote_reads_an_old_id():
    prof = {"gate_level": "flavored", "gate_promote": ("register-word",)}
    r = articulate.check_text("We delve into the data.\n", profile=prof)
    assert r["gate"] == "blocked"


def test_suppress_categories_reads_an_old_id():
    prof = {"gate_level": "flavored", "suppress_categories": ("filler-intensifier",)}
    r = articulate.check_text("It was really late.\n", profile=prof)
    assert not [f for t in ("high", "medium", "low") for f in r[t]
                if f["category"] == "intensifier"]


def test_a_mode_may_name_an_old_id(monkeypatch):
    changed = dict(modes.MODES)
    changed["academic/argue"] = {**changed["academic/argue"],
                                 "gate_promote": ("unsupported-authority", "assistant-closer")}
    monkeypatch.setattr(modes, "MODES", changed)
    assert "closing-boilerplate" in modes.load("academic/argue")["gate_promote"]
