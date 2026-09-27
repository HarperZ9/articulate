"""Receipt pins and the confirmatory binding of the release check (amendment of
27 September 2026 in fairness/PREREG.md).

- fairness/receipts/SHA256SUMS pins every committed receipt by its bytes, and a
  pinned receipt that differs from its pin fails the check.
- A confirmatory corpus confirms only the ruleset it was pre-registered for. A
  changed ruleset whose receipts all pass still fails without a confirmatory
  receipt of its own.

Synthetic edits of committed receipts; nothing here measures any group.
"""
import hashlib

from receipt_fakes import all_pass, as_ruleset
from test_release_integrity import CONFIRM, NEW_FP, RECEIPTS, _receipt, _stem, _write
from test_release_integrity import _one_manifest_fixture  # noqa: F401  (fixture one_manifest)

from articulate import fairness_release



# --- pins -------------------------------------------------------------------- #

def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_the_committed_receipts_are_pinned_by_their_bytes():
    pins = (RECEIPTS / "SHA256SUMS").read_text("utf-8").split("\n")
    listed = dict(reversed(line.split("  ", 1)) for line in pins if line)
    names = sorted(p.name for p in RECEIPTS.glob("*.json"))
    assert sorted(listed) == names
    for name in names:
        assert listed[name] == _sha(RECEIPTS / name), name
    assert _sha(RECEIPTS / CONFIRM) == \
        "22992435165b85aa04f2096627060d0a5e0ccdb5b8cc9a72af2befd229f1e7a7"


def test_a_receipt_that_differs_from_its_pin_is_refused(tmp_path, one_manifest):
    receipts = tmp_path / "receipts"
    receipts.mkdir()
    name = f"{_stem(NEW_FP)}.json"
    _write(receipts, name, as_ruleset(all_pass(_receipt()), NEW_FP))
    good = _sha(receipts / name)
    (receipts / "SHA256SUMS").write_text(f"{good}  {name}\n")
    assert fairness_release.release_check(str(receipts))[0]          # control
    _write(receipts, name, as_ruleset(all_pass(_receipt()), NEW_FP) | {"note": "edited"})
    ok, lines = fairness_release.release_check(str(receipts))
    assert not ok and any("does not match its pin" in x for x in lines), lines
    (receipts / "SHA256SUMS").write_text("")
    ok, lines = fairness_release.release_check(str(receipts))
    assert not ok and any("is not pinned" in x for x in lines), lines


# --- a confirmatory corpus confirms one ruleset ----------------------------- #

def test_a_changed_ruleset_needs_a_confirmatory_receipt_of_its_own(tmp_path, monkeypatch):
    # Passing receipts from both release manifests, but PERSUADE 2.0 was
    # pre-registered for another ruleset and its outcome is known: exploratory.
    monkeypatch.setattr(fairness_release, "ruleset_fingerprint", lambda: NEW_FP)
    receipts = tmp_path / "receipts"
    receipts.mkdir()
    liang = _receipt("sha256-46e1485cd2c98caa.json")
    persuade = _receipt(CONFIRM)
    _write(receipts, f"{_stem(NEW_FP)}.json", as_ruleset(all_pass(liang), NEW_FP))
    _write(receipts, f"{_stem(NEW_FP)}-persuade-2.0.json",
           as_ruleset(all_pass(persuade), NEW_FP))
    ok, lines = fairness_release.release_check(str(receipts), str(tmp_path / "none.json"))
    assert not ok and any("no confirmatory receipt" in x for x in lines), lines
    monkeypatch.setattr(fairness_release, "CONFIRMATORY",
                        {persuade["manifest_sha256"]: NEW_FP})           # control
    ok, lines = fairness_release.release_check(str(receipts), str(tmp_path / "none.json"))
    assert ok, lines
