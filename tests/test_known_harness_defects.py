"""Known defects in what the fingerprint covers and how a fairness receipt keys
notes, recorded until the next pre-registered ruleset.

- The fingerprint leaves out patterns that decide which text the blocking rules
  read. An edit to one of them changes blocking and still passes the release
  check as "ruleset unchanged". Folding them in moves the fingerprint of the
  ruleset the confirmatory receipt names, so it lands with the next ruleset.
- A fairness receipt keys the paragraph-uniformity and nominalization notes by
  rule ids that carry a per-document count. That splits one note across keys
  and records one essay's paragraph count. Keying them by category changes the
  bytes the harness writes, so the committed receipts would no longer re-derive
  from this code; the change lands with the next pre-registration.

Each defect test is strict xfail (fairness/PREREG.md, amendment of 27 September
2026). The controls are plain tests.
"""
import re

import pytest

from articulate import fairness, fingerprint, lexicon, logical, markup, masking


def _known(defect):
    return pytest.mark.xfail(strict=True, reason=f"known defect ({defect}); the fix "
                                                 "waits for the next pre-registration")


# --- the fingerprint leaves out constants that decide blocking --------------- #

# Each decides which text the blocking rules read: quote, URL, tag, code and
# LaTeX masks, fenced lines, sentence starts, and which lines join a paragraph.
BLOCKING_PATTERNS = [
    (masking, "QUOTED_PATTERN"), (masking, "URL_PATTERN"), (masking, "TAG_PATTERN"),
    (markup, "INLINE_CODE"), (markup, "TEX"), (markup, "FENCE"),
    (logical, "SENTENCE_END"), (lexicon, "HEADING"), (lexicon, "BULLET"),
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


@_known("the fingerprint does not hash this pattern")
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


@_known("a receipt key carries a per-document count")
@pytest.mark.parametrize("category,rule_id", [
    ("paragraph-uniformity", "paragraph-uniformity/31-paragraphs-of-near-equal-length"),
    ("nominalization", "nominalization/4-nominalizations-in-one-sentence"),
])
def test_a_note_whose_rule_id_carries_a_count_is_keyed_by_category(category, rule_id):
    assert fairness.rule_key(_finding(category, rule_id)) == f"LOW|{category}"
