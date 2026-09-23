"""The project config on the outputs main added after it: content-free outputs
and mode receipts.

A terminology rule id names a term the text holds, so every content-free output
keys it by category. A config glob may name a mode, and a receipt then records
that mode, so verify replays the same screening. Each test has a control.
Uses a project-local temp dir (tmp_path symlinks are denied on the Windows host).
"""
import json
import os
import shutil

import pytest

from articulate import cli, project, receipt

_TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_tmp_project_outputs")
CONFIG = {
    "version": 1,
    "profiles": {"memos/**": "memo/argue"},
    "terminology": {"banned": [{"term": "whitelist", "suggestion": "allowlist"}]},
}
BANNED_TEXT = "Add the host to the whitelist before you deploy.\n"


@pytest.fixture()
def work():
    shutil.rmtree(_TMP, ignore_errors=True)
    os.makedirs(os.path.join(_TMP, "memos"))
    with open(os.path.join(_TMP, project.CONFIG_NAME), "w", encoding="utf-8") as fh:
        json.dump(CONFIG, fh)
    yield _TMP
    shutil.rmtree(_TMP, ignore_errors=True)


def _write(work, rel, text):
    p = os.path.join(work, rel)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)
    return p


def test_a_content_free_receipt_keys_a_project_term_by_category(work):
    cfg = project.for_path(_write(work, "a.md", BANNED_TEXT))
    full = receipt.make_receipt(BANNED_TEXT, "flavored", config=cfg)
    assert "terminology/banned/whitelist" in {f["rule_id"] for f in full["findings"]}
    free = receipt.make_receipt(BANNED_TEXT, "flavored", redact="drop", config=cfg)
    ids = {f["rule_id"] for f in free["findings"]}
    assert "terminology" in ids and not any("whitelist" in i for i in ids)
    assert receipt.verify_receipt(free, BANNED_TEXT)[0] == "Match"


def test_check_content_free_keys_a_project_term_by_category(work, capsys):
    path = _write(work, "a.md", BANNED_TEXT)
    cli.main(["check", path, "--json"])
    shown = json.loads(capsys.readouterr().out)["results"][0]
    assert "terminology/banned/whitelist" in shown["rule_counts"]
    cli.main(["check", path, "--json", "--content-free"])
    out = capsys.readouterr().out
    free = json.loads(out)["results"][0]
    assert free["rule_counts"].get("terminology") == 1
    assert "whitelist" not in out.replace(os.path.basename(path), "")


def test_a_config_glob_that_names_a_mode_gives_a_mode_receipt(work, capsys):
    memo = _write(work, os.path.join("memos", "q3.md"), BANNED_TEXT)
    assert cli.main(["receipt", memo]) == 0
    rec = json.loads(capsys.readouterr().out)
    assert rec["mode"] == "memo/argue" and rec["profile"] != "memo/argue"
    assert receipt.verify_receipt(rec, BANNED_TEXT)[0] == "Match"
    # Control: a file outside the glob gets a profile receipt with no mode.
    other = _write(work, "b.md", BANNED_TEXT)
    assert cli.main(["receipt", other]) == 0
    assert "mode" not in json.loads(capsys.readouterr().out)
