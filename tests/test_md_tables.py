"""A Markdown table delimiter row is structure, never an em-dash.

Before this fix the inline "---" check read `|---|---|` as an em-dash and raised
a HIGH finding, so a Markdown paper with a table failed the gate under every
non-fiction profile. A real em-dash inside a table cell must still fire.
"""
import pytest

from articulate import detector, profiles

INTRO = ("The survey covered 42 plots across three counties in the spring of 2025, "
         "and the field team logged soil moisture at each one every week.\n\n")


def _findings(text, profile="research"):
    r = detector.check_text(text, profile=profiles.load(profile))
    return r, [f for f in r["high"] if f["category"] == "em-dash"]


@pytest.mark.parametrize("sep", [
    "|---|---|",
    "| --- | --- |",
    "|:---|---:|",
    "|:---:|:---:|",
    "---|---",
    "| --- |",
    "  |------|-----|  ",
])
def test_table_delimiter_row_is_not_an_em_dash(sep):
    table = f"| Site | Moisture |\n{sep}\n| North | 31% |\n"
    r, dashes = _findings(INTRO + table)
    assert dashes == [], dashes
    assert r["gate"] == "ok"


def test_em_dash_inside_a_table_cell_still_fires():
    table = "| Site | Note |\n|---|---|\n| North | wet — very wet |\n"
    _, dashes = _findings(INTRO + table)
    assert len(dashes) == 1
    assert dashes[0]["line"] == 5


def test_triple_hyphen_inside_a_table_cell_still_fires():
    table = "| Site | Note |\n|---|---|\n| North | wet --- very wet |\n"
    _, dashes = _findings(INTRO + table)
    assert len(dashes) == 1
    assert dashes[0]["line"] == 5


def test_prose_with_pipes_and_triple_hyphen_still_fires():
    # A line with a pipe that is not a delimiter row stays under the em-dash rule.
    text = INTRO + "Pipe a|b into the tool --- then read the result.\n"
    _, dashes = _findings(text)
    assert len(dashes) == 1


def test_is_md_table_sep_rejects_non_rows():
    assert not detector.is_md_table_sep("---")          # a thematic break, not a row
    assert not detector.is_md_table_sep("| a | b |")
    assert not detector.is_md_table_sep("a --- b | c")
    assert not detector.is_md_table_sep("|  |")
    assert detector.is_md_table_sep("|---|---|")
