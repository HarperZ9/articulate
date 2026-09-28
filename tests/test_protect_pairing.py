"""The protected-span layer pairs quotation marks and backticks as the rules do.

The detector pairs quotation marks by direction (articulate.quotemarks) and
reads a backtick between two letters as an apostrophe (masking.code_spans). The
protected-span layer, which decides what a model rewrite may not touch and what
the meaning guard compares, used to pair a straight quote with the next straight
quote and any backtick with the next backtick. A stray inch mark or an apostrophe
typed as a backtick then paired with the opening mark of the real quotation or
code span: the writer's prose between them was protected, and the real
quotation or code reached the model as editable prose that the guard read as
prose too. The finders now use the rules' pairing, with an empty pair still no
span of its own.
"""
import pytest

from articulate import finders, guard, invariants, protect

DQ = chr(34)
INCH = "The panel is 6" + DQ + " wide. Write " + DQ + "the board approved it" + DQ + " in the log.\n"
TICK = "I didn`t run `make` today, so run `make` now.\n"


def _quotes(text):
    return [text[s:e] for s, e, _ in finders.quote_spans(text)]


def _code(text):
    return [text[s:e] for kind, s, e, _ in invariants.claim(text, invariants.container_passes(
        numbers=False, quotes=False))[0] if kind == "code"]


def test_an_inch_mark_opens_no_protected_quotation():
    assert _quotes(INCH) == [DQ + "the board approved it" + DQ]


def test_the_quotation_after_an_inch_mark_is_protected():
    masked, spans = protect.mask(INCH)
    assert [s["text"] for s in spans if s["kind"] == "quote"] == [
        DQ + "the board approved it" + DQ]
    assert "approved" not in masked
    assert " wide. Write " in masked


def test_an_edit_inside_the_quotation_after_an_inch_mark_is_refused():
    edited = INCH.replace("approved", "rejected")
    with pytest.raises(guard.RewriteRefused):
        guard.RewriteGuard().check(INCH, edited)
    assert guard.RewriteGuard().run(lambda m: m.replace("approved", "rejected"), INCH) == INCH


@pytest.mark.parametrize("text,quoted", [
    # A quote after a digit closes an open quotation and opens none.
    ("the " + DQ + "top 10" + DQ + " list", [DQ + "top 10" + DQ]),
    # Other marks the rules pair: curly singles with an apostrophe inside,
    # guillemets, and German low quotes.
    ("she wrote ‘it’s done’ and left", ["‘it’s done’"]),
    ("il dit «non» et part", ["«non»"]),
    ("er sagte „ja“ und ging", ["„ja“"]),
    # An apostrophe before a year opens nothing.
    ("the ‘90s were " + DQ + "loud" + DQ, [DQ + "loud" + DQ]),
    # Controls that held before: plain pairs, and an empty pair is no span.
    ("a " + DQ + "b" + DQ + " c " + DQ + "d" + DQ, [DQ + "b" + DQ, DQ + "d" + DQ]),
    ("empty " + DQ + DQ + " then " + DQ + "q" + DQ, [DQ + "q" + DQ]),
    ("open " + DQ + "never closed", []),
])
def test_the_protected_quotations_follow_the_rules_pairing(text, quoted):
    assert _quotes(text) == quoted


def test_an_apostrophe_typed_as_a_backtick_opens_no_protected_code():
    assert _code(TICK) == ["`make`", "`make`"]


def test_the_code_after_a_backtick_apostrophe_is_protected():
    masked, spans = protect.mask(TICK)
    assert [s["text"] for s in spans if s["kind"] == "code"] == ["`make`", "`make`"]
    assert "didn`t run " in masked


@pytest.mark.parametrize("text,code", [
    ("run `make` then ``a ` b`` now", ["`make`", "``a ` b``"]),
    ("a lone ` tick", []),
])
def test_control_code_spans_that_held_before_still_hold(text, code):
    assert _code(text) == code
