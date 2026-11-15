"""List items under the structure rules, and the tier of a pronoun run.

Ten of 52 sampled replies carried a hand-back line and the pack caught two,
because most of them closed a bullet and the pack skipped lists. The pin,
pointer and landing rules now read a list item as a short paragraph. Each
case here has a near miss that differs by one feature, and the run rules
still stay out of lists.

A run of exactly three sentences on one personal pronoun was the largest
source of gating findings on human prose, and no sampled reply held one. It
reports at MEDIUM.
"""
import pytest

from test_pack_structure import SPECIMEN_B, hits, run, structure

ITEMS = [
    # landing: a hand-back that closes an item, or is the whole item
    ("structure-landing", "- **Listing.** Archiving keeps installs working but freezes the "
                          "listing. That one is your call.\n", ["HIGH"]),
    ("structure-landing", "- **Listing.** Archiving keeps installs working but freezes the "
                          "listing. That one is on the call sheet.\n", []),
    ("structure-landing", "- Whether to relicense the folder is up to you.\n", ["HIGH"]),
    ("structure-landing", "- Whether to relicense the folder turns on the audit.\n", []),
    ("structure-landing", "1. Granting the permission once adds each new record to your list "
                          "with no further step from anyone, and that click is yours.\n",
     ["HIGH"]),
    ("structure-landing", "1. Granting the permission once adds each new record to your list "
                          "with no further step from anyone, and that click is yours to make "
                          "whenever the next record is ready to go out.\n", []),
    ("structure-landing", "- [ ] The switch sits in the settings page.\n  That switch is "
                          "yours.\n", ["HIGH"]),
    ("structure-landing", "- Your call log is in the archive.\n- Their decision was final.\n",
     []),
    # pointer: a sentence in an item that only rates the one before it
    ("structure-pointer", "- The count came back at 40. That matters.\n", ["HIGH"]),
    ("structure-pointer", "- The count came back at 40. That matters to the two teams who "
                          "size their queues from it.\n", []),
    ("structure-pointer", "- Each team keeps its own copy. That is the silo.\n", ["MEDIUM"]),
    ("structure-pointer", "- This is the default.\n- That is the cache key.\n", []),
    # pin: an item that opens by announcing itself
    ("structure-pin", "- Here is the plan in short. We ship the fix on Monday, after the "
                      "cache test passes.\n", ["HIGH"]),
    ("structure-pin", "- Here is the plan.\n- Two steps remain.\n", []),
]


@pytest.mark.parametrize("category,text,tiers", ITEMS)
def test_list_item_control(category, text, tiers):
    assert [t for t, _r, _m in hits(text, category)] == tiers


def test_ordinary_list_items_stay_quiet():
    text = ("Install steps:\n\n"
            "- Download the archive for your platform.\n"
            "- Unpack it into a folder you can write to.\n"
            "- Run the installer. It asks for a folder and a port.\n"
            "- Open the settings page and choose a profile.\n"
            "1. The licence stays MIT.\n"
            "2. Keys open doors. Keys rust in rain. Keys get lost in coats.\n")
    assert structure(text) == []


def test_run_rules_stay_out_of_lists():
    text = "- Keys open doors.\n- Keys rust in rain.\n- Keys get lost in coats.\n"
    assert structure(text) == []
    text = "- Keys open doors. Keys rust in rain. Keys get lost in coats.\n"
    assert structure(text) == []


def test_a_list_item_span_indexes_the_text():
    text = "Notes:\n\n- **Listing.** Archiving freezes the listing. That one is your call.\n"
    (tier, rule, match), = hits(text, "structure-landing")
    assert (tier, rule, match) == ("HIGH", "structure-landing/handoff", "That one is your call.")
    f, = [f for f in run(text)["high"] if f["category"] == "structure-landing"]
    assert text[f["start"]:f["end"]] == match and f["line"] == 3


def test_a_wrapped_item_line_is_reported_once():
    text = "- The switch sits in the settings page.\n  That switch is yours.\n"
    assert len(hits(text, "structure-landing")) == 1


# --- a pronoun run of three reports, and does not gate ----------------------

PRONOUN = [
    ("It lives in small herds on the open plain, as far south as the islands near the "
     "cape. It is common across the whole of the temperate part of the continent. It "
     "runs from a rider at once when the herd has been hunted that season.\n", [("MEDIUM", "structure-anaphora/pronoun-run")]),
    ("I ran the suite twice on both machines. I read each failure against the log. I "
     "wrote the fix after lunch. I pushed it once the lock test passed.\n",
     [("HIGH", "structure-anaphora/run")]),
    ("One points at a line in the log. One reports that two counts agree. One hands "
     "the next step back.\n", [("HIGH", "structure-anaphora/run")]),
    ("Keys open doors. Keys rust in rain. Keys get lost in coats.\n",
     [("HIGH", "structure-anaphora/run")]),
]


@pytest.mark.parametrize("text,expected", PRONOUN)
def test_pronoun_run_tier(text, expected):
    assert [(t, r) for t, r, _m in hits(text, "structure-anaphora")] == expected


def test_a_pronoun_run_of_three_does_not_gate_and_is_no_triad():
    text = PRONOUN[0][0]
    r = run(text)
    assert r["gate"] == "ok" and r["verdict"] == "flagged"
    assert hits(text, "structure-triad") == []


def test_three_pronoun_sentences_on_one_frame_are_still_a_triad():
    text = "We read the file. We split the tokens. We print the errors.\n"
    assert [(t, r) for t, r, _m in hits(text, "structure-triad")] == [
        ("HIGH", "structure-triad/sentences")]
    assert run(text)["gate"] == "blocked"


def test_specimen_b_stays_blocked_with_its_opener_run_at_high():
    r = run(SPECIMEN_B)
    assert r["gate"] == "blocked"
    assert ("HIGH", "structure-anaphora/run") in [
        (t, rule) for t, rule, _m in hits(SPECIMEN_B, "structure-anaphora")]
