"""G4's layouts keep the document's structure (ruleset 0.9.0 harness).

G4 asks whether findings move when the same words are laid out differently. Its
rewrap replaced every newline with a space, which joined all paragraphs into one
(review C-14): a quotation left open in one paragraph then paired with a mark in
the next, and a paragraph with no closing punctuation joined the next sentence.
Its hard wrap could start a line with "- ", which Markdown reads as a list item.
Both change the document's structure, not only its layout. The rewrap now works
inside each paragraph, neither layout starts a line with a block marker, and the
receipt still reports, and never gates on, the paragraph-joining count. This
changes a gate's method and can turn a failing row into a passing one, so it is
its own commit. The texts are made up and measure nothing about fairness.
"""
import json
import re
import textwrap
from pathlib import Path

import pytest

from articulate import fairness, profiles
from articulate.logical import units
from test_fairness_reports import PLAIN, _manifest

DQ = chr(34)
ESSAY = profiles.load("essay")
MARKER = re.compile(r"^\s*(?:[-*+]|\d+[.)]|#{1,6}|>|\|)(?:\s|$)")


def test_the_rewrap_keeps_paragraph_breaks():
    assert fairness.rewrap("A one. A two.\n\nB one. B two.\n") == \
        "A one.\nA two.\n\nB one.\nB two.\n"


# A quotation left open at the end of one paragraph, and a stray closing mark in
# the next: joining the paragraphs pairs them and blanks the prose between.
OPEN_QUOTE = ("He wrote " + DQ + "we will be late and left.\n\n"
              "Studies show that the bus is slow, he said." + DQ + " Then we went home.\n")


def test_the_joined_rewrap_moves_a_finding_the_kept_rewrap_does_not():
    base = fairness.measure(OPEN_QUOTE, ESSAY)
    assert base["hm"], "premise: the text has a blocking-tier finding"
    joined = fairness.measure(fairness.rewrap_joined(OPEN_QUOTE), ESSAY)
    kept = fairness.measure(fairness.rewrap(OPEN_QUOTE), ESSAY)
    assert joined["hm"] != base["hm"], "premise: joining paragraphs moves it"
    assert kept["hm"] == base["hm"]
    assert fairness.layout_changes(OPEN_QUOTE, base, ESSAY) == (False, True)


def test_a_paragraph_with_no_closing_mark_keeps_its_own_sentence():
    text = "Some notes on the trip\n\nIt is important to note that we left early.\n"
    base = fairness.measure(text, ESSAY)
    assert fairness.measure(fairness.rewrap(text), ESSAY)["rules"] == base["rules"]


def test_the_joined_rewrap_is_the_old_one_sentence_per_line_rewrap():
    text = "One. Two!\nThree?\n\nFour.\n"
    assert fairness.rewrap_joined(text) == "One.\nTwo!\nThree?\nFour.\n"


# --- no layout starts a line with a block marker ------------------------------ #

HYPHENS = ("The long road into the old town runs past the mill - which closed in "
           "the spring - and then past a school that " + "ran for years - " * 6 + "and "
           "stops.\n")


def _new_block_lines(wrapped):
    return [ln for para in wrapped.split("\n\n") for ln in para.split("\n")[1:]
            if MARKER.match(ln)]


def _plain_fill(text, width):
    """The hard wrap before 0.9.0: textwrap.fill on each paragraph."""
    paras = [p.replace("\n", " ") for p in re.split(r"\n\s*\n", text) if p.strip()]
    return "\n\n".join(textwrap.fill(p, width, break_long_words=False) for p in paras)


def test_the_hard_wrap_never_starts_a_line_with_a_block_marker():
    assert any(_new_block_lines(_plain_fill(HYPHENS, w))
               for w in range(30, 70)), "premise: a plain hard wrap makes a list line"
    for width in range(30, 70):
        assert not _new_block_lines(fairness.hardwrap(HYPHENS, width)), width


def test_the_hard_wrap_keeps_every_word_in_order():
    for width in range(30, 70):
        assert fairness.hardwrap(HYPHENS, width).split() == HYPHENS.split()


def test_the_rewrap_never_starts_a_line_with_a_block_marker():
    text = "The plan failed. - It was late, and it was costly. 2. Next it rained.\n"
    out = fairness.rewrap(text)
    assert not _new_block_lines(out), out
    assert out.split() == text.split()


# --- the layouts keep the blocks the scanner reads ---------------------------- #
# A paragraph is what the scanner reads as one logical line
# (articulate.logical.units). A list item, heading, table row or block quote
# starts its own block with no blank line before it, a fence holds its lines as
# they are, and a line that ends in a hyphen after a letter joins the next with
# no space. A layout that split only at blank lines joined such blocks into one
# line, so the laid-out text was a different document.

def _shape(text):
    return [(u.kind, " ".join(u.text.split()))
            for u in units(text.splitlines(keepends=True))]


BLOCKS = {
    "list": "Our plan had three parts:\n- The truth is we were late.\n- Then we shipped it.\n",
    "heading": "Some intro text here.\n# Results\nThe truth is the test failed.\n",
    "block quote": ("He said this.\n\n> The truth is we were late.\n"
                    "> Studies show the bus is slow.\n"),
    "line-end hyphen": "We built a state-of-the-\nart design that works well.\n",
    "table": "| a | b |\n|---|---|\n| one. two. | three |\n",
    "fence": "Run this.\n\n```\nx = 1. y = 2.\n\n\nz = 3.\n```\nThe truth is it ran.\n",
}


@pytest.mark.parametrize("layout", ["rewrap", "hardwrap"])
@pytest.mark.parametrize("name", sorted(BLOCKS))
def test_a_layout_keeps_the_blocks_the_scanner_reads(name, layout):
    text = BLOCKS[name]
    assert _shape(getattr(fairness, layout)(text)) == _shape(text)


def test_a_fence_keeps_its_lines_as_they_are():
    text = BLOCKS["fence"]
    for out in (fairness.rewrap(text), fairness.hardwrap(text)):
        assert "```\nx = 1. y = 2.\n\n\nz = 3.\n```\n" in out, out


def test_a_heading_with_no_blank_line_before_it_moves_no_finding():
    text = BLOCKS["heading"]
    base = fairness.measure(text, ESSAY)
    assert base["hm"], "premise: the text has a blocking-tier finding"
    assert fairness.layout_changes(text, base, ESSAY)[0] is False


# A spaced hyphen after a word ("well- known") and a double hyphen: a hard wrap
# that breaks after the hyphen makes the scanner join the two lines with no
# space, or with one where the text had none, and the words change.
SPACED = ("It was a well- known fact that the plan -- which was new -- worked, "
          "and the long-term cost was low. ") * 4


def test_the_hard_wrap_never_changes_how_the_scanner_joins_a_line():
    for width in range(20, 70):
        assert _shape(fairness.hardwrap(SPACED, width)) == _shape(SPACED), width


REPO = Path(__file__).resolve().parents[1]
SHIPPED = [REPO / "README.md", REPO / "CHANGELOG.md", *sorted((REPO / "docs").glob("*.md")),
           *sorted(p for p in (REPO / "corpus").rglob("*") if p.suffix in (".md", ".txt"))]


@pytest.mark.parametrize("path", SHIPPED, ids=lambda p: p.relative_to(REPO).as_posix())
def test_the_layouts_keep_the_blocks_of_every_shipped_document(path):
    # Lists, tables, fences and block quotes in real Markdown: when this test was
    # written, the layouts that split only at blank lines changed the blocks in
    # 22 of the 64 layouts of these files.
    text = path.read_text("utf-8")
    for layout in (fairness.rewrap, fairness.hardwrap):
        assert _shape(layout(text)) == _shape(text), layout.__name__


# --- G4 in the receipt -------------------------------------------------------- #

def test_the_receipt_gates_on_the_kept_layouts_and_reports_the_joined_rewrap(tmp_path):
    path, _ = _manifest(tmp_path, {"a": [OPEN_QUOTE] + PLAIN[:3], "b": PLAIN[3:]})
    rec = fairness.run(str(path), names=["essay"])
    (cfg,) = rec["results"].values()
    assert cfg["g4"]["changed"] == 0
    assert cfg["g4"]["by_set"] == {"a": 0, "b": 0}
    assert cfg["g4"]["joined_rewrap"] == {"changed": 1, "by_set": {"a": 1, "b": 0},
                                          "gates": False}
    assert rec["gates"]["G4"] is True


def test_the_receipt_names_the_method_it_ran_under(tmp_path):
    path, _ = _manifest(tmp_path, {"a": PLAIN[:4], "b": PLAIN[4:]})
    rec = fairness.run(str(path), names=["flavored"])
    assert rec["method"] == fairness.METHOD
    assert set(fairness.METHOD) == {"g2_empty_arm", "g4_layouts", "stratified_interval"}


@pytest.mark.parametrize("jobs", [2])
def test_the_layout_counts_are_the_same_in_several_processes(tmp_path, jobs):
    path, _ = _manifest(tmp_path, {"a": [OPEN_QUOTE] + PLAIN[:3], "b": PLAIN[3:]})
    one = fairness.run(str(path), names=["essay", "flavored"])
    many = fairness.run(str(path), names=["essay", "flavored"], jobs=jobs)
    assert json.dumps(one, sort_keys=True, default=list) == \
        json.dumps(many, sort_keys=True, default=list)
