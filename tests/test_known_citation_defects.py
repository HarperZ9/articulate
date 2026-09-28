"""Defects in citation reading and sentence splitting found in review of the
0.6.0 candidate, fixed in ruleset 0.9.0 (SCAN_ALGO 7).

Decision 2 on pull request 9: `unanchored-claim` fires only when its sentence
carries no number, year or citation. The domain review: `unsupported-authority`
accepts a citation marker anywhere in its sentence, including right after the
closing period, and a year counts only in citation position, so a count does
not silence the rule. The splitter keeps a citation abbreviation inside its
sentence and must still end a sentence at an ordinary word. A review of the
0.6.0 candidate found each of these broken in the cases below.

Each defect test was strict xfail until the fix, because the fix moves the
ruleset and PERSUADE 2.0 had been read (fairness/PREREG.md, amendment of 27
September 2026). The tests now guard the fix. The controls show what must still
anchor and still join, so the tighter reading cannot overreach unseen.
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



# --- a cite key or a URL does not anchor "state of the art" ------------------ #

def test_control_a_bare_state_of_the_art_gets_the_note():
    assert "unanchored-claim" in _cats("This is the state of the art.", "low", DEFAULT)


@pytest.mark.parametrize("anchor", [f"{BS}cite{{smith}}", f"~{BS}citep{{smith,jones}}",
                                    "(see https://example.org/leaderboard)"])
def test_a_cite_key_or_a_url_anchors_state_of_the_art(anchor):
    text = f"This is the state of the art {anchor}."
    assert "unanchored-claim" not in _cats(text, "low", DEFAULT)


# --- a marker right after the closing period does not anchor ----------------- #

@pytest.mark.parametrize("marker", ["<sup>1</sup>", f"{BS}footnote{{Smith, 2019.}}",
                                    f"~{BS}cite{{smith}}"])
def test_control_the_same_marker_before_the_period_anchors(marker):
    text = f"Studies show that sleep improves recall{marker}."
    assert "unsupported-authority" not in _cats(text, "medium", ESSAY)


@pytest.mark.parametrize("marker", ["<sup>1</sup>", f"{BS}footnote{{Smith, 2019.}}",
                                    f"{BS}cite{{smith}}"])
def test_a_marker_right_after_the_closing_period_anchors(marker):
    text = f"Studies show that sleep improves recall.{marker} Then we slept."
    assert "unsupported-authority" not in _cats(text, "medium", ESSAY)


# --- counts and vague attributions read as citations ------------------------- #

@pytest.mark.parametrize("tail", ["(1600 patients)", "(n = 1850)",
                                  ", according to a recent study",
                                  ", according to researchers"])
def test_a_count_or_a_vague_attribution_does_not_anchor(tail):
    text = f"Studies show that sleep improves recall{tail}."
    assert "unsupported-authority" in _cats(text, "medium", ESSAY)


# --- the splitter joins a sentence that ends in "no" or "Ed" ----------------- #

@pytest.mark.parametrize("text", ["See p. 4 for details.", "Smith v. Jones settled it.",
                                  "Smith et al. (2019) agree.", "It sits in Fig. 3 here."])
def test_control_a_citation_abbreviation_stays_inside_its_sentence(text):
    assert len(sentences(text)) == 1


@pytest.mark.parametrize("first", ["The answer was no.", "I asked Ed."])
def test_a_sentence_ending_in_a_listed_word_still_ends(first):
    assert len(sentences(first + " Studies show that it works.")) == 2


def test_a_sentence_start_note_runs_after_a_sentence_ending_in_no():
    text = "The answer was no. It is important to note that the sample was small."
    assert "expletive-opener" in _cats(text, "low", DEFAULT)


# --- controls for the fixes: what must still anchor, and still join ---------- #

@pytest.mark.parametrize("tail", ["(Smith, 2019)", " (2019)", " (Smith 2019, p. 4)",
                                  " (e.g., Smith et al., 2019; Jones, 2020)",
                                  " (World Health Organization, 2021)",
                                  ", according to Smith (2019)",
                                  ", according to the WHO"])
def test_control_a_named_source_still_anchors(tail):
    text = f"Studies show that sleep improves recall{tail}."
    assert "unsupported-authority" not in _cats(text, "medium", ESSAY)


@pytest.mark.parametrize("text", ["See No. 5 below.", "Smith (Ed.) disagrees.",
                                  "They met in St. Louis twice.", "Read vol. 2 first."])
def test_control_the_citation_shapes_still_join(text):
    assert len(sentences(text)) == 1


@pytest.mark.parametrize("text", ["It was the Ed. Then it rained.",
                                  "Look at p. Then read on."])
def test_a_listed_word_without_its_citation_shape_ends_the_sentence(text):
    assert len(sentences(text)) == 2


# --- "According to" at a sentence start (found in the 0.9.0 build) ----------- #
# "according to" before a named source anchors the appeal. The pattern was read
# with its case, so a sentence that opens "According to NASA," went unread.

@pytest.mark.parametrize("text", [
    "According to NASA, research shows that the surface is too hot for a probe.",
    "According to the WHO, studies show that sleep improves recall.",
    "ACCORDING TO THE WHO, studies show that sleep improves recall.",
])
def test_according_to_a_named_source_anchors_at_a_sentence_start(text):
    assert "unsupported-authority" not in _cats(text, "medium", ESSAY)


@pytest.mark.parametrize("text", [
    "According to experts, research shows that sleep improves recall.",
    "According to a recent study, studies show that sleep improves recall.",
    "According To Recent Studies, research shows that sleep improves recall.",
])
def test_control_according_to_an_unnamed_source_still_fires_at_a_sentence_start(text):
    assert "unsupported-authority" in _cats(text, "medium", ESSAY)
