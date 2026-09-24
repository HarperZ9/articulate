"""Meaning-guard regressions for names and citations, and for formatting-only
edits the guard must let through.

Each unfaithful pair must read `changed` and each faithful pair `preserved`.
One test pins the blind spot the report states: a name used once, at a
sentence start, and swapped for another.
"""
import pytest

from articulate import meaning


def _verdict(original, rewrite):
    return meaning.compare(original, rewrite)["verdict"]


def _report(original, rewrite):
    return meaning.format_report(meaning.compare(original, rewrite))


# A name that opens with a lower-case letter was never an entity, a narrative
# citation had no pattern, and a name at a sentence start was weak even when
# the text used it mid-sentence too.
NAME_CHANGED = [
    ("It runs on macOS only.", "It runs on iOS only."),
    ("Test it on an iPhone first.", "Test it on an iPad first."),
    ("Smith (2020) showed the effect.", "Jones (2020) showed the effect."),
    ("Smith and Lee (2020, p. 4) showed it.", "Smith and Kim (2020, p. 4) showed it."),
    ("Alice approved the change. Ask Alice.", "Mallory approved the change. Ask Alice."),
    ("Alice approved the change.", "Mallory approved the change, as Mallory said."),
]
NAME_PRESERVED = [
    ("It runs on macOS only.", "Only macOS runs it."),
    ("Smith (2020) showed the effect.", "The effect was shown by Smith (2020)."),
    # A plain-language suggestion at a sentence start is a word swap.
    ("Utilize the cache first.", "Use the cache first."),
    # A title-case heading word is no evidence that the same word is a name.
    ("## Quick Start\n\nStart the server.", "## Quick Start\n\nLaunch the server."),
    # A word the text also uses in lower case is an ordinary word.
    ("Start the job. We start it daily, per the Start page.",
     "Run the job. We start it daily, per the Start page."),
]


@pytest.mark.parametrize("original,rewrite", NAME_CHANGED)
def test_changed_name_is_caught(original, rewrite):
    assert _verdict(original, rewrite) == "changed", _report(original, rewrite)


@pytest.mark.parametrize("original,rewrite", NAME_PRESERVED)
def test_kept_name_is_preserved(original, rewrite):
    assert _verdict(original, rewrite) == "preserved", _report(original, rewrite)


def test_single_sentence_start_name_swap_is_a_documented_blind_spot():
    """A capitalized word that opens a sentence may be an ordinary word, and
    pairing two of them by the word that follows refuses plain rewrites such as
    "Utilize the cache" to "Use the cache". A name used once at a sentence start
    therefore goes unreported, and the report says so."""
    report = meaning.compare("Alice approved the change.", "Mallory approved the change.")
    assert report["verdict"] == "preserved"
    assert "opens a sentence" in report["does_not_prove"]
