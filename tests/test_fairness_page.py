"""docs/fairness-audit.md must agree with the receipts it cites.

Every row of every table on the page is parsed and compared with the committed
receipt it names. A number typed by hand that drifts from its receipt fails
here. The receipts themselves are content-free and hold counts only.
"""
import json
import pathlib
import re

from articulate import fairness

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGE = (ROOT / "docs" / "fairness-audit.md").read_text(encoding="utf-8")
SETS = {"Learner scripts": "toefl", "College windows": "college", "Abstract windows": "abstracts"}
COMPARE = {"learner vs college": "toefl-vs-college", "learner vs abstracts": "toefl-vs-abstracts"}
PAIR = "toefl-original-vs-gpt4-rewrite"


def _receipts():
    m = re.search(r"before = `([^`]+)`,\s*after = `([^`]+)`", PAGE)
    assert m, "the page must name its receipts"
    return {k: json.loads((ROOT / p).read_text(encoding="utf-8"))
            for k, p in zip(("before", "after"), m.groups())}


RECS = _receipts()


def _config(receipt, profile):
    for v in RECS[receipt]["results"].values():
        if profile in v["profiles"]:
            return v
    raise AssertionError(f"profile {profile} not in receipt")


def _rows(first_header):
    table = PAGE.split(first_header, 1)[1].split("\n\n", 1)[0]
    return [[c.strip() for c in re.split(r"(?<!\\)\|", ln.strip().strip("|"))]
            for ln in table.splitlines()[2:] if ln.startswith("|")]


def _num(cell):
    return float(cell)


def test_block_rates_match_the_receipts():
    rows = _rows("| Receipt | Profile | Learner scripts |")
    assert len(rows) >= 6
    for receipt, profile, *cells in rows:
        g7 = _config(receipt, profile)["g7"]
        for name, cell in zip(SETS, cells):
            k, n = map(int, re.fullmatch(r"(\d+) of (\d+)", cell).groups())
            assert g7[SETS[name]]["blocked"] == [k, n], (receipt, profile, name)


def test_gaps_match_the_receipts():
    rows = _rows("| Receipt | Profile | Comparison | Gap |")
    assert len(rows) >= 10
    for receipt, profile, comparison, gap, ci in rows:
        g1 = _config(receipt, profile)["comparisons"][COMPARE[comparison]]["g1"]
        assert g1["diff"] == _num(gap), (receipt, profile, comparison)
        assert g1["ci"] == json.loads(ci), (receipt, profile, comparison)


def test_smallest_detectable_gaps_match_the_receipts():
    rows = _rows("| Receipt | Profile | Comparison | Smallest detectable gap |")
    assert len(rows) >= 4
    for receipt, profile, comparison, value in rows:
        g1 = _config(receipt, profile)["comparisons"][COMPARE[comparison]]["g1"]
        assert g1["min_detectable"] == _num(value), (receipt, profile, comparison)


def test_cadence_rows_match_the_receipts():
    rows = _rows("| Receipt | Profile | Comparison | Learner flagged |")
    assert len(rows) >= 4
    for receipt, profile, comparison, prot, ref, gap, ci in rows:
        g5 = _config(receipt, profile)["comparisons"][COMPARE[comparison]]["g5"]
        as_pair = [list(map(int, re.fullmatch(r"(\d+) of (\d+)", c).groups()))
                   for c in (prot, ref)]
        assert g5["uniform"] == as_pair, (receipt, profile, comparison)
        assert g5["diff"] == _num(gap) and g5["ci"] == json.loads(ci)


def test_note_rows_match_the_receipts():
    rows = _rows("| Receipt | Profile | Comparison | Note |")
    assert len(rows) >= 5
    for receipt, profile, comparison, note, prot, ref, ratio, shown in rows:
        rule = note.strip("`").replace("\\|", "|")
        g8 = _config(receipt, profile)["comparisons"][COMPARE[comparison]]["g8"][rule]
        assert g8["docs"] == [int(prot), int(ref)], rule
        assert g8["ratio"] == _num(ratio), rule
        assert g8["house"] is (shown == "no"), rule


def test_paired_rows_match_the_receipts():
    rows = _rows("| Receipt | Profile | Originals only |")
    assert len(rows) >= 4
    for receipt, profile, orig, rewr, p in rows:
        pair = _config(receipt, profile)["pairs"][PAIR]
        assert [pair["original_only"], pair["rewrite_only"]] == [int(orig), int(rewr)]
        assert pair["mcnemar_p"] == _num(p)


def test_the_g1_row_names_every_failing_bound_profile():
    bound = set(fairness.bound_profiles())
    failing = {p for v in RECS["after"]["results"].values() for p in v["profiles"]
               if p in bound and not all(c["g1"]["pass"] for c in v["comparisons"].values())}
    row = PAGE.split("| G1 gap within 5 points", 1)[1].split("\n", 1)[0]
    assert failing == set(re.findall(r"`([a-z/-]+)`", row)), failing
    assert f"{len(failing)} of the {len(bound)} bound profiles" in row


def test_the_page_states_the_release_gate_result():
    after = RECS["after"]
    assert after["gates"]["release_ok"] is False
    assert after["gates"]["G7_review"] == ["abstracts"]
    assert "does not pass on this corpus" in PAGE
