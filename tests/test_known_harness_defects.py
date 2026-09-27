"""Defects in what the fingerprint covers and how a fairness receipt keys
notes, found in review of the 0.6.0 candidate and fixed in ruleset 0.9.0.

- The fingerprint left out patterns that decide which text the blocking rules
  read, so an edit to one changed blocking and still passed the release check
  as "ruleset unchanged". It now hashes each of them, and the quotation-mark
  table, by module and name at call time.
- A fairness receipt keyed the paragraph-uniformity and nominalization notes by
  rule ids that carry a per-document count, which split one note across keys
  and recorded one essay's paragraph count. They are keyed by category now.

Each defect test was strict xfail until the fix (fairness/PREREG.md, amendment
of 27 September 2026). The tests now guard the fix; the controls are unchanged.
"""
import re

import pytest

from articulate import (fairness, fingerprint, lexicon, logical, markup, masking,
                        quotemarks, quoting)


# --- the fingerprint covers the constants that decide blocking -------------- #

# Each decides which text the blocking rules read: quote, URL, tag, code and
# LaTeX masks, fenced lines, sentence starts, and which lines join a paragraph.
BLOCKING_PATTERNS = [
    (masking, "QUOTED_PATTERN"), (masking, "URL_PATTERN"), (masking, "TAG_PATTERN"),
    (markup, "INLINE_CODE"), (markup, "TEX"), (markup, "FENCE"),
    (logical, "SENTENCE_END"), (lexicon, "HEADING"), (lexicon, "BULLET"),
    # added with ruleset 0.9.0 (SCAN_ALGO 7)
    (logical, "ABBREVIATIONS"), (logical, "ABBREV_BEFORE_NUMBER"),
    (logical, "ABBREV_BEFORE_NAME"), (logical, "ABBREV_IN_PARENS"),
    (quoting, "CSQUOTES"), (quoting, "_TEX_COMMENT"),
]


def _edited(value):
    """The same pattern with a regex comment appended: any edit of the source
    changes the pattern string this way, whatever it does to matching."""
    if isinstance(value, str):
        return value + "(?#edited)"
    return re.compile(value.pattern + "(?#edited)", value.flags)


def test_control_a_covered_pattern_moves_the_fingerprint(monkeypatch):
    before = fingerprint.ruleset_fingerprint()
    monkeypatch.setattr(lexicon, "PADDED_PURPOSE", _edited(lexicon.PADDED_PURPOSE))
    monkeypatch.setattr(fingerprint, "PADDED_PURPOSE", lexicon.PADDED_PURPOSE)
    assert fingerprint.ruleset_fingerprint() != before


@pytest.mark.parametrize("module,name", BLOCKING_PATTERNS,
                         ids=[f"{m.__name__.rsplit('.', 1)[-1]}.{n}" for m, n in BLOCKING_PATTERNS])
def test_every_pattern_that_decides_blocking_moves_the_fingerprint(monkeypatch, module, name):
    before = fingerprint.ruleset_fingerprint()
    monkeypatch.setattr(module, name, _edited(getattr(module, name)))
    assert fingerprint.ruleset_fingerprint() != before, name


# --- a fairness receipt keys two notes by a count ---------------------------- #

def _finding(category, rule_id):
    return {"tier": "LOW", "category": category, "rule_id": rule_id}


def test_control_the_text_quoting_notes_are_keyed_by_category():
    f = _finding("anaphora", "anaphora/4-consecutive-sentences-open-with-the")
    assert fairness.rule_key(f) == "LOW|anaphora"


@pytest.mark.parametrize("category,rule_id", [
    ("paragraph-uniformity", "paragraph-uniformity/31-paragraphs-of-near-equal-length"),
    ("nominalization", "nominalization/4-nominalizations-in-one-sentence"),
])
def test_a_note_whose_rule_id_carries_a_count_is_keyed_by_category(category, rule_id):
    assert fairness.rule_key(_finding(category, rule_id)) == f"LOW|{category}"


@pytest.mark.parametrize("edit", ["positional", "open-after", "family"])
def test_the_quotation_mark_table_moves_the_fingerprint(monkeypatch, edit):
    before = fingerprint.ruleset_fingerprint()
    if edit == "positional":
        monkeypatch.setattr(quotemarks, "POSITIONAL", quotemarks.POSITIONAL - {quotemarks.DQ})
    elif edit == "open-after":
        monkeypatch.setattr(quotemarks, "OPEN_AFTER", quotemarks.OPEN_AFTER | {"."})
    else:
        fams = dict(quotemarks.FAMILIES)
        fams["corner"] = {quotemarks.LCORNER: quotemarks.RCORNER}
        monkeypatch.setattr(quotemarks, "FAMILIES", fams)
    assert fingerprint.ruleset_fingerprint() != before, edit
