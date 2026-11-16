"""The outbound check ranks a model rewrite further from a human reference than
the human piece, loses that ranking when the reference is swapped, and stays
silent on a register the reader shares."""
import ast
import json
import pathlib

import pytest

from articulate import local_mcp, outbound, voice, voice_identity, voice_store
from articulate import outbound_features as of
from outbound_fixtures import FORMAL, FORMAL_DRAFT, HUMAN, REWRITE

SRC = pathlib.Path(outbound.__file__).parent


def _far(report):
    return len(report["outside_author"])


def _rewrite_ranked_further(base, i):
    """Leave pair i out, build the reference from the rest of base, compare both."""
    ref = outbound.reference([t for j, t in enumerate(base) if j != i], basis="test")
    return _far(outbound.compare(REWRITE[i], ref)) > _far(outbound.compare(HUMAN[i], ref))


@pytest.mark.parametrize("i", range(len(HUMAN)))
def test_rewrite_is_further_from_the_human_reference(i):
    assert _rewrite_ranked_further(HUMAN, i)


@pytest.mark.parametrize("i", range(len(HUMAN)))
def test_planted_bad_control_swapped_reference_loses_the_ranking(i):
    # Built from the rewrites, the reference must not rank the rewrite further.
    # If it did, the ranking above would come from the features, not the reference.
    assert not _rewrite_ranked_further(REWRITE, i)


def test_rewrite_findings_lean_toward_model_shape():
    ref = outbound.reference(HUMAN[:5], basis="test")
    found = {f["feature"] for f in outbound.compare(REWRITE[5], ref)["findings"]}
    assert {"proper_names_per_100", "numbers_per_100", "opener", "signoff"} <= found
    assert outbound.compare(HUMAN[5], ref)["findings"] == []


def test_more_numbers_than_the_reference_is_listed_but_not_a_finding():
    ref = outbound.reference(REWRITE, basis="test")
    report = outbound.compare(HUMAN[0], ref)
    assert "numbers_per_100" in report["outside_author"]
    assert "numbers_per_100" not in {f["feature"] for f in report["findings"]}


def test_shared_register_is_not_flagged_when_the_reader_shares_it():
    author = outbound.reference(HUMAN, basis="author")
    reader = outbound.reference(FORMAL, basis="recipient-messages")
    assert reader["samples"] == 3
    alone = {f["feature"] for f in outbound.compare(FORMAL_DRAFT, author)["findings"]}
    both = {f["feature"] for f in outbound.compare(FORMAL_DRAFT, author, reader)["findings"]}
    # The control is live: against the author alone, tell 1 fires.
    assert "noun_carry" in alone
    assert "noun_carry" not in both
    assert not {"greeting", "signoff"} & both


def test_finding_carries_its_line():
    ref = outbound.reference(HUMAN, basis="test")
    draft = "Hi Ana,\nThanks for the note.\n\nOne small thing I noticed: the totals differ.\nBest,\nSam"
    report = outbound.compare(draft, ref)
    by = {f["feature"]: f for f in report["findings"]}
    assert by["softener_per_100"]["line"] == 4
    assert "One small thing" in by["softener_per_100"]["excerpt"]
    assert by["opener"]["line"] == 2 and by["signoff"]["excerpt"] == "Best"


def test_body_strips_greeting_and_signoff_inline_and_multiline():
    assert of.body("Hey Joe, Got it. Zain")[2:] == ("Hey Joe,", None)
    assert of.body("Hi Joe, Thanks. All good. Cheers, Zain")[2:] == ("Hi Joe,", "Cheers")
    core, offset, greeting, signoff = of.body("Hey Ana,\nGot it.\n\nCheers,\nZain")
    assert (core, offset, greeting, signoff) == ("Got it.", 1, "Hey Ana,", "Cheers")


def test_outbound_never_imports_the_house_rules_or_the_linter():
    # Rule: text in the author's voice is not run through the house style. The
    # mechanism is that the check's modules cannot reach those rules.
    allowed = {"outbound_features", "corpus_features", "wordlists"}
    for name in ("outbound.py", "outbound_features.py"):
        tree = ast.parse((SRC / name).read_text(encoding="utf-8"))
        local = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom) and n.level:
                local |= {n.module} if n.module else {a.name for a in n.names}
        assert local <= allowed, (name, local - allowed)
    report = outbound.compare(REWRITE[0], outbound.reference(HUMAN, basis="t"))
    assert report["house_rules_applied"] is False and report["ai_detector_consulted"] is False


def test_profile_carries_outbound_rows_and_no_text():
    profile = voice.build_profile(HUMAN)
    rows = profile["outbound"]["rows"]
    assert len(rows) == len(HUMAN)
    flat = json.dumps(profile["outbound"])
    assert "Anacortes" not in flat and "ferry" not in flat


def _store(tmp_path):
    voice_identity.ensure_identity(tmp_path)
    profile = voice_identity.bind(voice.build_profile(HUMAN), tmp_path)
    voice_store.save(profile, "mine", tmp_path)


def test_cli_outbound_reads_recipient_file(tmp_path, capsys):
    from articulate import cli
    _store(tmp_path)
    draft, reader = tmp_path / "draft.txt", tmp_path / "reader.txt"
    draft.write_text(FORMAL_DRAFT, encoding="utf-8")
    reader.write_text(FORMAL, encoding="utf-8")
    code = cli.main(["voice", "outbound", str(draft), "--author", "mine", "--recipient",
                     str(reader), "--dir", str(tmp_path), "--json"])
    assert code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["recipient_given"] is True
    assert "noun_carry" not in {f["feature"] for f in report["findings"]}


def test_mcp_voice_outbound(tmp_path, monkeypatch):
    monkeypatch.setenv("ARTICULATE_VOICE_DIR", str(tmp_path))
    _store(tmp_path)
    response = local_mcp.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
        "name": "voice_outbound", "arguments": {"text": REWRITE[0], "voice_name": "mine"}}})
    report = json.loads(response["result"]["content"][0]["text"])
    assert report["schema"] == outbound.REPORT_SCHEMA and report["findings"]
