"""Rule fixtures for the PR 9 decisions on reader cost (decisions 2 and 3).

A pattern whose cost depends on register, or that style authorities accept in
some uses, reports without blocking. A report-only note with no reliable reader
cost moves to the house pack. Each human control line below is ordinary writing
that must not block under any profile.

These tests guard the decisions against regression. They measure nothing about
fairness; the measured effect lives in the fairness receipts.
"""
import pytest

import articulate
from articulate import fairness, rule_reasons

EVERY = tuple(fairness.bound_profiles()) + tuple(fairness.house_profiles())


def _r(text, name):
    return articulate.check_text(text if text.endswith("\n") else text + "\n",
                                 profile=fairness.load_any(name))


def _low(r):
    return {f["category"] for f in r["low"]}


def _all(r):
    return {f["category"] for t in ("high", "medium", "low") for f in r[t]}


# --- decision 2: `in order to` ---------------------------------------------- #

PURPOSE_LINES = (
    "We sampled twice in order to separate the two effects.",
    "In order to reach the station, take the second bus.",
    "The clinic stays open late in order to serve shift workers.",
)


@pytest.mark.parametrize("line", PURPOSE_LINES)
def test_in_order_to_never_blocks(line):
    for name in EVERY:
        r = _r(line, name)
        assert r["gate"] == "ok", (name, line)


def test_in_order_to_is_a_low_padded_purpose_note():
    r = _r(PURPOSE_LINES[0], "flavored")
    assert "padded-purpose" in _low(r)
    assert "wordiness" not in _all(r)


def test_the_rest_of_wordiness_still_blocks_under_essay():
    r = _r("The trial ended early due to the fact that funding ran out.", "essay")
    assert r["gate"] == "blocked"
    assert "wordiness" in {f["category"] for f in r["medium"]}


# --- decision 2: `state of the art` ----------------------------------------- #

UNANCHORED = (
    "Our parser is state of the art.",
    "They built a state-of-the-art lab for the students.",
)
ANCHORED = (
    "The parser reaches the state of the art on the 2019 benchmark.",
    "The method matches the state of the art (Wang et al., 2019).",
    "It is state of the art, with 91.2 F1 on the test set.",
    "This result sets the state of the art [3].",
)


@pytest.mark.parametrize("line", UNANCHORED + ANCHORED)
def test_state_of_the_art_never_blocks(line):
    for name in EVERY:
        r = _r(line, name)
        assert r["gate"] == "ok", (name, line)
        assert "marketing" not in _all(r), (name, line)


@pytest.mark.parametrize("line", UNANCHORED)
def test_state_of_the_art_without_an_anchor_is_a_low_note(line):
    assert "unanchored-claim" in _low(_r(line, "flavored"))


@pytest.mark.parametrize("line", ANCHORED)
def test_state_of_the_art_with_a_number_year_or_citation_raises_nothing(line):
    assert "unanchored-claim" not in _all(_r(line, "flavored"))


def test_the_anchor_is_read_per_sentence():
    r = _r("Our parser is state of the art. It scored 91 on the test.", "flavored")
    assert "unanchored-claim" in _low(r)


def test_other_marketing_superlatives_still_block_under_essay():
    r = _r("We hired a world-class team for the survey.", "essay")
    assert r["gate"] == "blocked"
    assert "marketing" in {f["category"] for f in r["medium"]}


def test_the_new_notes_carry_reader_cost_reasons():
    purpose = rule_reasons.reason_for("padded-purpose")
    claim = rule_reasons.reason_for("unanchored-claim")
    assert purpose and "usually 'to' does the same work" in purpose[0]
    assert claim and "name the comparison" in claim[0].lower()
    wordiness = rule_reasons.reason_for("wordiness")[0]
    assert "in order to" not in wordiness
    marketing = rule_reasons.reason_for("marketing")[0]
    assert "state of the art" not in marketing
