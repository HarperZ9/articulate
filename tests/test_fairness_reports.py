"""Harness reports settled for ruleset 0.9.0, on synthetic counts and text.

The reviews of 27 September 2026 found that the within-band and within-cell
interval re-centred the crude width (fairness review 9a), that the paired-rewrite
p-value was stored rounded, so 3.4e-7 read as 0 (7), and that a report-only
manifest's receipt did not say so and carried a release verdict (16). A writer
who contributed several texts, and a length difference between groups, had no
report. None of these changes a gate: G1 still gates on the within-group point
estimates. The texts and counts are made up and measure nothing about fairness
to any group of writers.
"""
import hashlib
import json
import math

import pytest

from articulate import fairness, fairness_corpora, fairness_gates
from articulate import fairness_stats as S


def _manifest(tmp_path, sets, extra=None):
    docs = []
    for name, texts in sets.items():
        for i, t in enumerate(texts):
            p = tmp_path / name / f"{i:02d}.txt"
            p.parent.mkdir(exist_ok=True)
            p.write_bytes(t.encode("utf-8"))
            row = {"set": name, "path": f"{name}/{i:02d}.txt", "key": str(i),
                   "sha256": "sha256:" + hashlib.sha256(t.encode()).hexdigest()}
            docs.append(row)
    names = list(sets)
    man = {"schema": fairness_corpora.SCHEMA,
           "corpora": {"synthetic": {"licence": "test fixture", "upstream": "this test",
                                     "retrieved": "2026-09-27"}},
           "sets": {n: {"corpus": "synthetic", "groups": {"first_language": n}} for n in names},
           "documents": docs,
           "comparisons": [{"name": "a-vs-b", "dimension": "first_language",
                            "protected": names[0], "reference": names[1],
                            "design": "matched"}]}
    man.update(extra or {})
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(man), encoding="utf-8")
    return path, man


PLAIN = [f"The bus came on day {i}. We walked home and cooked dinner before seven.\n"
         for i in range(8)]


# --- G1: the within-group interval ------------------------------------------ #

def _wald(k1, n1, k2, n2):
    p1, p2 = k1 / n1, k2 / n2
    return math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)


def test_the_sato_interval_is_wald_with_one_stratum():
    d, (lo, hi) = S.stratified_diff([(30, 100, 20, 100)])
    se = _wald(30, 100, 20, 100)
    assert math.isclose(d, 0.1)
    assert math.isclose(lo, 0.1 - S.Z * se) and math.isclose(hi, 0.1 + S.Z * se)


def test_the_sato_interval_narrows_with_identical_strata():
    one = S.stratified_diff([(30, 100, 20, 100)])
    four = S.stratified_diff([(30, 100, 20, 100)] * 4)
    assert math.isclose(four[0], one[0])
    assert math.isclose(four[1][1] - four[0], (one[1][1] - one[0]) / 2)


def test_the_within_band_interval_is_not_the_crude_width_recentred():
    strata = [(9, 10, 45, 50), (5, 50, 1, 10)]
    d, (lo, hi) = S.stratified_diff(strata)
    pooled, (plo, phi) = S.newcombe(14, 60, 46, 60)
    assert not math.isclose(hi - d, phi - pooled)
    # Sato's variance for the Mantel-Haenszel risk difference, written out.
    w = p = q = 0.0
    for k1, n1, k2, n2 in strata:
        n = n1 + n2
        w += n1 * n2 / n
        p += (n1 * n1 * k2 - n2 * n2 * k1 + n1 * n2 * (n2 - n1) / 2) / (n * n)
        q += (k1 * (n2 - k2) + k2 * (n1 - k1)) / (2 * n)
    assert math.isclose(hi - d, S.Z * math.sqrt((d * p + q) / (w * w)))


# --- G1 reports: writers and length ----------------------------------------- #

def _docs(blocked, words, writers=None):
    return [{"blocked": b, "words": w, "density": None,
             **({"writer": writers[i]} if writers else {})}
            for i, (b, w) in enumerate(zip(blocked, words))]


def test_a_writer_cluster_interval_is_reported_when_documents_name_writers():
    # Each writer's texts share an outcome, so the writer, not the text, is the
    # unit of resampling, and the interval is wider than the text-level one.
    prot = _docs([True] * 10 + [False] * 30, [300] * 40, [f"p{i // 5}" for i in range(40)])
    ref = _docs([True] * 5 + [False] * 35, [300] * 40, [f"r{i // 5}" for i in range(40)])
    g1 = fairness_gates.g1(prot, ref)
    wc = g1["writer_cluster"]
    assert wc["writers"] == [8, 8] and wc["gates"] is False and wc["b"] == 2000
    assert wc["ci"][0] <= g1["diff"] <= wc["ci"][1]
    assert wc["ci"][1] - wc["ci"][0] > g1["ci"][1] - g1["ci"][0]
    assert fairness_gates.g1(prot, ref) == g1       # seeded, so it re-derives


def test_no_writer_report_when_documents_name_no_writers():
    prot = _docs([True] * 10 + [False] * 30, [300] * 40)
    ref = _docs([True] * 5 + [False] * 35, [300] * 40)
    assert "writer_cluster" not in fairness_gates.g1(prot, ref)


def test_the_gap_is_reported_within_word_count_quintiles():
    words = list(range(100, 500, 10))
    prot = _docs([w >= 400 for w in words], words)
    ref = _docs([w >= 300 for w in words], words)
    g1 = fairness_gates.g1(prot, ref)
    lq = g1["length_quintiles"]
    assert lq["gates"] is False
    assert len(lq["bins"]) == 5
    assert sum(b["protected"][1] for b in lq["bins"]) == 40
    assert sum(b["reference"][1] for b in lq["bins"]) == 40
    assert lq["bins"][0]["diff"] == 0.0 and lq["bins"][-1]["diff"] == 0.0
    assert lq["bins"][2]["diff"] < 0
    assert lq["diff"] is not None and len(lq["ci"]) == 2
    # A report never moves the gate.
    assert g1["pass"] == fairness_gates.g1(
        [dict(d, words=None) for d in prot], [dict(d, words=None) for d in ref])["pass"]


def test_the_writer_column_is_read_from_a_table(tmp_path):
    rows = "id,text,l1,student\n1,One text here.,a,s1\n2,Two text here.,b,s2\n"
    data = rows.encode("utf-8")
    (tmp_path / "t.csv").write_bytes(data)
    man = {"schema": fairness_corpora.SCHEMA,
           "corpora": {"c": {"licence": "x", "upstream": "y", "retrieved": "z"}},
           "sets": {"a": {"corpus": "c"}, "b": {"corpus": "c"}},
           "tables": [{"corpus": "c", "path": "t.csv", "format": "csv",
                       "sha256": "sha256:" + hashlib.sha256(data).hexdigest(),
                       "id": "id", "text": "text", "writer": "student",
                       "sets": {"a": {"l1": "a"}, "b": {"l1": "b"}}}]}
    fairness_corpora._validate(man)
    got = {d["key"]: d["writer"] for d, _t in fairness_corpora.load_documents(man, str(tmp_path))}
    assert got == {"1": "s1", "2": "s2"}


def test_the_writer_never_reaches_the_receipt(tmp_path):
    path, man = _manifest(tmp_path, {"a": PLAIN[:4], "b": PLAIN[4:]})
    for i, d in enumerate(man["documents"]):
        d["writer"] = f"student-{i // 2}"
    path.write_text(json.dumps(man), encoding="utf-8")
    rec = fairness.run(str(path), names=["flavored"])
    assert "student-" not in json.dumps(rec, default=list)
    (cfg,) = rec["results"].values()
    assert cfg["comparisons"]["a-vs-b"]["g1"]["writer_cluster"]["writers"] == [2, 2]


# --- receipt markers ----------------------------------------------------------- #

def test_a_report_only_manifest_marks_its_receipt(tmp_path):
    note = "Report only, never a release gate."
    path, _ = _manifest(tmp_path, {"a": PLAIN[:4], "b": PLAIN[4:]}, {"report_only": note})
    rec = fairness.run(str(path), names=["flavored"])
    assert rec["report_only"] == note
    assert "release_ok" not in rec["gates"]


def test_a_release_manifest_receipt_keeps_release_ok(tmp_path):
    path, _ = _manifest(tmp_path, {"a": PLAIN[:4], "b": PLAIN[4:]})
    rec = fairness.run(str(path), names=["flavored"])
    assert "report_only" not in rec and "release_ok" in rec["gates"]


def test_the_paired_rewrite_p_value_is_stored_unrounded():
    a = [{"key": str(i), "blocked": False} for i in range(35)]
    b = [{"key": str(i), "blocked": True} for i in range(35)]
    p = fairness_gates.g3(a, b)["mcnemar_p"]
    assert p > 0 and math.isclose(p, 2 * 0.5 ** 35)


@pytest.mark.parametrize("jobs", [2])
def test_the_reports_are_the_same_in_several_processes(tmp_path, jobs):
    path, _ = _manifest(tmp_path, {"a": PLAIN[:4], "b": PLAIN[4:]})
    one = fairness.run(str(path), names=["essay", "flavored"])
    many = fairness.run(str(path), names=["essay", "flavored"], jobs=jobs)
    assert json.dumps(one, sort_keys=True, default=list) == \
        json.dumps(many, sort_keys=True, default=list)
