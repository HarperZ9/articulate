"""The benchmark is an expected-findings regression with a false-finding
control. It sets no target on text from any source.

These tests guard the benchmark contract. They measure nothing about fairness.
"""
import pathlib

from articulate import bench

CORPUS = pathlib.Path(__file__).resolve().parent.parent / "corpus"


def test_every_expectation_holds_on_the_shipped_corpus():
    rows, failures = bench.run(str(CORPUS))
    assert failures == 0, [r for r in rows if not r[3]]
    assert any(r[0] == "patterns" for r in rows) and any(r[0] == "control" for r in rows)


def test_a_lost_pattern_fails_the_benchmark(tmp_path):
    import json
    import shutil
    work = tmp_path / "corpus"
    shutil.copytree(CORPUS, work)
    expect = json.loads((work / "patterns" / "expect.json").read_text(encoding="utf-8"))
    expect["patterns"]["medium.md"]["categories"].append("marketing")
    (work / "patterns" / "expect.json").write_text(json.dumps(expect), encoding="utf-8")
    _rows, failures = bench.run(str(work))
    assert failures == 1


def test_the_corpus_carries_no_origin_labels():
    names = {p.name for p in CORPUS.rglob("*")}
    assert not {n for n in names if n.endswith(".pangram")}
    assert not (CORPUS / "ai").exists() and not (CORPUS / "human").exists()
