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
    # RFC 2119 makes NOT RECOMMENDED a synonym of SHOULD NOT, and plain
    # "not recommended" advises against in the same way.
    ("Clients SHOULD NOT retry.", "Retrying is NOT RECOMMENDED."),
    ("You should not merge it.", "Merging it is not recommended."),
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
    assert _modals("It is NOT RECOMMENDED.") == [("recommended+not:BCP14", "NOT RECOMMENDED")]


# Quantifiers and frequency words scope a claim as much as "only" does. None
# was read, and a sentence-initial "All" was a weak name, which is never
# reported when unmatched.
QUANTIFIER_CHANGED = [
    ("Users must reset all passwords.", "Users must reset some passwords."),
    ("The proxy logs every request.", "The proxy logs some requests."),
    ("All tests must pass.", "Tests must pass."),
    ("The job usually finishes in 10 min.", "The job rarely finishes in 10 min."),
    ("A few hosts failed.", "Few hosts failed."),
    # "after all" and "at all" before a noun quantify it; the idiom reading
    # used to swallow the "all".
    ("Deploy after all tests pass.", "Deploy after tests pass."),
    ("Keep the door locked at all times.", "Keep the door locked at times."),
]
QUANTIFIER_PRESERVED = [
    ("Users must reset all passwords.", "Users must reset every password."),
    ("Each request is logged.", "Every request is logged."),
    ("The job usually finishes early.", "The job typically finishes early."),
    ("Some hosts failed.", "Several hosts failed."),
    # Idioms that hold a quantifier word and quantify nothing.
    ("It did not work at all.", "It did not work."),
    ("After all, the cache is shared.", "In the end, the cache is shared."),
    ("They review each other's code.", "They review one another's code."),
    ("Above all, keep it short.", "Most of all, keep it short."),
    ("It works, after all.", "It works."),
    ("Deploy after all tests pass.", "Deploy after every test passes."),
    ("Deploy subsequent to all tests passing.", "Deploy after all tests passing."),
    ("Keep the door locked at all times.", "Keep the door locked always."),
]


@pytest.mark.parametrize("original,rewrite", QUANTIFIER_CHANGED)
def test_changed_quantifier_is_caught(original, rewrite):
    assert _verdict(original, rewrite) == "changed", _report(original, rewrite)


@pytest.mark.parametrize("original,rewrite", QUANTIFIER_PRESERVED)
def test_same_quantifier_is_preserved(original, rewrite):
    assert _verdict(original, rewrite) == "preserved", _report(original, rewrite)


def test_sentence_initial_quantifier_is_scope_and_no_name():
    items = invariants.extract("All tests pass. Every build ships.")
    assert [i["key"] for i in items if i["kind"] == "scope"] == ["universal", "universal"]
    assert [i["key"] for i in items if i["kind"] == "entity"] == []


def _pack_suggestions():
    from articulate import pack_controlled, pack_plain
    pairs = list(pack_plain._WORDY) + list(pack_controlled._IDIOMS.items())
    pairs += list(pack_controlled._PHRASAL.items())
    # "to, or for" offers two replacements; each one is a rewrite to check.
    return [(p, s) for p, both in pairs for s in both.split(", or ")]


@pytest.mark.parametrize("phrase,suggestion", _pack_suggestions())
def test_rule_pack_suggestions_keep_the_meaning(phrase, suggestion):
    """The plain-language and controlled-English packs suggest these rewrites,
    so the meaning guard must let each one through. "is able to" to "can" read
    as an added modal, and "a no-brainer" as a dropped negation. Before a
    statute citation, "pursuant to" to "under" read as an added bound."""
    for context in ("so we {} it", "so we {} 5 U.S.C. 552 now"):
        original, rewrite = context.format(phrase), context.format(suggestion)
        assert _verdict(original, rewrite) == "preserved", _report(original, rewrite)


def test_over_before_a_count_stays_a_bound_in_a_phrasal_verb():
    """The controlled-English pack suggests "review" for "go over". Before a
    count, "over" may mean "more than" ("do not go over 5 GB"), so the guard
    refuses that rewrite there. The refusal is the safe side of the ambiguity,
    and this test records it."""
    assert _verdict("Do not go over 5 GB.", "Do not review 5 GB.") == "changed"
    assert _verdict("We go over 3 items.", "We review 3 items.") == "changed"


ABILITY_PRESERVED = [
    ("The service is able to retry the call.", "The service can retry the call."),
    ("The client has the ability to cancel.", "The client can cancel."),
    ("The client is not able to cancel.", "The client cannot cancel."),
    ("The client is unable to cancel.", "The client can't cancel."),
    ("Caching is a no-brainer here.", "Caching is an easy choice here."),
]
ABILITY_CHANGED = [
    ("The service is able to retry the call.", "The service must retry the call."),
    ("The client is unable to cancel.", "The client can cancel."),
    ("No-one reviewed it.", "Someone reviewed it."),
]


@pytest.mark.parametrize("original,rewrite", ABILITY_PRESERVED)
def test_ability_and_hyphen_compounds_are_preserved(original, rewrite):
    assert _verdict(original, rewrite) == "preserved", _report(original, rewrite)


@pytest.mark.parametrize("original,rewrite", ABILITY_CHANGED)
def test_ability_and_hyphen_compound_changes_are_caught(original, rewrite):
    assert _verdict(original, rewrite) == "changed", _report(original, rewrite)
