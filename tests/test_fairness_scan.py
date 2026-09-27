"""Scanning documents in several processes gives the same receipt, byte for byte.

A synthetic table corpus written in the test: two sets, prompts and scores,
texts that block under some profiles and not others. It measures nothing about
any real group of writers. It checks that `--jobs` changes how the documents
are scanned and nothing in the receipt.
"""
import csv
import hashlib
import json

import pytest

from articulate import fairness, fairness_corpora, fairness_scan

TEXTS = [
    "It should be noted that the bus was late. We delve into the rich tapestry of "
    "travel. In today's fast-paced world, buses matter.",
    "The bus was really very late. I really wanted to go home. Honestly, it was "
    "truly a game-changer for the whole community.",
    "Studies show that phones distract drivers. Experts agree that texting is "
    "dangerous. It is important to note that laws help.",
    "Phones should be banned while driving. Drivers who text crash more often, and "
    "the data from 2019 shows a rise in crashes.",
    "Some students like online classes.\nOthers do not, because they miss their "
    "friends and the well-known routine of a school day.",
]


def _write(tmp_path, n=20):
    path = tmp_path / "table.csv"
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, ["id", "text", "prompt", "score", "group"])
        w.writeheader()
        for i in range(n):
            w.writerow({"id": f"D{i:03d}", "text": f"{TEXTS[i % len(TEXTS)]} Case {i}.",
                        "prompt": ("Phones", "Buses")[i % 2], "score": str(1 + i % 6),
                        "group": "A" if i % 3 == 0 else "B"})
    digest = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    man = {"schema": fairness_corpora.SCHEMA,
           "corpora": {"t": {"licence": "test fixture", "upstream": "this test",
                             "retrieved": "2026-09-27"}},
           "sets": {"a": {"corpus": "t", "groups": {"first_language": "A"}},
                    "b": {"corpus": "t", "groups": {"first_language": "B"}}},
           "tables": [{"corpus": "t", "path": "table.csv", "sha256": digest, "format": "csv",
                       "id": "id", "text": "text", "prompt": "prompt", "score": "score",
                       "sets": {"a": {"group": "A"}, "b": {"group": "B"}}}],
           "comparisons": [{"name": "a-vs-b", "dimension": "first_language",
                            "protected": "a", "reference": "b", "design": "matched"}]}
    mpath = tmp_path / "manifest.json"
    mpath.write_bytes(json.dumps(man).encode("utf-8"))
    return mpath


def _receipt_bytes(tmp_path, mpath, jobs):
    out = tmp_path / f"receipt-{jobs}.json"
    assert fairness.main([str(mpath), "--out", str(out), "--jobs", str(jobs)]) == 0
    return out.read_bytes()


@pytest.fixture(scope="module")
def corpus(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("scan")
    return tmp, _write(tmp)


def test_the_corpus_exercises_blocking_and_rules(corpus):
    tmp, mpath = corpus
    rec = json.loads(_receipt_bytes(tmp, mpath, 1))
    blocked = sum(x["blocked"][0] for v in rec["results"].values() for x in v["g7"].values())
    rules = sum(len(c["g2"]) for v in rec["results"].values()
                for c in v["comparisons"].values())
    assert blocked > 0 and rules > 0
    assert len(rec["results"]) > 1


@pytest.mark.parametrize("jobs", [2, 3])
def test_several_processes_write_the_same_receipt_bytes(corpus, jobs):
    tmp, mpath = corpus
    assert _receipt_bytes(tmp, mpath, jobs) == _receipt_bytes(tmp, mpath, 1)


def test_scan_keeps_document_order_and_one_entry_per_configuration(corpus):
    _tmp, mpath = corpus
    man, _ = fairness_corpora.load_manifest(str(mpath))
    configs, members = fairness.configs_for(["essay", "flavored", "house"])
    docs = list(fairness_corpora.load_documents(man, str(mpath.parent)))
    one = list(fairness_scan.scan(docs, configs, members, jobs=1))
    two = list(fairness_scan.scan(docs, configs, members, jobs=2))
    assert [r["key"] for r, _ in two] == [r["key"] for r, _ in docs]
    assert all(len(per) == len(configs) for _r, per in two)
    assert one == two
