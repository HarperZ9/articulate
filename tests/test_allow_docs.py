"""C5a: `writing-allow` is documented, with its scope and its leak.

The directive keeps a writer's terms of art. It was undocumented, so a writer
could not know that it reads only the first 15 lines, matches by substring,
applies to the whole file and leaves the contrast and cadence devices alone.
These tests pin the documented behavior and check that the README, the feature
reference and `check --help` all state it.
"""
import pathlib

import pytest

from articulate import check_text, cli, profiles

ROOT = pathlib.Path(__file__).resolve().parent.parent
LINE = "Our revolutionary platform ships today."


def _medium(text):
    r = check_text(text, profile=profiles.load("essay"), house_notes=False)
    return [f["category"] for f in r["medium"]]


def test_an_allowed_term_clears_the_finding_for_the_whole_file():
    assert _medium(LINE) == ["marketing"]
    assert _medium(f"<!-- writing-allow: revolutionary -->\n\n{LINE}\n") == []


def test_the_directive_is_read_only_in_the_first_15_lines():
    late = "\n" * 15 + "<!-- writing-allow: revolutionary -->\n"
    assert _medium(f"{LINE}\n{late}") == ["marketing"]


def test_the_match_is_a_substring_so_a_short_term_leaks():
    # The documented leak: allowing a period name's first word clears the
    # marketing use of the same word elsewhere in the file.
    text = ("<!-- writing-allow: revolutionary -->\n\nThe Revolutionary War ended in "
            "1783. Our new archive tool is revolutionary.\n")
    assert _medium(text) == []


def test_the_devices_ignore_the_list():
    text = "<!-- writing-allow: drill -->\n\nIt was not a drill, but a warning.\n"
    r = check_text(text, profile=profiles.load("house"))
    assert "antithesis" in [f["category"] for f in r["high"]]


@pytest.mark.parametrize("doc", ["README.md", "docs/features.md"])
def test_the_docs_state_scope_and_leak(doc):
    text = (ROOT / doc).read_text(encoding="utf-8")
    assert "writing-allow" in text
    for fact in ("first 15 lines", "substring", "whole file"):
        assert fact in text, (doc, fact)


def test_check_help_states_scope_and_leak(capsys):
    with pytest.raises(SystemExit):
        cli.main(["check", "--help"])
    out = " ".join(capsys.readouterr().out.split())
    for fact in ("first 15 lines", "substring", "whole file"):
        assert fact in out, fact


def test_the_list_reaches_the_high_tier_as_documented():
    # The documented reach: an allowed term clears a HIGH finding too, so a CI
    # owner must review the list. The em dash ignores it (control).
    default = profiles.load("flavored")
    line = "As an AI language model, I cannot browse the web.\n"
    assert check_text(line, profile=default, house_notes=False)["gate"] == "blocked"
    allowed = "<!-- writing-allow: language model -->\n" + line
    assert check_text(allowed, profile=default, house_notes=False)["gate"] == "ok"
    dash = "<!-- writing-allow: text -->\n\nSome text—more text.\n"
    assert "em-dash" in [f["category"] for f in check_text(dash, profile=profiles.load(
        "house"))["high"]]


@pytest.mark.parametrize("doc", ["README.md", "docs/features.md"])
def test_the_docs_state_that_the_list_reaches_the_high_tier(doc):
    text = " ".join((ROOT / doc).read_text(encoding="utf-8").split())
    assert "the HIGH tier included" in text and "review `writing-allow:` lines" in text
