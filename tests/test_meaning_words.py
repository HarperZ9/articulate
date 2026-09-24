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


def _negations(text):
    return [i["text"] for i in invariants.extract(text) if i["kind"] == "negation"]


# "no more than" is a bound, and the scope table already keys it with "at most".
# The negation pattern also matched its "no", so the equal rewrite to "at most"
# was refused as a dropped negation.
COMPARATIVE_PRESERVED = [
    ("Send no more than 3 requests.", "Send at most 3 requests."),
    ("Keep no fewer than 2 replicas.", "Keep at least 2 replicas."),
    ("Send a maximum of 3 requests.", "Send no more than 3 requests."),
    ("Send not more than 3 requests.", "Send at most 3 requests."),
    ("Keep not less than 2 replicas.", "Keep a minimum of 2 replicas."),
]
COMPARATIVE_CHANGED = [
    ("Send no more than 3 requests.", "Send more than 3 requests."),
    ("Keep no fewer than 2 replicas.", "Keep fewer than 2 replicas."),
    ("There is no limit on retries.", "There is a limit on retries."),
]


@pytest.mark.parametrize("original,rewrite", COMPARATIVE_PRESERVED)
def test_negated_comparative_is_a_bound(original, rewrite):
    assert _verdict(original, rewrite) == "preserved", _report(original, rewrite)


@pytest.mark.parametrize("original,rewrite", COMPARATIVE_CHANGED)
def test_negated_comparative_change_is_caught(original, rewrite):
    assert _verdict(original, rewrite) == "changed", _report(original, rewrite)


def test_negated_comparative_is_no_negation():
    assert _negations("Reply no later than May 5, not more than twice.") == []
    assert _scopes("Reply no later than May 5, not more than twice.") == [
        "at-most", "at-most"]
    assert _negations("No, it is not ready and there is no more.") == ["No", "not", "no"]


def _modals(text):
    return [(i["key"], i["text"]) for i in invariants.extract(text) if i["kind"] == "modal"]


# A negation right after a modal ("must not") forbids the act; one right before
# it ("do not have to") removes the obligation. The modal key was the class alone
# and negations were one pooled count, so the two read the same.
MODAL_CHANGED = [
    ("You must not delete the audit log.", "You do not have to delete the audit log."),
    ("You mustn't delete the file.", "You don't have to delete the file."),
    ("Clients MUST NOT retry.", "Clients are NOT REQUIRED to retry."),
    ("You should not merge it.", "You do not need to merge it."),
]
MODAL_PRESERVED = [
    ("You must not delete the log.", "You mustn't delete the log."),
    ("You do not have to delete the log.", "You don't have to delete the log."),
    ("You don't need to sign in.", "You do not have to sign in."),
    ("It cannot be undone.", "It can't be undone."),
    ("You must never share keys.", "You must not share keys, ever."),
    ("Do not panic; you must delete it.", "Don't panic; you must delete it."),
]


@pytest.mark.parametrize("original,rewrite", MODAL_CHANGED)
def test_negation_moved_across_a_modal_is_caught(original, rewrite):
    assert _verdict(original, rewrite) == "changed", _report(original, rewrite)


@pytest.mark.parametrize("original,rewrite", MODAL_PRESERVED)
def test_negation_kept_on_the_same_side_is_preserved(original, rewrite):
    assert _verdict(original, rewrite) == "preserved", _report(original, rewrite)


def test_modal_key_records_the_side_of_its_negation():
    assert _modals("You must not go, and you do not have to stay.") == [
        ("required+not", "must not"), ("not-required", "not have to")]
    assert _modals("It cannot fail. It is not strictly required.") == [
        ("optional+not", "cannot"), ("not-required", "not strictly required")]
    assert _modals("Clients MUST NOT retry.") == [("required+not:BCP14", "MUST NOT")]
    assert _modals("You don't have to stay.") == [("not-required", "don't have to")]
