"""Defaults the PR 9 record confirms (decisions 4 and 5).

These tests pin the defaults so a later change has to move them on purpose.
They measure nothing about fairness.
"""
import json

from articulate.cli import main


def _check_json(tmp_path, capsys, name, text, *extra):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    capsys.readouterr()
    main(["check", str(path), "--json", *extra])
    (result,) = json.loads(capsys.readouterr().out)["results"]
    return result


def _cats(result):
    return {f["category"] for t in ("high", "medium", "low") for f in result[t]}


# --- decision 4: house notes hidden by default ------------------------------ #

HOUSE_TEXT = "The results were really clear to everyone in the room.\n"


def test_check_hides_house_notes_by_default(tmp_path, capsys):
    result = _check_json(tmp_path, capsys, "notes.md", HOUSE_TEXT)
    assert result["profile"] == "flavored"
    assert "intensifier" not in _cats(result)
    assert not [f for t in ("high", "medium", "low") for f in result[t] if f["house"]]


def test_house_notes_show_when_the_writer_asks(tmp_path, capsys):
    result = _check_json(tmp_path, capsys, "notes.md", HOUSE_TEXT, "--house-notes")
    (f,) = [f for f in result["low"] if f["category"] == "intensifier"]
    assert f["house"] is True and f["gates"] is False


# --- decision 5: `.tex` resolves to `research` ------------------------------ #

TEX = "We sampled twice due to the fact that the first run failed.\n"


def test_a_tex_file_resolves_to_research(tmp_path, capsys):
    from articulate import profiles
    assert profiles.profile_for("thesis/chapter1.tex") == "research"
    result = _check_json(tmp_path, capsys, "chapter1.tex", TEX)
    assert result["profile"] == "research"
    assert result["gate"] == "ok"      # research blocks only the HIGH tier


def test_a_tex_file_can_name_the_strict_essay_profile(tmp_path, capsys):
    result = _check_json(tmp_path, capsys, "chapter1.tex",
                         "% writing-profile: essay\n" + TEX)
    assert result["profile"] == "essay"
    assert result["gate"] == "blocked"
