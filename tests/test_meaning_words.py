"""Meaning-guard regressions for the word-level invariants: scope words,
comparison direction, negation, modal strength, quantifiers, and names.

Each unfaithful pair must read `changed` and each faithful pair `preserved`.
The faithful pairs are the false-positive controls: a fix that catches more by
refusing more fails them.
"""
import pytest

from articulate import invariants, meaning


def _verdict(original, rewrite):
    return meaning.compare(original, rewrite)["verdict"]


def _report(original, rewrite):
    return meaning.format_report(meaning.compare(original, rewrite))


def _scopes(text):
    return [i["key"] for i in invariants.extract(text) if i["kind"] == "scope"]


# A scope or comparison word that bounds a number. The number mask used to blank
# the digits before the scope pattern looked for them, so "up to" never counted,
# and no comparison word was read at all.
BOUND_CHANGED = [
    ("Upload up to 10 MB per file.", "Upload 10 MB per file."),
    ("Send up to $5 today.", "Send $5 today."),
    ("Send up to three requests.", "Send three requests."),
    ("Load stays under 50% of capacity.", "Load stays over 50% of capacity."),
    ("Accounts with more than 3 failed logins are locked.",
     "Accounts with fewer than 3 failed logins are locked."),
    ("Alert when disk use is below 10%.", "Alert when disk use is above 10%."),
    ("Rotate the keys before 2026-05-05.", "Rotate the keys after 2026-05-05."),
]
BOUND_PRESERVED = [
    ("Send at most 3 requests.", "Send up to 3 requests."),
    ("Load stays under 50% of capacity.", "Load stays below 50% of capacity."),
    ("Accounts with more than 3 failed logins are locked.",
     "Accounts with over 3 failed logins are locked."),
    ("Rotate the keys prior to 2026-05-05.", "Rotate the keys before 2026-05-05."),
    # No number follows, so these are prepositions, not bounds.
    ("The data moves over the network.", "The data moves across the network."),
    ("Keep the form up to date.", "Keep the form current."),
    ("Look under the hood first.", "Look inside first."),
]


@pytest.mark.parametrize("original,rewrite", BOUND_CHANGED)
def test_changed_bound_is_caught(original, rewrite):
    assert _verdict(original, rewrite) == "changed", _report(original, rewrite)


@pytest.mark.parametrize("original,rewrite", BOUND_PRESERVED)
def test_same_bound_is_preserved(original, rewrite):
    assert _verdict(original, rewrite) == "preserved", _report(original, rewrite)


def test_bound_needs_a_number_after_it():
    assert _scopes("Send up to 3 requests.") == ["at-most"]
    assert _scopes("Stay under 5 ms, over 2 ms, before May 5, after 10:30.") == [
        "less-than", "more-than", "before", "after"]
    assert _scopes("Stay under the limit and over the moon, up to now.") == []
