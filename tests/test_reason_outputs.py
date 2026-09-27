"""C2: every output carries the reader-cost reason and the boundary line.

A finding list read without its reasons invites a reader to treat a count as a
verdict. So every finding in JSON carries its reason, `check --verbose` prints it
under the finding, every rule that can report has one (the n-gram note had
none), and the boundary sentence prints on every `check` run, a passing gate
included. Density and `score` say what they count.

These tests check that the words are present. They cannot check that a reason
is true; a second reader reviews the reasons before a release relies on them.
"""
import json

from articulate import check_text, cli, fingerprint, profiles, rule_reasons
from articulate.tool_text import DOES_NOT_PROVE

NEVER_REPORTED = {"prompt-injection"}   # the editor's warning; never in check_text


def test_every_reportable_category_is_house_or_reasoned():
    cats = fingerprint.known_categories() - NEVER_REPORTED
    missing = sorted(c for c in cats if not rule_reasons.is_house(c)
                     and rule_reasons.reason_for(c) is None)
    assert not missing, missing


def test_every_finding_in_json_carries_its_reason():
    text = ("Firstly, the plan failed. It is important to note that we need more data "
            "in order to decide. Studies show the cost rose.\n")
    r = check_text(text, profile=profiles.load("flavored"), house_notes=True)
    found = r["high"] + r["medium"] + r["low"]
    assert found
    for f in found:
        assert f["reason"].endswith("."), f["category"]
        if f["house"]:
            assert f["reason"] == rule_reasons.HOUSE_REASON and f["reason_source"] is None
        else:
            assert (f["reason"], f["reason_source"]) == rule_reasons.reason_for(f["category"])


def test_the_ngram_note_carries_a_reason():
    text = ("In my humble opinion we won. In my humble opinion it rained. "
            "In my humble opinion nobody cared.\n")
    r = check_text(text, profile=profiles.load("flavored"), house_notes=False)
    (f,) = [f for f in r["low"] if f["category"] == "ngram-repetition"]
    assert "key term" in f["reason"]


def _cli(capsys, *argv):
    rc = cli.main(list(argv))
    return rc, capsys.readouterr().out


def test_verbose_prints_the_reason_under_each_finding(tmp_path, capsys):
    p = tmp_path / "a.md"
    p.write_text("We need more data in order to decide.\n", encoding="utf-8")
    _rc, out = _cli(capsys, "check", str(p), "--verbose")
    lines = out.splitlines()
    i = next(n for n, ln in enumerate(lines) if "padded-purpose" in ln)
    assert lines[i + 1].strip().startswith("why: ")
    assert rule_reasons.reason_for("padded-purpose")[0] in lines[i + 1]


def test_the_boundary_line_prints_when_the_gate_is_ok(tmp_path, capsys):
    p = tmp_path / "a.md"
    p.write_text("The team met on Tuesday.\n", encoding="utf-8")
    q = tmp_path / "b.md"
    q.write_text("The team met on Wednesday.\n", encoding="utf-8")
    _rc, out = _cli(capsys, "check", str(p), str(q))
    assert "gate ok" in out and out.count(DOES_NOT_PROVE) == 1


def test_the_boundary_line_prints_once_when_blocked(tmp_path, capsys):
    p = tmp_path / "a.md"
    p.write_text("As an AI language model, I cannot give opinions.\n", encoding="utf-8")
    _rc, out = _cli(capsys, "check", str(p))
    assert "gate blocked" in out and out.count(DOES_NOT_PROVE) == 1


def test_json_output_carries_reasons(tmp_path, capsys):
    p = tmp_path / "a.md"
    p.write_text("We need more data in order to decide.\n", encoding="utf-8")
    _rc, out = _cli(capsys, "check", str(p), "--json")
    (res,) = json.loads(out)["results"]
    assert all(f["reason"] for f in res["low"])
    assert "does not show who or what wrote" in res["density"]["measures"]


def test_score_names_what_density_counts(tmp_path, capsys):
    p = tmp_path / "a.md"
    p.write_text("The team met on Tuesday.\n", encoding="utf-8")
    _rc, out = _cli(capsys, "score", str(p))
    assert "density counts the findings that block" in out and DOES_NOT_PROVE in out
