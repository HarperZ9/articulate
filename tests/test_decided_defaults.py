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


# --- decision 8: `blocking` joins check JSON; `clean` is deprecated --------- #

def test_check_json_counts_blocking_findings_and_keeps_clean(tmp_path, capsys):
    text = "Certainly! Here is the essay you asked for:\n\nThe trial ended early.\n"
    result = _check_json(tmp_path, capsys, "a.md", text, "--profile", "essay")
    gating = [f for t in ("high", "medium", "low") for f in result[t] if f["gates"]]
    assert result["blocking"] == len(gating) >= 1
    assert result["gate"] == "blocked"
    # `clean` keeps its 0.5.0 meaning (no HIGH or MEDIUM finding) until 0.7.0.
    assert result["clean"] is (not (result["high"] or result["medium"]))


def test_blocking_is_zero_when_nothing_blocks(tmp_path, capsys):
    result = _check_json(tmp_path, capsys, "b.md", "The trial ended early.\n")
    assert result["blocking"] == 0 and result["gate"] == "ok"
    assert result["clean"] is True


def test_the_mcp_check_tool_keeps_clean_through_the_deprecation_window():
    # Decision 8 keeps `clean` for one minor version on every surface that had
    # it in 0.5.0; the MCP check tool returned it then.
    from articulate import check_text, mcp_server
    for text in ("The trial ended early.\n",
                 "Studies show that this approach is a game-changer.\n"):
        out = mcp_server.do_check(text)
        r = check_text(text, house_notes=False)
        assert out["clean"] is r["clean"]
        assert out["blocking"] == r["blocking"]


def test_clean_is_not_the_gate():
    # docs/cli.md: `clean` reads false for a MEDIUM-only text that the default
    # profile lets through, so its equal is `findings`, not the gate.
    from articulate import check_text
    r = check_text("Studies show that this approach is a game-changer.\n", house_notes=False)
    assert r["medium"] and not r["high"]
    assert (r["clean"], r["gate"], r["findings"]) == (False, "ok", "has_findings")
    assert r["blocking_count"] == r["blocking"] == 0
