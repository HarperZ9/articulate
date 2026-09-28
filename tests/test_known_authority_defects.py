"""Known defects in `unsupported-authority`, recorded for the next ruleset.

The rule's reason: an appeal to unnamed studies or experts gives the reader no
source to check. Two shapes name the source and still fire, found while reading
the rule's hits for ruleset 0.9.0 (about 10 essays in an exploratory reading of
an already-read corpus):

- the sentence names its source by title or by a numbered source the document
  lists ("In source 2, studies show ...");
- a demonstrative refers back to a source the previous sentence names ("A 2019
  NASA report measured the surface. This research shows ...").

A fix reads the previous sentence, which the rule does not do today, and it
changes the ruleset after these hits were read, so it waits for a ruleset
pre-registered with its own corpus. Each defect test is strict xfail; the
controls are plain tests and must keep passing.
"""
import pytest

from articulate import check_text, profiles

ESSAY = profiles.load("essay")
DQ = chr(34)


def _fires(text):
    r = check_text(text + "\n", profile=ESSAY, house_notes=False)
    return any(f["category"] == "unsupported-authority" for f in r["medium"])


def _known(defect):
    return pytest.mark.xfail(strict=True, reason=f"known defect ({defect}); the fix "
                                                 "changes the ruleset and waits for the "
                                                 "next pre-registration")


# --- the sentence names its source by title or by number -------------------- #

@_known("a title or a numbered source in the sentence is no citation marker")
@pytest.mark.parametrize("text", [
    "In the article " + DQ + "The Challenge of Exploring Venus" + DQ
    + ", studies show that the surface is too hot for a probe.",
    "In source 2, studies show that drivers react more slowly.",
    "According to source 3, research shows that sleep improves recall.",
])
def test_a_source_named_in_the_sentence_anchors_the_appeal(text):
    assert not _fires(text)


# --- a demonstrative refers back to a source the previous sentence names ---- #

@_known("the rule reads one sentence, so a reference back to a named source is missed")
@pytest.mark.parametrize("text", [
    "A 2019 NASA report measured the surface of Venus. This research shows that "
    "the clouds hold sulfuric acid.",
    "Smith and Jones (2020) surveyed 400 drivers. These studies show that phones "
    "slow reaction times.",
])
def test_a_demonstrative_after_a_named_source_anchors_the_appeal(text):
    assert not _fires(text)


# --- controls: plain tests that hold before and after a fix ----------------- #

@pytest.mark.parametrize("text", [
    "Studies show that the surface is too hot for a probe.",
    "Research shows that sleep improves recall.",
    "The weather was fine. This research shows that sleep improves recall.",
])
def test_control_an_appeal_with_no_source_anywhere_fires(text):
    assert _fires(text)


@pytest.mark.parametrize("text", [
    "Studies show that the surface is too hot for a probe (Smith, 2019).",
    "Research shows that the surface is too hot for a probe, according to NASA.",
    "Studies show that drivers react more slowly (Source 2).",
])
def test_control_a_citation_marker_in_the_sentence_anchors_the_appeal(text):
    assert not _fires(text)
