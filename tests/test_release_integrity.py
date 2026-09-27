"""The release check blocks honestly (PR 9, decision 1, and the amendment of 27
September 2026 in fairness/PREREG.md).

Each test states an invariant the check must hold:

- A published-ruleset record skips the gates only when it names an earlier
  package than the one being built. A release commit that writes its own record
  gets no pass from it.
- An override never ships a regression, a failing row the old receipt lacked
  included, and it compares only with a sound receipt of the published ruleset.
- One receipt per ruleset and manifest: a second one is never ignored by name.
- A stored flag never claims more than its stored numbers allow.
- A pinned receipt must match its pin.
- A confirmatory corpus confirms only the ruleset it was pre-registered for.

The cases are synthetic edits of committed receipts; nothing here measures any
group.
"""
import json
import pathlib
import shutil

import pytest
from receipt_fakes import all_pass, as_ruleset

import articulate
from articulate import fairness, fairness_release

ROOT = pathlib.Path(__file__).resolve().parent.parent
RECEIPTS = ROOT / "fairness" / "receipts"
NEW_FP = "sha256:" + "ab" * 8
OLD_FP = "sha256:" + "cd" * 8
FIRST_RUN = "sha256-22a7b980e3dba991.json"     # committed, with real failing rows
CONFIRM = "sha256-46e1485cd2c98caa-persuade-2.0.json"


def _receipt(name=FIRST_RUN):
    return json.loads((RECEIPTS / name).read_text("utf-8"))


def _stem(fp):
    return fp.replace(":", "-")


@pytest.fixture(name="one_manifest")
def _one_manifest_fixture(monkeypatch):
    """Only the Liang et al. manifest is required, it stands in for a corpus
    pre-registered to confirm NEW_FP, and the current ruleset is NEW_FP."""
    man = _receipt()["manifest_sha256"]
    req = {man: fairness_release.REQUIREMENTS[man]}
    monkeypatch.setattr(fairness_release, "REQUIREMENTS", req)
    monkeypatch.setattr(fairness_release, "RELEASE_MANIFESTS", tuple(req))
    monkeypatch.setattr(fairness_release, "CONFIRMATORY", {man: NEW_FP}, raising=False)
    monkeypatch.setattr(fairness_release, "ruleset_fingerprint", lambda: NEW_FP)
    return man


def _publish(tmp_path, version, fp, receipts=()):
    (tmp_path / "published-ruleset.json").write_text(json.dumps(
        {"package_version": version, "ruleset_version": fp, "receipts": list(receipts)}))


def _write(folder, name, rec):
    (folder / name).write_text(json.dumps(rec))


def _override(folder, reason="ship it"):
    _write(folder, f"{_stem(NEW_FP)}.override.json",
           {"ruleset_version": NEW_FP, "reason": reason, "decided_by": "maintainer"})


# --- the unchanged path needs a record from an earlier release -------------- #

def test_a_record_written_by_the_release_commit_does_not_skip_the_gates(tmp_path,
                                                                         one_manifest):
    receipts = tmp_path / "receipts"
    receipts.mkdir()
    _publish(tmp_path, articulate.__version__, NEW_FP, [f"{_stem(NEW_FP)}.json"])
    ok, lines = fairness_release.release_check(str(receipts))
    assert not ok, lines
    assert "a record cannot vouch for the release that writes it" in lines[0]


def test_control_a_record_from_an_earlier_release_still_skips_the_gates(tmp_path,
                                                                          one_manifest):
    receipts = tmp_path / "receipts"
    receipts.mkdir()
    _publish(tmp_path, "0.0.1", NEW_FP)
    ok, lines = fairness_release.release_check(str(receipts))
    assert ok and "gates not re-run" in lines[0], lines


@pytest.mark.parametrize("version", ["", None, "next", "99.0.0"])
def test_a_record_with_no_earlier_version_does_not_skip(tmp_path, one_manifest, version):
    receipts = tmp_path / "receipts"
    receipts.mkdir()
    _publish(tmp_path, version, NEW_FP)
    ok, lines = fairness_release.release_check(str(receipts))
    assert not ok, lines


def test_the_documented_release_commit_cannot_pass_the_committed_receipts(tmp_path, monkeypatch):
    # The probe from the review: copy the committed receipts, then write the
    # record as a release commit would, naming the ruleset being released and
    # the version being built. The check must give the same answer as with the
    # record untouched.
    fp = fairness.ruleset_fingerprint()
    receipts = tmp_path / "receipts"
    shutil.copytree(RECEIPTS, receipts)
    before = fairness_release.release_check(str(receipts))
    _publish(tmp_path, articulate.__version__, fp, [f"{_stem(fp)}.json"])
    after = fairness_release.release_check(str(receipts))
    assert after[0] is before[0], (before, after)
    assert "cannot vouch" in after[1][0]
    assert after[1][1:] == before[1]


# --- an override never ships a regression ---------------------------------- #

def test_an_override_does_not_excuse_a_newly_bound_profile_that_fails(tmp_path, monkeypatch,
                                                                     one_manifest):
    bound = fairness.bound_profiles() + ["newly-bound"]
    monkeypatch.setattr(fairness, "bound_profiles", lambda: list(bound))
    new = all_pass(_receipt())
    extra = json.loads(json.dumps(next(iter(new["results"].values()))))
    extra["profiles"] = ["newly-bound"]
    for c in extra["comparisons"].values():
        c["g1"]["pass"] = False
    new["results"]["config-new"] = extra
    new["bound_profiles"] = bound
    new["measured_profiles"] = sorted(set(new["measured_profiles"]) | {"newly-bound"})
    receipts = tmp_path / "receipts"
    receipts.mkdir()
    _write(receipts, f"{_stem(NEW_FP)}.json", as_ruleset(new, NEW_FP))
    _write(receipts, f"{_stem(OLD_FP)}.json", as_ruleset(all_pass(_receipt()), OLD_FP))
    _publish(tmp_path, "0.0.1", OLD_FP, [f"{_stem(OLD_FP)}.json"])
    _override(receipts)
    ok, lines = fairness_release.release_check(str(receipts))
    assert not ok, lines
    assert any("G1 newly-bound" in x for x in lines), lines


def test_an_override_does_not_compare_a_receipt_with_itself(tmp_path, one_manifest):
    # The published record lists the new ruleset's own receipt: the comparison
    # would find nothing regressed and label it as the published ruleset.
    receipts = tmp_path / "receipts"
    receipts.mkdir()
    _write(receipts, f"{_stem(NEW_FP)}.json", as_ruleset(_receipt(), NEW_FP))
    _publish(tmp_path, "0.0.1", OLD_FP, [f"{_stem(NEW_FP)}.json"])
    _override(receipts)
    ok, lines = fairness_release.release_check(str(receipts))
    assert not ok, lines
    assert any("not the published ruleset" in x for x in lines), lines


def test_an_override_is_refused_when_the_record_names_the_ruleset_being_released(
        tmp_path, one_manifest):
    receipts = tmp_path / "receipts"
    receipts.mkdir()
    _write(receipts, f"{_stem(NEW_FP)}.json", as_ruleset(_receipt(), NEW_FP))
    # An earlier version with the same fingerprint takes the unchanged path, so
    # name the version being built to reach the override.
    _publish(tmp_path, articulate.__version__, NEW_FP, [f"{_stem(NEW_FP)}.json"])
    _override(receipts)
    ok, lines = fairness_release.release_check(str(receipts))
    assert not ok, lines
    assert any("no earlier ruleset to compare with" in x for x in lines), lines


def test_an_override_base_whose_flags_disagree_with_its_numbers_is_refused(tmp_path,
                                                                           one_manifest):
    receipts = tmp_path / "receipts"
    receipts.mkdir()
    rec = _receipt()
    _write(receipts, f"{_stem(NEW_FP)}.json", as_ruleset(rec, NEW_FP))
    base = as_ruleset(rec, OLD_FP)
    for v in base["results"].values():
        for c in v["comparisons"].values():
            c["g1"]["pass"] = True                    # flags only, numbers unchanged
    _write(receipts, f"{_stem(OLD_FP)}.json", base)
    _publish(tmp_path, "0.0.1", OLD_FP, [f"{_stem(OLD_FP)}.json"])
    _override(receipts)
    ok, lines = fairness_release.release_check(str(receipts))
    assert not ok, lines
    assert any("cannot serve as a comparison" in x for x in lines), lines


# --- one receipt per ruleset and manifest ----------------------------------- #

@pytest.mark.parametrize("passing_name", ["-rerun.json", "-0.json", ".json"])
def test_a_second_receipt_from_the_same_manifest_is_not_ignored(tmp_path, one_manifest,
                                                                passing_name):
    receipts = tmp_path / "receipts"
    receipts.mkdir()
    failing_name = ".json" if passing_name != ".json" else "-z.json"
    _write(receipts, _stem(NEW_FP) + passing_name, as_ruleset(all_pass(_receipt()), NEW_FP))
    _write(receipts, _stem(NEW_FP) + failing_name, as_ruleset(_receipt(), NEW_FP))
    ok, lines = fairness_release.release_check(str(receipts))
    assert not ok, lines
    assert any("two receipts for" in x for x in lines), lines


def test_control_one_passing_receipt_passes(tmp_path, one_manifest):
    receipts = tmp_path / "receipts"
    receipts.mkdir()
    _write(receipts, f"{_stem(NEW_FP)}.json", as_ruleset(all_pass(_receipt()), NEW_FP))
    ok, lines = fairness_release.release_check(str(receipts))
    assert ok, lines


# --- a stored flag never claims more than its numbers ----------------------- #

def _flip(rec, edit):
    rec = json.loads(json.dumps(rec))
    for v in rec["results"].values():
        for c in v["comparisons"].values():
            edit(c)
    return as_ruleset(rec, NEW_FP)


def _g1_flag(c):
    c["g1"]["pass"] = True


def _g2_flag(c):
    for row in c["g2"].values():
        row["pass"] = True


def _g1_number(c):
    c["g1"]["diff"] = 0.0


@pytest.mark.parametrize("edit,message", [
    (_g1_flag, "G1 is stored as passing and its own numbers fail"),
    (_g2_flag, "is stored as passing with a failing state"),
    (_g1_number, "differs from its own counts"),
])
def test_a_hand_set_flag_is_refused(tmp_path, one_manifest, edit, message):
    receipts = tmp_path / "receipts"
    receipts.mkdir()
    _write(receipts, f"{_stem(NEW_FP)}.json", _flip(_receipt(), edit))
    ok, lines = fairness_release.release_check(str(receipts))
    assert not ok and any(message in x for x in lines), lines


def test_every_committed_receipt_has_flags_that_agree_with_its_numbers():
    from articulate.fairness_verify import flag_problems
    for path in sorted(RECEIPTS.glob("*.json")):
        assert flag_problems(json.loads(path.read_text("utf-8"))) == [], path.name


def test_the_committed_receipts_give_the_stored_verdict():
    # Outcome-neutral: the check on the committed folder agrees with the gates
    # the current ruleset's receipts record, whatever they are.
    fp = fairness.ruleset_fingerprint()
    ok, _lines = fairness_release.release_check(str(RECEIPTS))
    stored = [json.loads(p.read_text("utf-8"))["gates"]["release_ok"]
              for p in RECEIPTS.glob(f"{_stem(fp)}*.json")]
    assert stored and ok is all(stored)
