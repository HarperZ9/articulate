"""Findings must not move when a paragraph is rewrapped.

Before this change the scanner ran one re.search per rule per physical line. A
writer who puts one sentence per line (common in LaTeX and in some Markdown
styles) got a different result from one who soft-wraps, and a rule matched at
most once per line. The scanner now reads a paragraph as one logical line with
an offset map back to the file, counts every match, and runs line-start rules at
every sentence start. Headings, list items, table rows, block quotes, verse and
screenplay lines keep their physical lines.

These tests guard that fix against regression. They measure nothing about
fairness.
"""
import time

import articulate
from articulate import profiles

SOFT = ("It is\nimportant to note that the survey ran twice. The second run\n"
        "used a new sample of students from the same school. Both runs agree\n"
        "on the main result. Firstly, the\ncounts match.\n")
ONE_PER_LINE = ("It is important to note that the survey ran twice.\n"
                "The second run used a new sample of students from the same school.\n"
                "Both runs agree on the main result.\n"
                "Firstly, the counts match.\n")


def _hm(text, prof="essay"):
    r = articulate.check_text(text, profile=profiles.load(prof))
    return sorted((f["tier"], f["category"], f["match"].replace("\n", " "))
                  for f in r["high"] + r["medium"]), r


def test_soft_wrap_and_one_sentence_per_line_agree():
    a, ra = _hm(SOFT)
    b, rb = _hm(ONE_PER_LINE)
    assert a == b
    assert ra["gate"] == rb["gate"]
    assert ra["cadence"]["words"] == rb["cadence"]["words"]


def test_every_match_on_a_line_is_counted():
    r = articulate.check_text("We really tried and really failed.\n",
                              profile=profiles.load("flavored"))
    assert sum(1 for f in r["high"] + r["medium"] + r["low"]
               if f["match"].lower() == "really") == 2


def test_a_match_across_a_soft_wrap_maps_back_to_the_file():
    text = "The plan was sound. It is important\nto note that it failed.\n"
    r = articulate.check_text(text, profile=profiles.load("essay"))
    hits = [f for f in r["medium"] if f["category"] == "throat-clearing"]
    assert hits
    f = hits[0]
    assert text[f["start"]:f["end"]] == f["match"]
    assert f["line"] == 1 and f["end_line"] == 2


def test_single_line_findings_carry_end_line():
    r = articulate.check_text("In conclusion, the test passed.\n",
                              profile=profiles.load("essay"))
    assert all(f["end_line"] == f["line"] for f in r["high"] + r["medium"] + r["low"])


def test_line_start_rules_run_at_every_sentence_start():
    one = articulate.check_text("The data are in. Firstly, we check the counts.\n",
                                profile=profiles.load("essay"))
    two = articulate.check_text("The data are in.\nFirstly, we check the counts.\n",
                                profile=profiles.load("essay"))
    cats = lambda r: sorted(f["category"] for t in ("high", "medium", "low")  # noqa: E731
                            for f in r[t])
    assert "enumeration" in cats(one)
    assert cats(one) == cats(two)


def test_headings_and_list_items_do_not_join_the_next_line():
    text = "# Methods\nWe ran the survey twice.\n\n- first item\n- second item\n"
    r = articulate.check_text(text, profile=profiles.load("flavored"))
    for f in r["high"] + r["medium"] + r["low"]:
        assert f["end_line"] == f["line"]
        assert text[f["start"]:f["end"]] == f["match"]


def test_verse_keeps_physical_lines():
    poem = "the rain comes down\nand not the snow but the rain\n"
    r = articulate.check_text(poem, profile=profiles.load("poetry"))
    assert all(f["end_line"] == f["line"] for f in r["high"] + r["medium"] + r["low"])


def test_a_long_soft_wrapped_paragraph_stays_fast():
    # Joining lines lengthens every regex input, so the ReDoS budget is rechecked
    # on paragraph-length inputs.
    para = ("not only the cat but " * 20 + "\n") * 400
    for name in ("flavored", "essay"):
        start = time.perf_counter()
        articulate.check_text(para, profile=profiles.load(name))
        assert time.perf_counter() - start < 3.0, name


def test_receipts_are_schema_v2_and_carry_end_line():
    from articulate import receipt
    text = "The plan was sound. It is important\nto note that it failed.\n"
    rec = receipt.make_receipt(text, "essay")
    assert rec["schema"] == "articulate/receipt/v2"
    assert all("end_line" in f for f in rec["findings"])
    assert receipt.verify_receipt(rec, text)[0] == "Match"
    free = receipt.make_receipt(text, "essay", redact="drop")
    assert free["schema"] == "articulate/receipt/audit/v2"
    assert receipt.verify_receipt(free, text)[0] == "Match"


def test_a_v1_receipt_reads_unverifiable_with_a_reason():
    from articulate import receipt
    text = "In conclusion, the test passed.\n"
    rec = receipt.make_receipt(text, "essay")
    rec["schema"] = "articulate/receipt/v1"
    rec["ruleset_version"] = "sha256:0000000000000000"
    verdict, detail = receipt.verify_receipt(rec, text)
    assert verdict == "Unverifiable" and "ruleset changed" in detail
