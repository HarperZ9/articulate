"""A3, A5 and A6a: three phrasing rules leave the blocking tier.

A3: "It is important to ..." and "It is worth noting that" become one LOW
`expletive-opener` note. PR9 decision 3 placed this opener at LOW, and the docs
promise it never blocks; the MEDIUM throat-clearing and worth-noting rules
contradicted that. "It should be noted that" stays MEDIUM `wordiness`.

A5: the self-referential framing rule becomes a LOW `announcement` note that
fires only on announcement verbs. "In this essay, I argue" and "This article
examines" state content, and style authorities model both.

A6a: "with respect to" leaves MEDIUM `wordiness` for a LOW `padded-preposition`
note, silent in its operator sense (a gradient with respect to a variable).

The lines are the proposals file's control lines. They measure nothing about
fairness.
"""
import pytest

from articulate import genres, modes, profiles
from controls import assert_passes, cats, high_medium, run

A3_LINES = [
    ("c1", "Before proceeding to examine the survey, it is important to define the sample.",
     ("flavored", "essay", "persuasive-essay/argue")),
    ("c2", "It is important to consider both sides of this issue.",
     ("flavored", "essay", "persuasive-essay/argue", "procedure")),
    ("c3", "It is worth noting that each option has costs.", ("flavored", "essay")),
    ("c4", "It is important to note that adverse events were rare.",
     ("flavored", "essay", "procedure")),
    ("c5", "It is important to bear in mind the possible bias in these responses.",
     ("flavored", "essay")),
]


@pytest.mark.parametrize("cid,text,runs", A3_LINES, ids=[c[0] for c in A3_LINES])
def test_a3_the_opener_is_one_low_note_that_never_blocks(cid, text, runs):
    for run_id in runs:
        r = run(text, run_id)
        assert r["gate"] == "ok" and not high_medium(r), (run_id, high_medium(r))
        assert cats(r, "LOW").count("expletive-opener") == 1, run_id


def test_a3_it_should_be_noted_that_stays_medium():
    line = "It should be noted that the results were mixed."
    assert cats(run(line, "flavored"), "MEDIUM") == ["wordiness"]
    assert run(line, "essay")["gate"] == "blocked"


# Every form the docs call LOW-only: "to" plus a verb, "to note that", the
# gerund preamble and a mid-sentence use, with each adjective the rule names.
_ADJ = ("important", "worth", "crucial", "essential", "necessary", "vital")
LOW_ONLY = ([f"It is {a} to consider the cost." for a in _ADJ if a != "worth"]
            + [f"It is {a} to note that the cost rose." for a in _ADJ if a != "worth"]
            + [f"It's {a} to weigh the cost." for a in ("important", "essential")]
            + ["It is worth noting that the cost rose.",
               "It is worth mentioning that the cost rose.",
               "It is worth pointing out that the cost rose.",
               "However, it is worth noting that the cost rose.",
               "In the end, it is important to note that the cost rose.",
               "It was important to weigh the cost."])


def _every_id():
    return (sorted(profiles.PROFILES) + sorted(genres.GENRES) + list(modes.names()))


def test_the_id_list_is_the_one_the_proposals_counted():
    assert len(_every_id()) == 55


@pytest.mark.parametrize("run_id", _every_id())
def test_a3_low_only_openers_raise_nothing_above_low_under_any_id(run_id):
    # A house profile still gates its own word list ("crucial" is on it); the
    # opener itself must raise nothing above LOW anywhere.
    for line in LOW_ONLY:
        r = run(line, run_id)
        above = [(f["tier"], f["category"]) for t in ("high", "medium") for f in r[t]
                 if not f["house"]]
        assert not above, (run_id, line, above)


A5_PASS = [
    ("c1", "In this essay, I argue that the novel resists closure.", ("flavored", "essay")),
    ("c2", "This essay will discuss three approaches to the issue of housing.",
     ("flavored", "essay")),
    ("c3", "In this section, we prove the main lemma.", ("research", "academic/prove", "essay")),
    ("c4", "This guide covers installing the agent on Linux.", ("flavored", "procedure")),
    ("c5", "This article examines the reception of Ovid in Renaissance Italy.",
     ("flavored", "essay")),
    ("c6", "In this article, we report a randomized controlled trial of home exercise.",
     ("research", "essay")),
]


@pytest.mark.parametrize("cid,text,runs", A5_PASS, ids=[c[0] for c in A5_PASS])
def test_a5_self_reference_does_not_block(cid, text, runs):
    for run_id in runs:
        r = run(text, run_id)
        assert r["gate"] == "ok" and not high_medium(r), (run_id, high_medium(r))


@pytest.mark.parametrize("cid", ["c1", "c3", "c4", "c5", "c6"])
def test_a5_a_statement_of_content_raises_no_note(cid):
    text = dict((c[0], c[1]) for c in A5_PASS)[cid]
    assert "announcement" not in cats(run(text, "flavored"), "LOW")


@pytest.mark.parametrize("text", [
    "This post delves into the topic of productivity.",
    "In this article, we will explore the world of productivity.",
    "This paper will discuss three causes of the war.",
])
def test_a5_an_announcement_is_a_low_note(text):
    for run_id in ("flavored", "essay"):
        r = run(text, run_id)
        assert "announcement" in cats(r, "LOW") and not high_medium(r), run_id
        assert r["gate"] == "ok", run_id


A6_PASS = [
    ("c1", "The gradient with respect to θ vanishes at the optimum.", "a.md",
     ("flavored", "essay")),
    ("c2", "The measure is absolutely continuous with respect to Lebesgue measure.",
     "a.tex", ("research", "essay")),
    ("c3", "Fix gradient with respect to bias", "COMMIT_EDITMSG", ("commit",)),
    ("c4", "The tax is imposed with respect to each taxable year.", "a.md",
     ("legal", "legal/argue", "essay")),
    ("c7", "The derivative with respect to $t$ is zero.", "a.md", ("essay",)),
    ("c8", "The loss is convex with respect to the weights.", "a.md",
     ("flavored", "essay")),
]


@pytest.mark.parametrize("cid,text,name,runs", A6_PASS, ids=[c[0] for c in A6_PASS])
def test_a6_with_respect_to_does_not_block(cid, text, name, runs):
    assert_passes(text, runs, name)


@pytest.mark.parametrize("cid", ["c1", "c2", "c3", "c7", "c8"])
def test_a6_the_operator_sense_raises_no_note(cid):
    text, name = [(c[1], c[2]) for c in A6_PASS if c[0] == cid][0]
    r = run(text, "essay", name)
    assert "padded-preposition" not in cats(r, "LOW") and not high_medium(r)


def test_a6_the_relational_sense_is_a_low_note():
    r = run("The tax is imposed with respect to each taxable year.", "essay")
    assert cats(r, "LOW") == ["padded-preposition"] and r["gate"] == "ok"


@pytest.mark.parametrize("text", ["Due to the fact that the bus was late, we missed class.",
                                  "We are in the process of reviewing the file."])
def test_a6_the_other_padded_phrases_stay_medium(text):
    assert cats(run(text, "flavored"), "MEDIUM") == ["wordiness"]
    assert run(text, "essay")["gate"] == "blocked"


def test_a6_the_readme_example_passes():
    assert_passes("The derivative with respect to $t$ is zero.", ("essay", "flavored"))
