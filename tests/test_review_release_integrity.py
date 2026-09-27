"""Correctness review of the 0.6.0 release check (PR 9, decision 1).

Each test states an invariant that decision 1 asks the check to hold: a changed
ruleset ships only with passing receipts, and an override never ships a
regression. At 35f4f8a the check breaks each invariant below. The cases are
synthetic edits of a committed receipt; nothing here measures any group.

The fingerprint test is marked strict xfail: fixing it moves the fingerprint,
which is a ruleset-identity change and belongs with the next ruleset. The
others need no ruleset change and fail until the check is fixed.
"""
import copy
import json
import pathlib
import re

import pytest

import articulate
from articulate import fairness, fairness_release, fingerprint, lexicon, logical, markup, masking

ROOT = pathlib.Path(__file__).resolve().parent.parent
NEW_FP = "sha256:" + "ab" * 8
OLD_FP = "sha256:" + "cd" * 8
FIRST_RUN = "sha256-22a7b980e3dba991.json"   # committed, with real failing rows


def _receipt():
    return json.loads((ROOT / "fairness" / "receipts" / FIRST_RUN).read_text("utf-8"))


def _all_pass(rec):
    rec = copy.deepcopy(rec)
    for v in rec["results"].values():
        v["g4"]["changed"] = 0
        for c in v["comparisons"].values():
            c["g1"]["pass"] = True
            for row in c["g2"].values():
                row["pass"] = True
    return rec


def _as(rec, fp):
    rec = copy.deepcopy(rec)
    rec["ruleset_version"] = fp
    rec["gates"] = fairness._gate_summary(rec["results"], fairness.bound_profiles())
    return rec


def _stem(fp):
    return fp.replace(":", "-")


@pytest.fixture
def one_manifest(monkeypatch):
    """Only the Liang et al. manifest is required; the current ruleset is NEW_FP."""
    man = _receipt()["manifest_sha256"]
    req = {man: fairness_release.REQUIREMENTS[man]}
    monkeypatch.setattr(fairness_release, "REQUIREMENTS", req)
    monkeypatch.setattr(fairness_release, "RELEASE_MANIFESTS", tuple(req))
    monkeypatch.setattr(fairness_release, "ruleset_fingerprint", lambda: NEW_FP)
    return man


def _publish(tmp_path, version, fp, receipts=()):
    (tmp_path / "published-ruleset.json").write_text(json.dumps(
        {"package_version": version, "ruleset_version": fp, "receipts": list(receipts)}))


# --- C-1: the release commit's own record skips every gate ------------------ #

def test_a_record_written_by_the_release_commit_does_not_skip_the_gates(tmp_path,
                                                                         one_manifest):
    # Decision 1 and publish.yml: "the release commit updates" the record. On
    # that commit the record already names the ruleset being released, so it
    # is no evidence that the ruleset was published before. With no receipt at
    # all the check must fail; today it prints "ruleset unchanged" and passes.
    receipts = tmp_path / "receipts"
    receipts.mkdir()
    _publish(tmp_path, articulate.__version__, NEW_FP, [f"{_stem(NEW_FP)}.json"])
    ok, lines = fairness_release.release_check(str(receipts))
    assert not ok, lines


def test_control_a_record_from_an_earlier_release_still_skips_the_gates(tmp_path,
                                                                          one_manifest):
    # The security-fix path decision 1 keeps: the ruleset shipped in an
    # earlier package, and this release does not change it.
    receipts = tmp_path / "receipts"
    receipts.mkdir()
    _publish(tmp_path, "0.0.1", NEW_FP)
    ok, lines = fairness_release.release_check(str(receipts))
    assert ok and "gates not re-run" in lines[0], lines


# --- C-4: an override excuses a failing profile the old receipt lacked ------- #

def test_an_override_does_not_excuse_a_newly_bound_profile_that_fails(tmp_path, monkeypatch,
                                                                     one_manifest):
    # A ruleset change that binds a new profile (a new path rule, say) sends
    # writers to it. If its rows fail, those writers meet a failing gate that
    # the published ruleset did not have: a regression the override must refuse.
    bound = fairness.bound_profiles() + ["newly-bound"]
    monkeypatch.setattr(fairness, "bound_profiles", lambda: list(bound))
    new = _all_pass(_receipt())
    extra = copy.deepcopy(next(iter(new["results"].values())))
    extra["profiles"] = ["newly-bound"]
    for c in extra["comparisons"].values():
        c["g1"]["pass"] = False
    new["results"]["config-new"] = extra
    new["bound_profiles"] = bound
    new["measured_profiles"] = sorted(set(new["measured_profiles"]) | {"newly-bound"})
    receipts = tmp_path / "receipts"
    receipts.mkdir()
    (receipts / f"{_stem(NEW_FP)}.json").write_text(json.dumps(_as(new, NEW_FP)))
    (receipts / f"{_stem(OLD_FP)}.json").write_text(
        json.dumps(_as(_all_pass(_receipt()), OLD_FP)))
    _publish(tmp_path, "0.0.1", OLD_FP, [f"{_stem(OLD_FP)}.json"])
    (receipts / f"{_stem(NEW_FP)}.override.json").write_text(json.dumps(
        {"ruleset_version": NEW_FP, "reason": "ship it", "decided_by": "maintainer"}))
    ok, lines = fairness_release.release_check(str(receipts))
    assert not ok, lines


# --- C-5: a second receipt from the same manifest is read or ignored by name - #

def test_a_second_receipt_from_the_same_manifest_is_not_ignored(tmp_path, one_manifest):
    # Two receipts for one ruleset and one manifest: the check reads the one
    # whose name sorts first and never opens the other. A failing receipt
    # must not be hidden behind a passing one.
    receipts = tmp_path / "receipts"
    receipts.mkdir()
    (receipts / f"{_stem(NEW_FP)}-rerun.json").write_text(
        json.dumps(_as(_all_pass(_receipt()), NEW_FP)))
    (receipts / f"{_stem(NEW_FP)}.json").write_text(json.dumps(_as(_receipt(), NEW_FP)))
    ok, lines = fairness_release.release_check(str(receipts))
    assert not ok, lines


# --- C-6: the fingerprint leaves out constants that decide blocking --------- #

# Each decides which text the blocking rules read: quote, URL, tag, code and
# LaTeX masks, fenced lines, sentence starts, and which lines join a paragraph.
BLOCKING_PATTERNS = [
    (masking, "QUOTED_PATTERN"), (masking, "URL_PATTERN"), (masking, "TAG_PATTERN"),
    (markup, "INLINE_CODE"), (markup, "TEX"), (markup, "FENCE"),
    (logical, "SENTENCE_END"), (lexicon, "HEADING"), (lexicon, "BULLET"),
]


def _edited(value):
    """The same pattern with a regex comment appended: any edit of the source
    changes the pattern string this way, whatever it does to matching."""
    if isinstance(value, str):
        return value + "(?#edited)"
    return re.compile(value.pattern + "(?#edited)", value.flags)


@pytest.mark.xfail(strict=True, reason="REVIEW-correctness C-6: moves the fingerprint; "
                                       "land with the next ruleset")
@pytest.mark.parametrize("module,name", BLOCKING_PATTERNS,
                         ids=[f"{m.__name__.rsplit('.', 1)[-1]}.{n}" for m, n in BLOCKING_PATTERNS])
def test_every_pattern_that_decides_blocking_moves_the_fingerprint(monkeypatch, module, name):
    # Since decision 1, an unchanged fingerprint skips every gate. An edit to
    # any of these patterns changes blocking, so it must move the fingerprint,
    # or a release with new blocking behavior passes as "ruleset unchanged".
    before = fingerprint.ruleset_fingerprint()
    monkeypatch.setattr(module, name, _edited(getattr(module, name)))
    assert fingerprint.ruleset_fingerprint() != before, name
