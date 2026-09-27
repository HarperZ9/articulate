"""The confirmatory arm (PR 9, decision 7): a table loader, prompt-matched G1
strata and a release requirement per manifest.

Synthetic tables and synthetic measurements only. Nothing here reads the
licensed corpus or measures any real group of writers.
"""
import csv
import hashlib
import json
import pathlib
import re

import pytest

from articulate import fairness, fairness_corpora, fairness_gates, fairness_release

ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "fairness" / "manifests" / "persuade-2.0.json"
FIELDS = ["essay_id_comp", "full_text", "prompt_name", "holistic_essay_score", "ell_status",
          "discourse_type"]


def _rows():
    rows = []
    for i in range(4):
        text = f"Essay {i} says the bus was late. It says so twice.\r\nThe end."
        for part in ("Lead", "Claim"):                     # one row per discourse element
            rows.append({"essay_id_comp": f"E{i}", "full_text": text,
                         "prompt_name": "Bus" if i % 2 else "Car",
                         "holistic_essay_score": str(2 + i % 3),
                         "ell_status": ("Yes", "No", "", "No")[i], "discourse_type": part})
    return rows


def _write_table(tmp_path, rows=None):
    path = tmp_path / "table.csv"
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, FIELDS)
        w.writeheader()
        w.writerows(rows or _rows())
    digest = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    man = {"schema": fairness_corpora.SCHEMA,
           "corpora": {"t": {"licence": "test fixture", "upstream": "this test",
                             "retrieved": "2026-09-26"}},
           "sets": {"ell": {"corpus": "t", "groups": {"first_language": "learner"}},
                    "non_ell": {"corpus": "t", "groups": {"first_language": "not learner"}}},
           "tables": [{"corpus": "t", "path": "table.csv", "sha256": digest, "format": "csv",
                       "id": "essay_id_comp", "text": "full_text", "prompt": "prompt_name",
                       "score": "holistic_essay_score",
                       "sets": {"ell": {"ell_status": "Yes"},
                                "non_ell": {"ell_status": "No"}}}],
           "comparisons": [{"name": "ell-vs-non-ell", "dimension": "first_language",
                            "protected": "ell", "reference": "non_ell", "design": "matched"}]}
    return man


# --- the table loader -------------------------------------------------------- #

def test_a_table_yields_one_document_per_essay_with_prompt_and_score(tmp_path):
    man = _write_table(tmp_path)
    fairness_corpora._validate(man)
    docs = list(fairness_corpora.load_documents(man, str(tmp_path)))
    by = {d["key"]: (d, t) for d, t in docs}
    assert sorted(by) == ["E0", "E1", "E3"]              # the blank status is left out
    assert by["E0"][0]["set"] == "ell" and by["E1"][0]["set"] == "non_ell"
    assert by["E1"][0]["prompt"] == "Bus" and by["E1"][0]["score"] == 3
    assert "\r" not in by["E0"][1]


def test_a_table_whose_bytes_moved_is_refused(tmp_path):
    man = _write_table(tmp_path)
    man["tables"][0]["sha256"] = "sha256:" + "0" * 64
    with pytest.raises(fairness_corpora.CorpusError, match="does not match"):
        list(fairness_corpora.load_documents(man, str(tmp_path)))


def test_one_essay_with_two_texts_is_refused(tmp_path):
    rows = _rows()
    rows[1]["full_text"] = "A different text."
    man = _write_table(tmp_path, rows)
    with pytest.raises(fairness_corpora.CorpusError, match="more than one text"):
        list(fairness_corpora.load_documents(man, str(tmp_path)))


def test_a_table_naming_an_unknown_set_or_column_is_refused(tmp_path):
    man = _write_table(tmp_path)
    man["tables"][0]["sets"]["other"] = {"ell_status": "Yes"}
    with pytest.raises(fairness_corpora.CorpusError, match="unknown set"):
        fairness_corpora._validate(man)
    man = _write_table(tmp_path)
    man["tables"][0]["prompt"] = "no_such_column"
    with pytest.raises(fairness_corpora.CorpusError, match="no column"):
        list(fairness_corpora.load_documents(man, str(tmp_path)))


def test_the_harness_reads_a_table_from_a_root_outside_the_manifest(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    man = _write_table(corpus)
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(man), encoding="utf-8")
    rec = fairness.run(str(path), names=["flavored"], root=str(corpus))
    (cfg,) = rec["results"].values()
    g1 = cfg["comparisons"]["ell-vs-non-ell"]["g1"]
    assert g1["protected"][1] == 1 and g1["reference"][1] == 2
    assert "bus was late" not in json.dumps(rec, default=list)


# --- G1 within prompt-and-score strata -------------------------------------- #

def _docs(prompt, blocked, n):
    return [{"blocked": i < blocked, "density": None, "score": None, "prompt": prompt}
            for i in range(n)]


def test_g1_fails_a_gap_that_only_shows_within_prompts():
    # Raw rates are equal (20 of 100 each), but on the one shared prompt the
    # protected arm is blocked 10 points more often.
    prot = _docs("A", 20, 100)
    ref = _docs("A", 10, 100) + _docs("B", 30, 100)
    raw = fairness_gates.g1(prot, _docs("A", 20, 100))
    assert raw["pass"] is True                                 # control
    out = fairness_gates.g1(prot, ref)
    assert out["diff"] == 0.0
    assert out["matched_diff"] == 10.0 and out["pass"] is False


def test_g1_has_no_matched_row_without_prompts():
    docs = [dict(d, prompt=None) for d in _docs("A", 5, 100)]
    assert "matched_diff" not in fairness_gates.g1(docs, docs)


# --- a release requirement per manifest ------------------------------------- #

def test_prereg_release_requirements_name_each_manifest_and_its_comparisons():
    text = (ROOT / "fairness" / "PREREG.md").read_text(encoding="utf-8")
    req = json.loads(re.findall(r"```json\n(.*?)\n```", text, re.S)[1])
    assert tuple(req["manifests"]) == fairness_release.RELEASE_MANIFESTS
    assert {k: tuple(v) for k, v in req["comparisons"].items()} == \
        fairness_release.REQUIREMENTS
    assert set(req["comparisons"]) == set(req["manifests"])


def test_prereg_confirmatory_block_binds_each_manifest_to_one_ruleset():
    text = (ROOT / "fairness" / "PREREG.md").read_text(encoding="utf-8")
    block = json.loads(re.findall(r"```json\n(.*?)\n```", text, re.S)[2])
    assert block == fairness_release.CONFIRMATORY
    assert set(block) <= set(fairness_release.RELEASE_MANIFESTS)


def test_the_committed_manifest_is_pinned_and_content_free():
    man, digest = fairness_corpora.load_manifest(str(MANIFEST))
    assert digest in fairness_release.REQUIREMENTS
    assert fairness_release.REQUIREMENTS[digest] == ("persuade-ell-vs-non-ell",)
    assert not man.get("documents") and not man.get("root")
    (table,) = man["tables"]
    assert table["sha256"] == ("sha256:f61319edd8bf16a982711ea0399fad59"
                               "c05afaec05cdf0767f16a2c05c467e23")
    assert [c["design"] for c in man["comparisons"]] == ["matched"]


def test_a_changed_ruleset_with_only_one_manifests_receipt_fails(tmp_path, monkeypatch):
    rec = json.loads((ROOT / "fairness" / "receipts" / "sha256-1c8f54b02d8aa211.json"
                      ).read_text("utf-8"))
    fp = rec["ruleset_version"]
    monkeypatch.setattr(fairness_release, "ruleset_fingerprint", lambda: fp)
    (tmp_path / (fp.replace(":", "-") + ".json")).write_text(json.dumps(rec))
    ok, lines = fairness_release.release_check(str(tmp_path), str(tmp_path / "none.json"))
    assert not ok
    persuade = [m for m in fairness_release.RELEASE_MANIFESTS if m != rec["manifest_sha256"]]
    assert persuade and any(persuade[0] in x for x in lines)


def test_the_liang_manifest_the_release_check_pins_is_committed():
    # A reader who writes their own manifest gets another hash, so the receipt
    # the release check accepts could not be reproduced without this file.
    man, digest = fairness_corpora.load_manifest(str(ROOT / "fairness" / "manifests"
                                                     / "liang-2023.json"))
    assert digest in fairness_release.REQUIREMENTS
    assert fairness_release.REQUIREMENTS[digest] == ("toefl-vs-abstracts", "toefl-vs-college")
    # Paths and hashes only: no document row carries text.
    assert {k for d in man["documents"] for k in d} == {"key", "path", "set", "sha256"}
    assert max(len(d["path"]) for d in man["documents"]) < 80
