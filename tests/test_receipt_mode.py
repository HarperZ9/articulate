"""`articulate receipt --mode` records the mode it screened under, and verify
replays the receipt under that same mode.

academic/argue promotes unsupported-authority to a gate category, so the text
below reads `blocked` under the mode and `ok` under its base profile, research.
A receipt that dropped the mode would record a screening the author never ran.
"""
import io
import json
import os
import shutil
from contextlib import redirect_stdout

import pytest

from articulate import receipt
from articulate.cli import main as cli_main

MODE = "academic/argue"
TEXT = ("Studies show the method works across 42 plots in every season we measured, "
        "and the gains hold under drought and flood alike.\n")

_TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_tmp_rmode")


@pytest.fixture()
def work():
    os.makedirs(_TMP, exist_ok=True)
    yield _TMP
    shutil.rmtree(_TMP, ignore_errors=True)


def _cli(argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = cli_main(argv)
    return code, buf.getvalue()


def _src(work):
    p = os.path.join(work, "paper.md")
    with open(p, "w", encoding="utf-8", newline="") as fh:
        fh.write(TEXT)
    return p


def test_premise_mode_and_base_profile_disagree():
    assert receipt.make_receipt(TEXT, "research")["gate"] == "ok"


def test_library_receipt_records_the_mode():
    rec = receipt.make_receipt(TEXT, mode=MODE)
    assert rec["mode"] == MODE
    assert rec["profile"] == "research"          # the mode's base profile
    assert rec["gate"] == "blocked"


def test_library_mode_receipt_replays_to_match():
    rec = receipt.make_receipt(TEXT, mode=MODE)
    verdict, detail = receipt.verify_receipt(rec, TEXT)
    assert verdict == "Match", detail


def test_mode_receipt_with_an_unknown_mode_is_unverifiable():
    rec = receipt.make_receipt(TEXT, mode=MODE)
    rec["mode"] = "no-such/mode"
    verdict, _ = receipt.verify_receipt(rec, TEXT)
    assert verdict == "Unverifiable"


@pytest.mark.parametrize("bad", ["", 7, ["academic/argue"]])
def test_mode_receipt_with_a_malformed_mode_is_unverifiable(bad):
    rec = receipt.make_receipt(TEXT, mode=MODE)
    rec["mode"] = bad
    verdict, _ = receipt.verify_receipt(rec, TEXT)
    assert verdict == "Unverifiable"


def test_mode_receipt_whose_profile_is_not_the_mode_base_is_unverifiable():
    rec = receipt.make_receipt(TEXT, mode=MODE)
    rec["profile"] = "flavored"
    verdict, detail = receipt.verify_receipt(rec, TEXT)
    assert verdict == "Unverifiable"
    assert "base" in detail


def test_stripping_the_mode_from_a_receipt_does_not_match():
    rec = receipt.make_receipt(TEXT, mode=MODE)
    del rec["mode"]
    verdict, _ = receipt.verify_receipt(rec, TEXT)
    assert verdict == "Drift"


def test_cli_receipt_honors_mode(work):
    src = _src(work)
    code, out = _cli(["receipt", src, "--mode", MODE])
    assert code == 0
    rec = json.loads(out)
    assert rec["mode"] == MODE
    assert rec["gate"] == "blocked"


def test_cli_mode_receipt_verifies(work):
    src = _src(work)
    _, out = _cli(["receipt", src, "--mode", MODE])
    rpath = os.path.join(work, "paper.receipt.json")
    with open(rpath, "w", encoding="utf-8") as fh:
        fh.write(out)
    code, printed = _cli(["verify", rpath, src])
    assert code == 0, printed
    assert "Match" in printed


def test_cli_receipt_rejects_an_unknown_mode(work):
    src = _src(work)
    code, out = _cli(["receipt", src, "--mode", "no-such/mode"])
    assert code == 2
    assert out == ""


def test_cli_receipt_without_mode_is_unchanged(work):
    src = _src(work)
    _, out = _cli(["receipt", src, "--profile", "research"])
    rec = json.loads(out)
    assert "mode" not in rec
    assert rec["profile"] == "research" and rec["gate"] == "ok"
