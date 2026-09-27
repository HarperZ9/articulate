"""A1 and A2: quoted text is evidence the writer cites, not the writer's prose.

A1: a quoted chatbot line leaves the HIGH self-description rule. A reflection
that pastes a tool's output, a court that quotes an exchange and a refusal study
that tabulates replies all need the line verbatim. An interface markup token
stays HIGH everywhere, quotes included, because an unrendered token costs every
reader.

A2: the phrasing rules run on text with direct quotations, Markdown block quotes
and LaTeX quote environments masked. Changing a quoted phrase would misquote its
source. The same words unquoted keep their findings.

The lines are the proposals file's control lines (A1-c1 to A1-f2, A2-c1 to
A2-f1). These tests show the rules leave these conventions alone. They measure
nothing about fairness.
"""
import pytest

from controls import assert_passes, cats, run

AI = "As an AI language model, I cannot"

A1_PASS = [
    ("c1", f'It answered, "{AI} give opinions," which surprised me.', "a.md",
     ("flavored", "research", "legal", "essay")),
    ("c2", f"> {AI} rank these sources.", "a.md", ("flavored", "research", "essay")),
    ("c3", "ChatGPT: As an AI language model, I do not have access to that journal.",
     "a.md", ("flavored", "research")),
    ("c4", f"| Prompt | Reply |\n|---|---|\n| Rank the sources | {AI} rank sources. |\n",
     "a.md", ("flavored", "research")),
    ("c5", f"The refusals were uniform.\n\\begin{{quote}}\n{AI} help with that "
           "request.\n\\end{quote}\n", "a.tex", ("research",)),
    ("c6", f'The chatbot replied, "{AI} open links."', "a.md",
     ("journalism", "journalism/explain")),
    ("c7", f"It answered, “{AI} give opinions,” which surprised me.", "a.md",
     ("flavored",)),
]


@pytest.mark.parametrize("cid,text,name,runs", A1_PASS, ids=[c[0] for c in A1_PASS])
def test_a1_quoted_chatbot_text_does_not_block(cid, text, name, runs):
    assert_passes(text, runs, name)


@pytest.mark.parametrize("run_id", ["flavored", "research"])
def test_a1_the_same_line_unquoted_still_blocks(run_id):
    r = run("As an AI language model, I cannot give opinions on this topic.", run_id)
    assert r["gate"] == "blocked" and "chat-interface-text" in cats(r, "HIGH")


def test_a1_a_bare_interface_token_still_blocks():
    r = run("The survey found strong support. contentReference[oaicite:0]", "flavored")
    assert r["gate"] == "blocked"
    assert cats(r, "HIGH").count("chat-interface-text") == 2


def test_a1_an_interface_token_blocks_inside_quotes_too():
    r = run('The page read "see contentReference[oaicite:3]" at the foot.', "flavored")
    assert r["gate"] == "blocked"


def test_a1_a_hidden_character_blocks_inside_quotes_too():
    r = run('The label read "safe​word" on the box.', "flavored")
    assert r["gate"] == "blocked" and "invisible-unicode" in cats(r, "HIGH")


def test_a1_texttt_and_verb_spans_are_masked_for_self_description():
    tex = ("The log shows \\texttt{As an AI language model, I cannot help} and "
           "\\verb|I'm an AI model| verbatim.\n")
    assert_passes(tex, ("research", "essay"), "a.tex")


def test_a1_a_transcript_turn_is_masked_across_its_wrapped_lines():
    text = ("Assistant: I checked the catalogue for you,\n"
            "and as an AI language model, I cannot open the scan.\n")
    assert_passes(text, ("flavored",))


A2_PASS = [
    ("c1", 'The ad promises a "world-class, game-changing experience" but never '
           "names a rival.", "a.md", ("flavored", "essay")),
    ("c2", "> For the purpose of this section, the Secretary shall act with respect "
           "to such persons.", "a.md", ("flavored", "legal", "essay")),
    ("c3", "The Act is short.\n\\begin{quote}\nFor the purpose of this Act, the duty "
           "applies with respect to each carrier.\n\\end{quote}\n", "a.tex",
     ("research", "essay")),
    ("c4", 'Participants rated the item "It is important to note that my pain limits '
           'my work" on a 5-point scale.', "a.md", ("flavored", "essay")),
    ("c5", "The court held that the duty arose 'with respect to the claimant alone'.",
     "a.md", ("flavored", "essay")),
    ("c6", '"It is a revolutionary, world-class product," the chief executive said.',
     "a.md", ("journalism", "journalism/explain", "essay")),
    ("c7", 'Smith (2020) writes that "technology plays an important role in society" '
           "(p. 4).", "a.md", ("flavored", "essay")),
]


@pytest.mark.parametrize("cid,text,name,runs", A2_PASS, ids=[c[0] for c in A2_PASS])
def test_a2_quoted_source_text_does_not_block(cid, text, name, runs):
    assert_passes(text, runs, name)


def test_a2_quoted_phrases_raise_no_medium_finding_under_the_default():
    r = run(A2_PASS[0][1], "flavored")
    assert "marketing" not in cats(r, "MEDIUM")


def test_a2_the_same_phrases_unquoted_still_flag():
    line = "Our platform is a world-class, game-changing experience."
    assert cats(run(line, "flavored"), "MEDIUM").count("marketing") == 2
    r = run(line, "essay")
    assert r["gate"] == "blocked"


def test_a2_scare_quotes_are_exempt_and_the_rest_of_the_sentence_is_not():
    # The open design point: quotation marks exempt what they enclose, and only
    # that. The sentence around them is still the writer's.
    r = run('Our "world-class" platform is a game-changing experience.', "essay")
    assert cats(r, "MEDIUM") == ["marketing"]


def test_a2_a_block_quote_after_a_prose_line_is_masked_line_by_line():
    text = ("The statute reads as follows.\n"
            "> Due to the fact that the carrier failed, the duty ends.\n"
            "Due to the fact that it is short, we quote it whole.\n")
    r = run(text, "essay")
    assert [f["line"] for f in r["medium"]] == [3]


def test_a2_latex_double_quotes_are_masked():
    tex = "The report calls it ``a world-class, game-changing tool'' twice.\n"
    assert_passes(tex, ("research", "essay"), "a.tex")
