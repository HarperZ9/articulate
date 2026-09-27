"""Each blocking rule fires on the pattern its label and reason name, and not on
ordinary uses of the same words (ruleset 0.9.0).

A reading of the PERSUADE 2.0 hits, exploratory because that corpus had been
read, found five rules whose matches included uses their own definition
excludes: a mid-sentence "when it comes to" under an opener rule, the noun
phrase "the power of" and the literal "next level" under a superlative rule,
"can possibly" as an intensifier under a hedge rule, the probability idiom
"chances are" under a mind-reading rule, and an essay's own "this is a great
idea" under a rule on flattering an interlocutor. Each fix is judged by the
rule's reason, never by a group rate; the controls show each rule still fires
on the pattern it names.
"""
import pytest

from articulate import check_text, profiles

ESSAY = profiles.load("essay")


def _cats(text, tier):
    r = check_text(text + "\n", profile=ESSAY, house_notes=False)
    return {f["category"] for f in r[tier]}


def _all(text):
    r = check_text(text + "\n", profile=ESSAY, house_notes=False)
    return {f["category"] for t in ("high", "medium", "low") for f in r[t]}


# --- throat-clearing is an opener --------------------------------------------- #

@pytest.mark.parametrize("text", [
    "When it comes to safety, the car is reliable.",
    "But the truth is, the test failed twice.",
    "Needless to say, the benchmark shows no gain.",
    "In today's modern world, every second counts.",
])
def test_control_an_opener_still_blocks(text):
    assert "throat-clearing" in _cats(text, "medium")


@pytest.mark.parametrize("text", [
    "The car is reliable when it comes to safety.",
    "Adults have different views when it comes to school.",
])
def test_a_mid_sentence_topic_frame_is_a_note_not_an_opener(text):
    assert "throat-clearing" not in _cats(text, "medium")
    assert "padded-preposition" in _cats(text, "low")


def test_a_mid_sentence_emphatic_is_not_an_opener():
    assert "throat-clearing" not in _cats("I think the truth is that it failed.", "medium")


# --- marketing names a superlative ------------------------------------------ #

@pytest.mark.parametrize("text", [
    "The sensors reduce the power of the engine.",
    "The electors hold the power of the people.",
    "The Revolutionary War ended in 1783.",
    "Students move on to the next level of learning.",
])
def test_an_ordinary_noun_phrase_is_not_a_superlative(text):
    assert "marketing" not in _all(text)


@pytest.mark.parametrize("text", [
    "Driverless cars will revolutionize travel.",
    "This next-level tool ships today.",
    "It is a revolutionary change in how we travel.",
    "It is a game changer for the team.",
])
def test_control_a_superlative_still_blocks(text):
    assert "marketing" in _cats(text, "medium")


def test_taking_it_to_the_next_level_is_an_idiom():
    text = "We want to take our project to the next level."
    assert "idiom-cliche" in _cats(text, "medium")
    assert "marketing" not in _all(text)


# --- a stacked hedge hedges twice -------------------------------------------- #

@pytest.mark.parametrize("text", [
    "They made it as fun as they can possibly make it.",
    "It is the most exciting job you can possibly get.",
    "It will be the best it can possibly turn out.",
])
def test_an_intensifier_after_a_comparison_is_not_a_hedge(text):
    assert "hedge-stack" not in _all(text)


@pytest.mark.parametrize("text", [
    "The device could possibly help students.",
    "It could potentially save a life.",
    "The best plan could possibly fail. The device could possibly help.",
])
def test_control_a_double_hedge_still_blocks(text):
    assert "hedge-stack" in _cats(text, "medium")


# --- mind-reading and flattery address someone -------------------------------- #

def test_chances_are_is_not_mind_reading():
    assert "meta" not in _all("Chances are you would ask a friend first.")


@pytest.mark.parametrize("text", [
    "This is a great idea because it saves time.",
    "That is a great example of the problem.",
    "This is a very good point about cost.",
])
def test_the_writers_own_praise_of_a_proposal_is_not_flattery(text):
    assert "sycophancy" not in _all(text)


@pytest.mark.parametrize("text", ["That's a great question, and the answer is no.",
                                  "That is an excellent catch in the second table."])
def test_control_praise_of_a_question_still_blocks(text):
    assert "sycophancy" in _cats(text, "medium")
