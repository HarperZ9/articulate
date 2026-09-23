"""Drafting provenance: an append-only, hash-chained record of drafts.

Every tamper case has an untouched control that verifies intact, so a pass
cannot come from a verifier that rejects everything. One test pins the limit the
docs state: deleting the tail leaves a valid, shorter chain.
"""
import json
import os
import shutil
from datetime import datetime, timedelta, timezone

import pytest

from articulate import cli, detector, drafts

_TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_tmp_drafts")
T0 = datetime(2026, 9, 23, 9, 0, tzinfo=timezone.utc)
V1 = "A first rough draft of the note.\n"
V2 = "A first rough draft of the note.\nIt gained a second line.\n"
V3 = "A tighter note.\nIt gained a second line.\n"


@pytest.fixture()
def doc():
    shutil.rmtree(_TMP, ignore_errors=True)
    os.makedirs(_TMP)
    path = os.path.join(_TMP, "note.md")
    yield path
    shutil.rmtree(_TMP, ignore_errors=True)


def _record_three(path, **kw):
    out = []
    for i, text in enumerate((V1, V2, V3)):
        entry, why = drafts.record(path, text, actor="alice", now=T0 + timedelta(hours=i), **kw)
        assert why is None
        out.append(entry)
    return out


def _lines(path):
    log, _ = drafts.paths(path)
    with open(log, encoding="utf-8") as fh:
        return fh.read().splitlines()


def _rewrite(path, lines):
    log, _ = drafts.paths(path)
    with open(log, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")


def test_records_chain_and_measure_each_draft(doc):
    e1, e2, e3 = _record_three(doc)
    assert [e["seq"] for e in (e1, e2, e3)] == [1, 2, 3]
    assert e1["prev"] == drafts.GENESIS and e2["prev"] == e1["hash"] and e3["prev"] == e2["hash"]
    assert e1["diff"] is None
    assert e2["diff"] == {"lines_added": 1, "lines_removed": 0, "chars_delta": len(V2) - len(V1)}
    assert e3["diff"]["lines_added"] == 1 and e3["diff"]["lines_removed"] == 1
    assert e3["actor"] == "alice" and e3["words"] > 0


def test_unchanged_text_records_nothing(doc):
    drafts.record(doc, V1)
    entry, why = drafts.record(doc, V1)
    assert entry is None and "unchanged" in why and len(_lines(doc)) == 1


def test_untouched_log_verifies_intact(doc):
    _record_three(doc)
    rep = drafts.verify(doc, V3)
    assert rep["verdict"] == "intact" and rep["drafts"] == 3 and rep["problems"] == []
    assert any("matches the last recorded draft" in n for n in rep["notes"])


def _edit_entry(doc, index, rehash, **changes):
    lines = _lines(doc)
    e = json.loads(lines[index])
    e.update(changes)
    if rehash:
        e["hash"] = drafts.entry_hash(e)
    lines[index] = json.dumps(e, sort_keys=True)
    _rewrite(doc, lines)


@pytest.mark.parametrize("rehash,needle", [
    (False, "does not match its hash"),
    (True, "does not link to the entry before it"),
])
def test_an_edited_entry_breaks_the_chain(doc, rehash, needle):
    _record_three(doc)
    _edit_entry(doc, 1, rehash, words=999)
    rep = drafts.verify(doc)
    assert rep["verdict"] == "broken" and any(needle in p for p in rep["problems"])


def test_a_removed_middle_entry_breaks_the_chain(doc):
    _record_three(doc)
    lines = _lines(doc)
    _rewrite(doc, [lines[0], lines[2]])
    assert drafts.verify(doc)["verdict"] == "broken"


def test_an_altered_or_missing_snapshot_is_caught(doc):
    e1, _e2, _e3 = _record_three(doc)
    _, objects = drafts.paths(doc)
    obj = os.path.join(objects, e1["text_sha256"].split(":")[1] + ".txt")
    with open(obj, "w", encoding="utf-8") as fh:
        fh.write("something else\n")
    assert any("altered" in p for p in drafts.verify(doc)["problems"])
    os.remove(obj)
    assert any("missing" in p for p in drafts.verify(doc)["problems"])


def test_a_deleted_tail_is_not_detectable_from_the_log_alone(doc):
    _record_three(doc)
    _rewrite(doc, _lines(doc)[:2])
    rep = drafts.verify(doc, V3)
    assert rep["verdict"] == "intact" and rep["drafts"] == 2
    assert any("differs from the last recorded draft" in n for n in rep["notes"])


def test_hash_only_mode_stores_no_text(doc):
    _record_three(doc, snapshot=False)
    _, objects = drafts.paths(doc)
    assert not os.path.isdir(objects)
    assert drafts.verify(doc)["verdict"] == "intact"
    assert json.loads(_lines(doc)[1])["diff"] is None


def test_a_broken_log_is_never_extended(doc):
    _record_three(doc)
    _edit_entry(doc, 0, False, words=1)
    with pytest.raises(drafts.LogBroken):
        drafts.record(doc, "A new draft.\n")
    assert len(_lines(doc)) == 3


def test_clock_and_ruleset_changes_are_notes(doc, monkeypatch):
    drafts.record(doc, V1, now=T0)
    drafts.record(doc, V2, now=T0 - timedelta(hours=1))
    monkeypatch.setattr(detector, "ruleset_fingerprint", lambda: "sha256:other")
    rep = drafts.verify(doc)
    assert rep["verdict"] == "intact"
    assert any("goes backwards" in n for n in rep["notes"])
    assert any("another ruleset" in n for n in rep["notes"])


def test_cli_record_show_verify(doc, capsys):
    with open(doc, "w", encoding="utf-8") as fh:
        fh.write(V1)
    assert cli.main(["drafts", "record", doc, "--actor", "alice"]) == 0
    with open(doc, "w", encoding="utf-8") as fh:
        fh.write(V2)
    assert cli.main(["drafts", "record", doc]) == 0
    assert "+1/-0 lines" in capsys.readouterr().out
    assert cli.main(["drafts", "show", doc, "--json"]) == 0
    assert len(json.loads(capsys.readouterr().out)["entries"]) == 2
    assert cli.main(["drafts", "verify", doc]) == 0
    _edit_entry(doc, 0, False, actor="mallory")
    assert cli.main(["drafts", "verify", doc]) == 1
    assert cli.main(["drafts", "verify", os.path.join(_TMP, "other.md")]) == 2
