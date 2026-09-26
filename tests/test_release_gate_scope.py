"""The release gate scoped to ruleset changes (PR 9, decision 1).

- A ruleset equal to the last published one is not gated; the check says so.
- A changed ruleset must pass every gate on every required receipt.
- An override for one exact ruleset is accepted only when no gate row that
  passes in the published ruleset's receipt fails in the new one, and the
  check prints that comparison.

Synthetic edits of the committed receipt only; nothing here measures any group.
"""
import copy
import json
import pathlib
import re

import pytest

from articulate import fairness, fairness_release

ROOT = pathlib.Path(__file__).resolve().parent.parent
PUBLISHED = ROOT / "fairness" / "published-ruleset.json"
NEW_FP = "sha256:" + "ab" * 8
OLD_FP = "sha256:" + "cd" * 8


# The first run of ruleset 0.7.0, which failed G1 and G2: a committed receipt
# with real failing rows to build the synthetic cases from.
FIRST_RUN = "sha256-22a7b980e3dba991.json"


def _after():
    return json.loads((ROOT / "fairness" / "receipts" / FIRST_RUN).read_text("utf-8"))


def _as(rec, fp):
    rec = copy.deepcopy(rec)
    rec["ruleset_version"] = fp
    rec["gates"] = fairness._gate_summary(rec["results"], fairness.bound_profiles())
    return rec


def _all_pass(rec):
    rec = copy.deepcopy(rec)
    for v in rec["results"].values():
        v["g4"]["changed"] = 0
        for c in v["comparisons"].values():
            c["g1"]["pass"] = True
            for row in c["g2"].values():
                row["pass"] = True
    return rec


def _stem(fp):
    return fp.replace(":", "-")


@pytest.fixture
def layout(tmp_path, monkeypatch):
    """receipts/ plus a published record for OLD_FP, with the current ruleset
    fingerprint set to NEW_FP."""
    monkeypatch.setattr(fairness_release, "ruleset_fingerprint", lambda: NEW_FP)
    receipts = tmp_path / "receipts"
    receipts.mkdir()

    def write(new=None, published=None, override=None):
        if new is not None:
            (receipts / f"{_stem(NEW_FP)}.json").write_text(json.dumps(_as(new, NEW_FP)))
        if published is not None:
            (receipts / f"{_stem(OLD_FP)}.json").write_text(json.dumps(_as(published, OLD_FP)))
            (tmp_path / "published-ruleset.json").write_text(json.dumps({
                "package_version": "9.9.9", "ruleset_version": OLD_FP,
                "receipts": [f"{_stem(OLD_FP)}.json"]}))
        if override is not None:
            (receipts / f"{_stem(NEW_FP)}.override.json").write_text(json.dumps(
                {"ruleset_version": NEW_FP, "reason": override, "decided_by": "maintainer"}))
        return str(receipts)
    return write


def test_an_unchanged_ruleset_passes_with_a_note_and_no_receipt(tmp_path, monkeypatch):
    monkeypatch.setattr(fairness_release, "ruleset_fingerprint", lambda: OLD_FP)
    (tmp_path / "receipts").mkdir()
    (tmp_path / "published-ruleset.json").write_text(json.dumps(
        {"package_version": "9.9.9", "ruleset_version": OLD_FP, "receipts": []}))
    ok, lines = fairness_release.release_check(str(tmp_path / "receipts"))
    assert ok
    assert lines == [f"ruleset unchanged since 9.9.9 ({OLD_FP}); gates not re-run"]


def test_a_changed_ruleset_that_passes_every_gate_passes(layout):
    ok, lines = fairness_release.release_check(layout(new=_all_pass(_after()),
                                                      published=_after()))
    assert ok, lines


def test_a_changed_ruleset_with_a_failing_gate_fails_without_an_override(layout):
    rec = _after()
    assert not _as(rec, NEW_FP)["gates"]["release_ok"]     # control: it does fail
    ok, lines = fairness_release.release_check(layout(new=rec, published=rec))
    assert not ok and any("a release gate fails" in x for x in lines)


def test_an_override_with_no_regression_passes_and_prints_the_comparison(layout):
    rec = _after()
    ok, lines = fairness_release.release_check(
        layout(new=rec, published=rec, override="security patch"))
    assert ok, lines
    assert "security patch" in lines[0]
    text = "\n".join(lines)
    assert "comparison with the published ruleset 9.9.9" in text
    assert "0 pass before and fail now" in text


def test_an_override_that_hides_a_regression_is_refused(layout):
    rec = _after()
    ok, lines = fairness_release.release_check(
        layout(new=rec, published=_all_pass(rec), override="ship it"))
    assert not ok
    text = "\n".join(lines)
    assert "override refused" in text and "ship it" in text
    assert re.search(r"[1-9]\d* pass before and fail now", text)
    assert "G1 essay toefl-vs-abstracts" in text


def test_an_override_with_no_published_record_is_refused(layout):
    ok, lines = fairness_release.release_check(layout(new=_after(), override="why not"))
    assert not ok
    assert any("no published ruleset record" in x for x in lines)


def test_an_override_never_excuses_a_malformed_receipt(layout):
    rec = _after()
    rec["manifest_sha256"] = "sha256:" + "0" * 64
    ok, lines = fairness_release.release_check(
        layout(new=rec, published=_after(), override="security patch"))
    assert not ok and any("not a release manifest" in x for x in lines)


def test_gate_rows_name_the_gate_profile_and_comparison():
    rows = fairness_release.gate_rows(_after())
    assert rows["G1 essay toefl-vs-abstracts"] is False
    assert rows["G1 flavored toefl-vs-college"] is True
    assert rows["G4 flavored"] is True


def test_the_published_record_names_a_committed_release_receipt():
    pub = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    assert pub["package_version"] == "0.5.0"
    assert pub["receipts"]
    for name in pub["receipts"]:
        rec = json.loads((ROOT / "fairness" / "receipts" / name).read_text("utf-8"))
        assert rec["ruleset_version"] == pub["ruleset_version"]
        assert rec["manifest_sha256"] in fairness_release.RELEASE_MANIFESTS


def test_the_command_prints_the_unchanged_note(monkeypatch, capsys):
    pub = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    monkeypatch.setattr(fairness_release, "ruleset_fingerprint",
                        lambda: pub["ruleset_version"])
    code = fairness.main(["--release-check", str(ROOT / "fairness" / "receipts")])
    out = capsys.readouterr().out
    assert code == 0
    assert (f"ruleset unchanged since 0.5.0 ({pub['ruleset_version']}); gates not re-run"
            in out)
