"""The change report: sentence-level before/after pairs with the detector
findings and the meaning-guard rows attached to each pair.

Controls: unchanged sentences never appear, and a pair with no tell carries no
findings, so a report cannot pass by listing everything.
"""
import json
import os
import shutil
import sys

import pytest

from articulate import changes, editor, guard

_TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_tmp_changes")
ORIGINAL = ("# Notes\n\nThe build runs nightly. We leverage the cache to save time. "
            "Retry 3 times on failure.\n\n- Keep the logs.\n\n```\nmake test\n```\n")
FINAL = ("# Notes\n\nThe build runs nightly. We use the cache to save time. "
         "Retry 3 times on failure.\n\n- Keep the logs.\n\n```\nmake test\n```\n")


@pytest.fixture()
def work():
    os.makedirs(_TMP, exist_ok=True)
    yield _TMP
    shutil.rmtree(_TMP, ignore_errors=True)


def _texts(text):
    return [text[s:e] for s, e in changes.segments(text)]


def test_segments_split_sentences_and_blocks():
    assert _texts(ORIGINAL) == ["# Notes", "The build runs nightly.",
                                "We leverage the cache to save time.",
                                "Retry 3 times on failure.", "- Keep the logs.",
                                "```\nmake test\n```"]


def test_only_the_changed_sentence_is_reported_with_its_finding():
    rep = changes.build(ORIGINAL, FINAL)
    assert rep["summary"]["changes"] == 1
    change = rep["changes"][0]
    assert change["op"] == "replace"
    assert change["before"]["text"] == "We leverage the cache to save time."
    assert change["after"]["text"] == "We use the cache to save time."
    assert change["before"]["line_start"] == 3
    rules = {f["rule_id"].split("/")[0] for f in change["findings_before"]}
    assert "corporate-verb" in rules and change["findings_after"] == []
    assert rep["summary"]["meaning"] == "preserved" and change["meaning"] == []


def test_identical_text_has_no_changes():
    rep = changes.build(ORIGINAL, ORIGINAL)
    assert rep["changes"] == [] and rep["summary"]["changes"] == 0


def test_meaning_rows_attach_to_their_pair():
    rep = changes.build("Keep going. Retry 3 times.", "Keep going. Retry 5 times.")
    assert len(rep["changes"]) == 1
    assert rep["changes"][0]["meaning"] == ["changed number '3' (L1) -> '5' (L1)"]


def test_refusals_from_the_guard_are_reported():
    g = guard.RewriteGuard()
    with pytest.raises(guard.RewriteRefused):
        g.run(lambda t: "Retry 5 times.", "Retry 3 times.")
    rep = changes.build("Retry 3 times.", "Retry 3 times.", guard=g)
    assert rep["refusals"][0]["stage"] == "meaning"
    assert "changed number" in rep["refusals"][0]["blocking"][0]
    text = changes.format_report(rep)
    assert "refused a candidate" in text and "does not prove" in text


def test_editor_explain_prints_text_and_json(work, monkeypatch, capsys):
    src = os.path.join(work, "n.md")
    with open(src, "w", encoding="utf-8") as fh:
        fh.write(ORIGINAL)
    monkeypatch.setattr(editor, "claude_call", lambda instr, text: text.replace(
        "leverage", "use"))
    monkeypatch.setattr(sys, "argv", ["articulate.editor", "--fix", src, "--explain"])
    assert editor.main() == 0
    out = capsys.readouterr().out
    assert "flagged before: HIGH corporate-verb" in out and "+ We use the cache" in out
    monkeypatch.setattr(sys, "argv", ["articulate.editor", "--fix", src, "--explain", "json"])
    assert editor.main() == 0
    out = capsys.readouterr().out
    payload = json.loads(out[out.index("\n{") + 1:])
    assert payload["schema"] == changes.SCHEMA and payload["summary"]["changes"] == 1
    assert payload["out"].endswith("n.fixed.md")
