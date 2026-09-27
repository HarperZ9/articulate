"""The domain packs and project terms read a paragraph as one line, as the core
checks do, so a line break inside a phrase changes no finding.

Main reads every paragraph as a logical line, and the fairness harness gates on
it (G4: blocking findings are identical after a rewrap to one sentence per line
and after a hard wrap at 60 columns). `normative-spec` is a profile a path can
assign, so its BCP 14 rules fall under that gate. Each case below states a
phrase once unwrapped and once with a line break inside it; the findings must
match. A control splits the phrase across two paragraphs, where it must not
match. The UI-string pack reads one string per line by design and is left out.
"""
from collections import Counter

import pytest

import articulate
from articulate import fairness, profiles, project

CASES = [
    ("normative-spec", "Clients SHOULD not retry after a timeout.", "bcp14-mixed-case"),
    ("normative-spec", "Servers MAY NOT cache the reply for later use.", "bcp14-may-not"),
    ("plain-language", "Press the key in order to start the pump.", "plain-wordy"),
    ("controlled-english", "The tool works out of the box on most hosts.", "controlled-idiom"),
    ("controlled-english", "Run the test to find out which host failed.",
     "controlled-phrasal-verb"),
]


def _found(text, prof, cat):
    r = articulate.check_text(text, profile=prof)
    return Counter((f["tier"], f["rule_id"]) for t in ("high", "medium", "low")
                   for f in r[t] if f["category"] == cat)


def _break_inside(sentence, phrase_words):
    """The sentence with a line break between the phrase's first two words."""
    first, second = phrase_words[:2]
    i = sentence.index(first + " " + second)
    j = i + len(first)
    return sentence[:j] + "\n" + sentence[j + 1:]


_PHRASES = {"bcp14-mixed-case": ("SHOULD", "not"), "bcp14-may-not": ("MAY", "NOT"),
            "plain-wordy": ("in", "order"), "controlled-idiom": ("out", "of"),
            "controlled-phrasal-verb": ("find", "out")}


@pytest.mark.parametrize("name,sentence,cat", CASES, ids=[c[2] for c in CASES])
def test_a_line_break_inside_a_phrase_changes_no_finding(name, sentence, cat):
    prof = profiles.load(name)
    flat = sentence + "\n"
    wrapped = _break_inside(sentence, _PHRASES[cat]) + "\n"
    assert _found(flat, prof, cat), (cat, "premise: the phrase fires unwrapped")
    assert _found(wrapped, prof, cat) == _found(flat, prof, cat)
    # Control: across a paragraph break the words are no longer one phrase.
    split = wrapped.replace("\n", "\n\n", 1)
    assert not _found(split, prof, cat)


def test_a_project_term_that_wraps_is_still_found():
    term = {"preferred": [{"use": "sign in", "instead_of": ["log in"]}]}
    prof = project.apply_payload(profiles.load("flavored"), {"terminology": term})
    flat = "Users log in with a key.\n"
    wrapped = "Users log\nin with a key.\n"
    assert _found(flat, prof, "terminology")
    assert _found(wrapped, prof, "terminology") == _found(flat, prof, "terminology")
    assert not _found("Users log\n\nin with a key.\n", prof, "terminology")


def _hm(text, prof):
    r = articulate.check_text(text, profile=prof)
    return Counter((f["tier"], f["rule_id"]) for t in ("high", "medium") for f in r[t])


def _split_by_hardwrap(phrase):
    """A one-line paragraph whose 60-column hard wrap breaks inside `phrase`."""
    first, rest = phrase.split(" ", 1)
    for n in range(60):
        para = "The client " + "and " * n + f"{phrase} retry the call after a timeout."
        if f"{first}\n{rest}" in fairness.hardwrap(para):
            return para
    raise AssertionError(f"no padding splits {phrase!r}")


@pytest.mark.parametrize("phrase", ["SHOULD not", "MAY NOT"])
def test_normative_spec_findings_hold_under_the_g4_rewraps(phrase):
    text = _split_by_hardwrap(phrase) + "\n"
    prof = profiles.load("normative-spec")
    base = _hm(text, prof)
    assert base, "premise: the paragraph has a blocking-tier finding"
    for variant in (fairness.rewrap(text), fairness.hardwrap(text)):
        assert _hm(variant, prof) == base, variant
