"""A table set may select rows by a list of values, so one set can hold a band of
scores (the ELLIPSE proficiency report). Synthetic tables only.
"""
import csv
import hashlib

import pytest

from articulate import fairness_corpora

FIELDS = ["id", "text", "Overall"]


def _manifest(tmp_path, where):
    path = tmp_path / "t.csv"
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, FIELDS)
        w.writeheader()
        for i, s in enumerate(("1.5", "2.5", "3", "3.5", "4.5", "")):
            w.writerow({"id": f"T{i}", "text": f"Text {i} is short.", "Overall": s})
    digest = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    return {"schema": fairness_corpora.SCHEMA,
            "corpora": {"t": {"licence": "test fixture", "upstream": "this test",
                              "retrieved": "2026-09-26"}},
            "sets": {"low": {"corpus": "t", "groups": {"proficiency": "low"}},
                     "high": {"corpus": "t", "groups": {"proficiency": "high"}}},
            "tables": [{"corpus": "t", "path": "t.csv", "sha256": digest, "format": "csv",
                        "id": "id", "text": "text", "sets": where}],
            "comparisons": [{"name": "low-vs-high", "dimension": "proficiency",
                             "protected": "low", "reference": "high", "design": "proxy"}]}


def test_a_set_selects_every_row_whose_value_is_in_its_list(tmp_path):
    man = _manifest(tmp_path, {"low": {"Overall": ["1", "1.5", "2", "2.5"]},
                               "high": {"Overall": ["4", "4.5", "5"]}})
    fairness_corpora._validate(man)
    got = {d["key"]: d["set"] for d, _t in fairness_corpora.load_documents(man, str(tmp_path))}
    assert got == {"T0": "low", "T1": "low", "T4": "high"}


def test_a_single_value_still_selects_by_equality(tmp_path):
    man = _manifest(tmp_path, {"low": {"Overall": "3"}, "high": {"Overall": "3.5"}})
    got = {d["key"]: d["set"] for d, _t in fairness_corpora.load_documents(man, str(tmp_path))}
    assert got == {"T2": "low", "T3": "high"}


def test_an_empty_value_list_is_refused(tmp_path):
    man = _manifest(tmp_path, {"low": {"Overall": []}, "high": {"Overall": "4.5"}})
    with pytest.raises(fairness_corpora.CorpusError, match="empty"):
        fairness_corpora._validate(man)
