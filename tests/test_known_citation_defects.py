"""Known defects in citation reading and sentence splitting, recorded until the
next pre-registered ruleset.

Decision 2 on pull request 9: `unanchored-claim` fires only when its sentence
carries no number, year or citation. The domain review: `unsupported-authority`
accepts a citation marker anywhere in its sentence, including right after the
closing period, and a year counts only in citation position, so a count does
not silence the rule. The splitter keeps a citation abbreviation inside its
sentence and must still end a sentence at an ordinary word. A review of the
0.6.0 candidate found each of these broken in the cases below.

Each defect test is strict xfail: a fix moves the ruleset, and PERSUADE 2.0 has
been read, so the fix waits for the next pre-registered ruleset
(fairness/PREREG.md, amendment of 27 September 2026). The controls are plain
tests.
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


def _known(defect):
    return pytest.mark.xfail(strict=True, reason=f"known defect ({defect}); the fix "
                                                 "changes the ruleset and waits for the "
                                                 "next pre-registration")


# --- a cite key or a URL does not anchor "state of the art" ------------------ #

def test_control_a_bare_state_of_the_art_gets_the_note():
    assert "unanchored-claim" in _cats("This is the state of the art.", "low", DEFAULT)


@_known("the claim anchor reads text that is already blanked")
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


@_known("a marker after the closing period falls into the next sentence")
@pytest.mark.parametrize("marker", ["<sup>1</sup>", f"{BS}footnote{{Smith, 2019.}}",
                                    f"{BS}cite{{smith}}"])
def test_a_marker_right_after_the_closing_period_anchors(marker):
    text = f"Studies show that sleep improves recall.{marker} Then we slept."
    assert "unsupported-authority" not in _cats(text, "medium", ESSAY)


# --- counts and vague attributions read as citations ------------------------- #

@_known("a count in parentheses or a vague attribution reads as a citation")
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


@_known("a sentence ending in a listed abbreviation word does not end")
@pytest.mark.parametrize("first", ["The answer was no.", "I asked Ed."])
def test_a_sentence_ending_in_a_listed_word_still_ends(first):
    assert len(sentences(first + " Studies show that it works.")) == 2


@_known("a sentence-start note misses a sentence after one ending in no")
def test_a_sentence_start_note_runs_after_a_sentence_ending_in_no():
    text = "The answer was no. It is important to note that the sample was small."
    assert "expletive-opener" in _cats(text, "low", DEFAULT)
