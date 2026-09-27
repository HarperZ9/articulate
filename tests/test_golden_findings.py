"""A golden digest of every finding over the shipped corpus, pinned to the
ruleset fingerprint that produced it.

The fingerprint hashes the rule tables and the scanner constants. It cannot see
a change to the scanner's control flow. This test can: if the findings over the
corpus change while the fingerprint stays the same, the change moved behavior
without moving the fingerprint, and a receipt issued before it would replay to a
false Match. When a reviewed change moves the fingerprint on purpose, regenerate
the pin with `python tests/test_golden_findings.py --write`. The writer refuses a
new digest under the same fingerprint, since that is the change this test exists
to catch; pass `--corpus-changed` as well when only the corpus changed.

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


def write_pin(argv, pin=PIN, current=None):
    """Regenerate the pin; 0 on success, 1 when refused. A new digest under the
    fingerprint the pin already names is refused unless `--corpus-changed` says
    the corpus moved: otherwise regenerating would hide the behavior change the
    test above catches."""
    now = current or _current()
    old = json.loads(pin.read_text(encoding="utf-8")) if pin.is_file() else {}
    if (now["fingerprint"] == old.get("fingerprint") and now["digest"] != old.get("digest")
            and "--corpus-changed" not in argv):
        print("refused: the findings changed while the fingerprint stayed the same. Move "
              "the fingerprint with the change, or pass --corpus-changed when only the "
              "corpus changed.", file=sys.stderr)
        return 1
    pin.write_bytes((json.dumps(now, indent=1) + "\n").encode("utf-8"))
    return 0


def test_the_writer_refuses_a_new_digest_under_the_same_fingerprint(tmp_path):
    pin = tmp_path / "pin.json"
    pin.write_text(json.dumps({"fingerprint": "sha256:aa", "digest": "sha256:1"}))
    moved = {"fingerprint": "sha256:aa", "digest": "sha256:2"}
    assert write_pin(["--write"], pin, moved) == 1
    assert json.loads(pin.read_text())["digest"] == "sha256:1"
    assert write_pin(["--write", "--corpus-changed"], pin, moved) == 0
    assert json.loads(pin.read_text())["digest"] == "sha256:2"
    # Control: a moved fingerprint regenerates without the flag.
    assert write_pin(["--write"], pin, {"fingerprint": "sha256:bb", "digest": "sha256:3"}) == 0


if __name__ == "__main__" and "--write" in sys.argv:
    sys.path.insert(0, str(ROOT / "src"))
    code = write_pin(sys.argv)
    print(PIN.read_text(encoding="utf-8"))
    sys.exit(code)
