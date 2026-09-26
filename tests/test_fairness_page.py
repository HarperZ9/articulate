"""docs/fairness-audit.md must agree with the receipts it cites.

Every block-rate and gap row on the page is parsed and compared with the
committed receipt. A number typed by hand that drifts from its receipt fails
here. The receipts themselves are content-free and hold counts only.
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGE = (ROOT / "docs" / "fairness-audit.md").read_text(encoding="utf-8")
SETS = {"Learner scripts": "toefl", "College windows": "college", "Abstract windows": "abstracts"}
COMPARE = {"learner vs college": "toefl-vs-college", "learner vs abstracts": "toefl-vs-abstracts"}


def _receipts():
    m = re.search(r"before = `([^`]+)`,\s*after = `([^`]+)`", PAGE)
    assert m, "the page must name its receipts"
    return {k: json.loads((ROOT / p).read_text(encoding="utf-8"))
            for k, p in zip(("before", "after"), m.groups())}


def _config(rec, profile):
    for v in rec["results"].values():
        if profile in v["profiles"]:
            return v
    raise AssertionError(f"profile {profile} not in receipt")


def _rows(first_header):
    table = PAGE.split(first_header, 1)[1].split("\n\n", 1)[0]
    return [[c.strip() for c in ln.strip("|").split("|")]
            for ln in table.splitlines()[2:] if ln.startswith("|")]


def test_block_rates_match_the_receipts():
    recs = _receipts()
    rows = _rows("| Receipt | Profile | Learner scripts |")
    assert len(rows) >= 6
    for receipt, profile, *cells in rows:
        g7 = _config(recs[receipt], profile)["g7"]
        for name, cell in zip(SETS, cells):
            k, n = map(int, re.fullmatch(r"(\d+) of (\d+)", cell).groups())
            assert g7[SETS[name]]["blocked"] == [k, n], (receipt, profile, name)


def test_gaps_match_the_receipts():
    recs = _receipts()
    rows = _rows("| Receipt | Profile | Comparison | Gap |")
    assert len(rows) >= 8
    for receipt, profile, comparison, gap, ci in rows:
        g1 = _config(recs[receipt], profile)["comparisons"][COMPARE[comparison]]["g1"]
        assert g1["diff"] == float(gap), (receipt, profile, comparison)
        assert g1["ci"] == json.loads(ci), (receipt, profile, comparison)


def test_the_page_states_the_release_gate_result():
    after = _receipts()["after"]
    assert after["gates"]["release_ok"] is False
    assert "does not pass on this corpus" in PAGE
