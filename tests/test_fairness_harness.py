"""The fairness harness on a synthetic corpus written in the test.

The corpus is made up: one set leans on "really", the other does not. The tests
check that the harness reads a manifest, refuses a file whose hash moved, keeps
text out of its receipt and computes the gates. They guard the harness against
regression and measure nothing about fairness to any real group of writers.
"""
import hashlib
import json

import pytest

from articulate import fairness, fairness_corpora, fairness_gates

PROTECTED = [f"The bus was really late on day {i}. I really wanted to get home and "
             f"cook dinner for my family before the game started at seven." for i in range(12)]
REFERENCE = [f"The bus came on time on day {i}. I walked home, cooked dinner for my "
             f"family and sat down before the game started at seven." for i in range(12)]
MARKER = "cooked dinner"


def _write_corpus(tmp_path):
    docs = []
    for name, texts in (("learners", PROTECTED), ("reference", REFERENCE)):
        for i, t in enumerate(texts):
            p = tmp_path / name / f"{i:02d}.txt"
            p.parent.mkdir(exist_ok=True)
            p.write_bytes(t.encode("utf-8"))
            docs.append({"set": name, "path": f"{name}/{i:02d}.txt", "key": str(i),
                         "sha256": "sha256:" + hashlib.sha256(t.encode()).hexdigest()})
    man = {"schema": fairness_corpora.SCHEMA,
           "corpora": {"synthetic": {"licence": "test fixture", "upstream": "this test",
                                     "retrieved": "2026-09-26"}},
           "sets": {"learners": {"corpus": "synthetic",
                                 "groups": {"first_language": "L2"}},
                    "reference": {"corpus": "synthetic",
                                  "groups": {"first_language": "L1"}}},
           "documents": docs,
           "comparisons": [{"name": "learners-vs-reference", "dimension": "first_language",
                            "protected": "learners", "reference": "reference",
                            "design": "proxy"}],
           "pairs": [{"name": "same-index", "a": "learners", "b": "reference"}]}
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(man), encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def receipt(tmp_path_factory):
    path = _write_corpus(tmp_path_factory.mktemp("corpus"))
    return fairness.run(str(path), names=["flavored"])


def test_receipt_is_content_free(receipt):
    blob = json.dumps(receipt, default=list)
    assert MARKER not in blob and "really late" not in blob
    assert receipt["schema"] == fairness.SCHEMA
    assert "who or what wrote" in receipt["does_not_prove"]


def test_receipt_names_the_manifest_and_ruleset(receipt):
    assert receipt["manifest_sha256"].startswith("sha256:")
    assert receipt["ruleset_version"].startswith("sha256:")
    assert receipt["measured_profiles"] == ["flavored"]


def test_g1_reports_both_directions(receipt):
    (cfg,) = receipt["results"].values()
    g1 = cfg["comparisons"]["learners-vs-reference"]["g1"]
    assert g1["diff"] == -g1["reverse_diff"]
    assert g1["ci"][0] <= g1["diff"] <= g1["ci"][1]
    assert g1["min_detectable"] > 0


def test_g2_has_one_of_four_states(receipt):
    (cfg,) = receipt["results"].values()
    for row in cfg["comparisons"]["learners-vs-reference"]["g2"].values():
        assert row["toward_protected"]["state"] in (
            "skewed", "not skewed", "bounded", "inconclusive")


def test_g3_is_report_only(receipt):
    (cfg,) = receipt["results"].values()
    assert cfg["pairs"]["same-index"]["gates"] is False


def test_g6_is_reported_as_not_run(receipt):
    assert receipt["g6"]["state"] == "not run"


def test_layout_check_ran(receipt):
    (cfg,) = receipt["results"].values()
    assert cfg["g4"]["applies"] is True and cfg["g4"]["changed"] >= 0


def test_a_moved_file_is_refused(tmp_path):
    path = _write_corpus(tmp_path)
    (tmp_path / "learners" / "00.txt").write_bytes(b"edited")
    with pytest.raises(fairness_corpora.CorpusError):
        fairness.run(str(path), names=["flavored"])


def test_an_unknown_group_dimension_is_refused(tmp_path):
    path = _write_corpus(tmp_path)
    man = json.loads(path.read_text(encoding="utf-8"))
    man["sets"]["learners"]["groups"] = {"nationality": "x"}
    path.write_text(json.dumps(man), encoding="utf-8")
    with pytest.raises(fairness_corpora.CorpusError):
        fairness_corpora.load_manifest(str(path))


def test_skew_state_rules():
    few = [{"words": 100, "rules": {"R": 1}} for _ in range(3)] + \
          [{"words": 100, "rules": {}} for _ in range(97)]
    none = [{"words": 100, "rules": {}} for _ in range(100)]
    many = [{"words": 100, "rules": {"R": 3}} for _ in range(40)]
    assert fairness_gates.g2_state(none, none, "R")["state"] == "bounded"
    assert fairness_gates.g2_state(many, none, "R")["state"] == "skewed"
    # three documents, under the five-document floor and over the 2% share
    assert fairness_gates.g2_state(few, none, "R")["state"] == "inconclusive"
    assert fairness_gates.g2_state(many, many, "R")["state"] == "not skewed"


def test_windows_are_sentence_aligned():
    text = " ".join(f"Sentence number {i} has five words." for i in range(40))
    parts = fairness_corpora.windows(text, 20, 10)
    assert all(p.endswith(".") for p in parts)
    assert all(len(p.split()) >= 10 for p in parts)


def test_rewrap_puts_one_sentence_per_line():
    assert fairness.rewrap("One. Two!\nThree?") == "One.\nTwo!\nThree?\n"


def test_bound_profiles_cover_the_default_and_every_path_target():
    bound = set(fairness.bound_profiles())
    from articulate import profiles
    assert profiles.DEFAULT in bound
    for _rx, name in profiles.PATH_RULES:
        if name not in fairness.house_profiles():
            assert name in bound


def test_release_check_fails_without_a_receipt(tmp_path):
    ok, reasons = fairness.release_check(str(tmp_path))
    assert not ok and "no fairness receipt" in reasons[0]


def test_release_check_fails_when_a_bound_profile_is_missing(tmp_path, receipt):
    fp = receipt["ruleset_version"]
    rec = dict(receipt, gates=dict(receipt["gates"], release_ok=True))
    (tmp_path / (fp.replace(":", "-") + ".json")).write_text(json.dumps(rec, default=list))
    ok, reasons = fairness.release_check(str(tmp_path))
    assert not ok and any("omits bound profiles" in r for r in reasons)


def test_prereg_thresholds_match_the_code():
    import pathlib
    import re
    text = (pathlib.Path(__file__).resolve().parent.parent / "fairness" / "PREREG.md"
            ).read_text(encoding="utf-8")
    block = re.search(r"```json\n(.*?)\n```", text, re.S).group(1)
    assert json.loads(block) == fairness_gates.THRESHOLDS
