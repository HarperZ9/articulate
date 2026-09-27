"""Correctness review of citation detection and sentence splitting (decision 2,
P1 item A4, SCAN_ALGO 5 and 6).

Decision 2: `unanchored-claim` fires only when the sentence carries no number,
year or citation. A4: `unsupported-authority` anchors on a marker anywhere in
the sentence, "and on a marker placed right after the closing period", and a
year counts only in citation position, "so 'in 1200 patients' no longer
silences the rule". The splitter keeps a citation abbreviation inside its
sentence and must still end a sentence at an ordinary word.

Every test here is strict xfail: a fix moves the ruleset, and PERSUADE 2.0 has
been read, so the fix is exploratory on it (fairness/PREREG.md). Controls are
plain tests and pass today.
"""
import pytest

from articulate import check_text, profiles
from articulate.logical import sentences

ESSAY = profiles.load("essay")
DEFAULT = profiles.load("flavored")
BS = chr(92)


def _cats(text, tier, prof):
    r = check_text(text + "\n", profile=prof, house_notes=False)
    return [f["category"] for f in r[tier]]


def _xfail(item):
    return pytest.mark.xfail(strict=True, reason=f"REVIEW-correctness {item}")


# --- C-8: two of the five claim anchors read text that is already blanked --- #

def test_control_a_bare_state_of_the_art_gets_the_note():
    assert "unanchored-claim" in _cats("This is the state of the art.", "low", DEFAULT)


@_xfail("C-8")
@pytest.mark.parametrize("anchor", [f"{BS}cite{{smith}}", f"~{BS}citep{{smith,jones}}",
                                    "(see https://example.org/leaderboard)"])
def test_a_cite_key_or_a_url_anchors_state_of_the_art(anchor):
    text = f"This is the state of the art {anchor}."
    assert "unanchored-claim" not in _cats(text, "low", DEFAULT)


# --- C-10: a marker after the closing period does not anchor ----------------- #

@pytest.mark.parametrize("marker", ["<sup>1</sup>", f"{BS}footnote{{Smith, 2019.}}",
                                    f"~{BS}cite{{smith}}"])
def test_control_the_same_marker_before_the_period_anchors(marker):
    text = f"Studies show that sleep improves recall{marker}."
    assert "unsupported-authority" not in _cats(text, "medium", ESSAY)


@_xfail("C-10")
@pytest.mark.parametrize("marker", ["<sup>1</sup>", f"{BS}footnote{{Smith, 2019.}}",
                                    f"{BS}cite{{smith}}"])
def test_a_marker_right_after_the_closing_period_anchors(marker):
    text = f"Studies show that sleep improves recall.{marker} Then we slept."
    assert "unsupported-authority" not in _cats(text, "medium", ESSAY)


# --- C-11: counts and vague attributions read as citations ------------------- #

@_xfail("C-11")
@pytest.mark.parametrize("tail", ["(1600 patients)", "(n = 1850)",
                                  ", according to a recent study",
                                  ", according to researchers"])
def test_a_count_or_a_vague_attribution_does_not_anchor(tail):
    text = f"Studies show that sleep improves recall{tail}."
    assert "unsupported-authority" in _cats(text, "medium", ESSAY)


# --- C-13: the splitter joins a sentence that ends in "no" or "Ed" ----------- #

@pytest.mark.parametrize("text", ["See p. 4 for details.", "Smith v. Jones settled it.",
                                  "Smith et al. (2019) agree.", "It sits in Fig. 3 here."])
def test_control_a_citation_abbreviation_stays_inside_its_sentence(text):
    assert len(sentences(text)) == 1


@_xfail("C-13")
@pytest.mark.parametrize("first", ["The answer was no.", "I asked Ed."])
def test_a_sentence_ending_in_a_listed_word_still_ends(first):
    assert len(sentences(first + " Studies show that it works.")) == 2


@_xfail("C-13")
def test_a_sentence_start_note_runs_after_a_sentence_ending_in_no():
    text = "The answer was no. It is important to note that the sample was small."
    assert "expletive-opener" in _cats(text, "low", DEFAULT)
