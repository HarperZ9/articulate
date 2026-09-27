"""A content-free output carries no word of the text.

Two notes put words from the text into their rule id: the repeated-phrase note
quotes the phrase and the repeated-opener note quotes the opener. Every
content-free path keys them by category instead, as the fairness harness does:
`check --content-free` (console, JSON, SARIF, per-paragraph counts) and
`receipt --redact drop|hash`, with and without `--spans`. A redacted receipt
still replays to Match.
"""
import json

import pytest

from articulate import check_text, cli, receipt

TEXT = ("Zebras graze near the quarterly marmalade budget ledger each spring. "
        "Zebras rest near the quarterly marmalade budget ledger in summer. "
        "Zebras drink near the quarterly marmalade budget ledger at dusk. "
        "Zebras sleep near the quarterly marmalade budget ledger at night.\n")
WORDS = ("zebras", "quarterly", "marmalade", "ledger")


@pytest.fixture()
def doc(tmp_path):
    path = tmp_path / "notes.md"
    path.write_text(TEXT, encoding="utf-8")
    return str(path)


def _leaks(out):
    low = out.lower()
    return [w for w in WORDS if w in low]


def test_control_the_two_notes_quote_the_text_in_a_full_result():
    ids = [f["rule_id"] for f in check_text(TEXT, house_notes=False)["low"]]
    assert any("zebras" in i for i in ids) and any("quarterly" in i for i in ids)


@pytest.mark.parametrize("flags", [["--json"], ["--sarif"], ["--json", "--spans"],
                                   ["--spans"], ["--verbose"]])
def test_check_content_free_carries_no_word_of_the_text(doc, capsys, flags):
    assert cli.main(["check", doc, "--content-free", *flags]) == 0
    out = capsys.readouterr().out
    assert _leaks(out) == [], out


def test_check_content_free_json_keys_the_notes_by_category(doc, capsys):
    cli.main(["check", doc, "--content-free", "--json"])
    r = json.loads(capsys.readouterr().out)["results"][0]
    assert {f["rule_id"] for f in r["low"]} >= {"anaphora", "ngram-repetition"}
    assert r["rule_counts"]["anaphora"] == 1 and r["rule_counts"]["ngram-repetition"] == 1


@pytest.mark.parametrize("mode", ["drop", "hash"])
@pytest.mark.parametrize("spans", [False, True])
def test_a_redacted_receipt_carries_no_word_and_still_matches(mode, spans):
    rec = receipt.make_receipt(TEXT, per_span=spans, redact=mode)
    assert _leaks(json.dumps(rec)) == []
    assert receipt.verify_receipt(rec, TEXT)[0] == "Match"


def test_control_a_full_receipt_keeps_the_rule_ids():
    rec = receipt.make_receipt(TEXT, per_span=True)
    assert "zebras" in json.dumps(rec).lower()
    assert receipt.verify_receipt(rec, TEXT)[0] == "Match"
