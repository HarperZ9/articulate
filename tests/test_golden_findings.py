"""A golden digest of every finding over the shipped corpus, pinned to the
ruleset fingerprint that produced it.

The fingerprint hashes the rule tables and the scanner constants. It cannot see
a change to the scanner's control flow. This test can: if the findings over the
corpus change while the fingerprint stays the same, the change moved behavior
without moving the fingerprint, and a receipt issued before it would replay to a
false Match. When a reviewed change moves the fingerprint on purpose, regenerate
the pin with `python tests/test_golden_findings.py --write`.

These tests guard the replay contract. They measure nothing about fairness.
"""
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PIN = pathlib.Path(__file__).resolve().parent / "golden_findings.json"
PROFILES = ("flavored", "essay", "research", "narrative", "poetry", "screenplay")


def _corpus():
    # Sort by the POSIX relative path string. Path objects compare
    # case-insensitively on Windows and case-sensitively elsewhere, so sorting
    # them directly put corpus/README.md in a different place on each OS and
    # moved the digest.
    files = [p for p in (ROOT / "corpus").rglob("*")
             if p.suffix in (".txt", ".md") and p.is_file()]
    yield from sorted(files, key=lambda p: p.relative_to(ROOT).as_posix())


def findings_digest():
    """sha256 over the (rule, tier, line, offsets) of every finding, the gate and
    the cadence record,
    for each corpus file under each pinned profile."""
    import articulate
    from articulate import profiles

    rows = []
    for p in _corpus():
        text = p.read_bytes().decode("utf-8").replace("\r\n", "\n")
        for name in PROFILES:
            r = articulate.check_text(text, profile=profiles.load(name))
            found = sorted((f["rule_id"], f["tier"], f["line"], f["start"], f["end"])
                           for t in ("high", "medium", "low") for f in r[t])
            cad = sorted((k, v) for k, v in r["cadence"].items())
            rows.append([p.relative_to(ROOT).as_posix(), name, r["gate"], found, cad])
    blob = json.dumps(rows, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _current():
    from articulate import detector
    return {"fingerprint": detector.ruleset_fingerprint(), "digest": findings_digest()}


def test_findings_match_the_pin_for_this_fingerprint():
    pin = json.loads(PIN.read_text(encoding="utf-8"))
    now = _current()
    assert now["fingerprint"] == pin["fingerprint"], (
        "the ruleset fingerprint moved; review the change and regenerate the pin "
        "with `python tests/test_golden_findings.py --write`")
    assert now["digest"] == pin["digest"], (
        "findings over the corpus changed while the fingerprint stayed the same: "
        "a behavior change the fingerprint does not cover")


def test_the_corpus_is_not_empty():
    # Control: a digest over nothing would pin nothing.
    assert len(list(_corpus())) >= 5


if __name__ == "__main__" and "--write" in sys.argv:
    sys.path.insert(0, str(ROOT / "src"))
    PIN.write_text(json.dumps(_current(), indent=1) + "\n", encoding="utf-8")
    print(PIN.read_text(encoding="utf-8"))
