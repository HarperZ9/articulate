"""docs/fairness-confirmatory.md must agree with the receipts it cites.

Every row of every table on the page is parsed and compared with the committed
receipt: the PERSUADE 2.0 confirmatory receipt, and the report-only ELLIPSE
receipt. Both hold counts only. The gate-level claims in the page's result
section are checked against the receipt's own rows as well.
"""
import json
import pathlib
import re

from articulate import fairness, fairness_release
from articulate.fairness_regress import gate_rows

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGE = (ROOT / "docs" / "fairness-confirmatory.md").read_text(encoding="utf-8")
FLAT = " ".join(PAGE.split())          # running text, with line breaks as spaces
CONFIRM_NAME = "persuade-ell-vs-non-ell"
BANDS = {"Overall 1.0 to 2.5": "ellipse_low", "Overall 3.0 to 3.5": "ellipse_mid",
         "Overall 4.0 to 5.0": "ellipse_high"}


def _receipt(label):
    m = re.search(label + r" = `([^`]+)`", PAGE)
    assert m, f"the page must name the {label} receipt"
    return json.loads((ROOT / m.group(1)).read_text(encoding="utf-8"))


CONFIRM, ELLIPSE = _receipt("confirmatory"), _receipt("report")


def _config(rec, profile):
    for v in rec["results"].values():
        if profile in v["profiles"]:
            return v
    raise AssertionError(f"profile {profile} not in the receipt")


def _rows(first_header):
    """Rows of every table on the page that opens with this header."""
    rows = []
    for part in PAGE.split(first_header)[1:]:
        table = part.split("\n\n", 1)[0]
        rows += [[c.strip() for c in re.split(r"(?<!\\)\|", ln.strip().strip("|"))]
                 for ln in table.splitlines()[2:] if ln.startswith("|")]
    return rows


def _num(cell):
    return None if cell == "none" else float(cell)


def _count(cell):
    return list(map(int, re.fullmatch(r"(\d+) of (\d+)", cell).groups()))


def test_the_page_names_the_manifests_the_receipts_ran_on():
    assert CONFIRM["manifest_sha256"] in PAGE
    assert CONFIRM["ruleset_version"] == ELLIPSE["ruleset_version"]
    assert f"`{CONFIRM['ruleset_version']}`" in PAGE


def test_confirmatory_block_rates_match_the_receipt():
    rows = _rows("| Profile | Learner essays | Other essays |")
    assert len(rows) >= 4
    for profile, prot, ref in rows:
        g7 = _config(CONFIRM, profile)["g7"]
        assert g7["persuade_ell"]["blocked"] == _count(prot), profile
        assert g7["persuade_non_ell"]["blocked"] == _count(ref), profile


def test_confirmatory_gaps_match_the_receipt():
    rows = _rows("| Profile | Raw gap | 95% interval | Within score bands |")
    assert len(rows) >= 4
    for profile, gap, ci, banded, matched in rows:
        g1 = _config(CONFIRM, profile)["comparisons"][CONFIRM_NAME]["g1"]
        assert g1["diff"] == _num(gap) and g1["ci"] == json.loads(ci), profile
        assert g1.get("banded_diff") == _num(banded), profile
        assert g1.get("matched_diff") == _num(matched), profile


def test_confirmatory_notes_match_the_receipt():
    rows = _rows("| Profile | Note | Learner essays | Other essays |")
    assert rows
    for profile, note, prot, ref, ratio, state, shown in rows:
        rule = note.strip("`").replace("\\|", "|")
        g8 = _config(CONFIRM, profile)["comparisons"][CONFIRM_NAME]["g8"][rule]
        assert g8["docs"] == [int(prot), int(ref)], rule
        assert g8["ratio"] == ("inf" if ratio == "inf" else _num(ratio)), rule
        assert g8["state"] == state and g8["house"] is (shown == "no"), rule


def test_the_page_states_the_confirmatory_result():
    rows = gate_rows(CONFIRM)
    passing = sum(1 for ok in rows.values() if ok)
    assert f"{passing} of the {len(rows)} gate rows" in PAGE
    verdict = "passes" if CONFIRM["gates"]["release_ok"] else "fails"
    assert f"the release gate {verdict} on the confirmatory corpus" in PAGE


def test_proficiency_band_rates_match_the_report():
    header = "| Profile | " + " | ".join(BANDS) + " |"
    rows = _rows(header)
    assert len(rows) >= 2
    for profile, *cells in rows:
        g7 = _config(ELLIPSE, profile)["g7"]
        for band, cell in zip(BANDS, cells):
            assert g7[BANDS[band]]["blocked"] == _count(cell), (profile, band)


def test_the_receipt_is_the_one_the_prereg_names_and_its_summary_is_its_own():
    prereg = (ROOT / "fairness" / "PREREG.md").read_text(encoding="utf-8")
    assert f"`{CONFIRM['ruleset_version']}`" in prereg
    assert CONFIRM["manifest_sha256"] in fairness_release.RELEASE_MANIFESTS
    assert fairness._gate_summary(CONFIRM["results"], CONFIRM["bound_profiles"]) \
        == CONFIRM["gates"]


def _bound(rec):
    return [v for v in rec["results"].values() if set(v["profiles"]) & set(rec["bound_profiles"])]


def _g2_failures():
    """{(rule, "learner" or "other"): (state row, failing bound profiles)}."""
    out = {}
    for v in _bound(CONFIRM):
        profiles = [p for p in v["profiles"] if p in CONFIRM["bound_profiles"]]
        for rule, r in v["comparisons"][CONFIRM_NAME]["g2"].items():
            for d, side in (("toward_protected", "learner"), ("toward_reference", "other")):
                if r[d]["state"] in ("skewed", "inconclusive"):
                    row = out.setdefault((rule, side), (r[d], []))
                    assert row[0] == r[d], rule         # one measurement, one row
                    row[1].extend(profiles)
    return out


def test_the_g2_table_lists_every_failing_rule_and_matches_the_receipt():
    rows = _rows("| Rule | Learner essays | Other essays | Ratio toward |")
    fails = _g2_failures()
    seen = set()
    for rule, prot, ref, side, ratio, ci, state, count in rows:
        key = (rule.strip("`").replace("\\|", "|"), side)
        s, profiles = fails[key]
        learner, other = s["docs"] if side == "learner" else s["docs"][::-1]
        assert [int(prot), int(ref)] == [learner, other], key
        assert str(s["ratio"]) == ratio and state == s["state"], key
        assert ci == "[" + ", ".join(str(x) for x in s["ci"]) + "]", key
        assert int(count) == len(profiles), key
        seen.add(key)
    assert seen == set(fails)
    toward_learner = [k for k in fails if k[1] == "learner"]
    assert ("none toward the learner essays" in FLAT) is (not toward_learner)


def test_the_power_table_matches_the_receipt():
    rows = _rows("| Profile | Smallest gap it can see (points) |")
    assert len(rows) >= 4
    for profile, size in rows:
        g1 = _config(CONFIRM, profile)["comparisons"][CONFIRM_NAME]["g1"]
        assert g1["min_detectable"] == float(size), profile


def test_the_result_section_counts_match_the_receipt_rows():
    rows = gate_rows(CONFIRM)
    bound = CONFIRM["bound_profiles"]

    def failing(gate):
        return sum(1 for k, ok in rows.items() if k.startswith(gate + " ") and not ok)
    assert f"**G1 fails under {failing('G1')} strict profiles.**" in FLAT
    assert f"**G2 fails under {failing('G2')} bound profiles.**" in FLAT
    assert f"**G4 fails under {failing('G4')} of the {len(bound)} bound profiles.**" in FLAT
    assert failing("G5") == 0 and "**G5 passes.**" in FLAT
    zero = [p for v in _bound(CONFIRM) for p in v["profiles"] if p in bound
            and all(x["blocked"][0] == 0 for x in v["g7"].values())]
    assert f"neither do {len(zero) - 1} other bound profiles" in FLAT
    assert ("**G7 opens a review.**" in FLAT) is bool(CONFIRM["gates"]["G7_review"])
