"""--spans: per-paragraph counts by rule, in document order.

A paragraph that carries findings shows them in place with its line range. No
paragraph carries a gate, a label or a score: the gate belongs to the document,
and a per-paragraph flag would point a reader at a paragraph as if it were
different in kind. The receipt records the same per-paragraph counts.
"""
from articulate import detector, profiles, receipt

MIXED = (
    "The rain fell for three days. Water pooled in the low field behind the barn.\n"
    "My grandfather watched it from the porch and said nothing.\n"
    "\n"
    "In today's rapidly evolving landscape, it is important to leverage comprehensive\n"
    "and robust solutions across the board. Moreover, these transformative frameworks\n"
    "deliver seamless, impactful outcomes that enhance productivity and streamline\n"
    "workflows. Ultimately, this underscores the pivotal role of innovative, cutting-edge\n"
    "approaches in driving meaningful value for every stakeholder in the ecosystem.\n"
)


def test_segment_blocks_tracks_line_ranges_and_offsets():
    blocks = detector.segment_blocks(MIXED)
    assert len(blocks) == 2
    assert (blocks[0]["start_line"], blocks[0]["end_line"]) == (1, 2)
    assert (blocks[1]["start_line"], blocks[1]["end_line"]) == (4, 8)
    for b in blocks:
        assert MIXED[b["start"]:b["end"]] == b["text"]


def test_findings_localize_to_their_paragraph():
    blocks = detector.analyze_blocks(MIXED, profile=profiles.load("house"))
    first, second = blocks
    assert sum(first["counts"].values()) < sum(second["counts"].values())
    assert second["rule_counts"]
    assert (second["start_line"], second["end_line"]) == (4, 8)


def test_no_paragraph_carries_a_gate_label_or_score():
    for b in detector.analyze_blocks(MIXED, profile=profiles.load("house")):
        assert not {"gate", "verdict", "texture_score", "elevated", "clean"} & set(b)


def test_span_finding_offsets_are_document_relative():
    blocks = detector.analyze_blocks(MIXED, profile=profiles.load("house"))
    hits = blocks[1]["high"] + blocks[1]["medium"]
    assert hits, "the second paragraph must produce findings"
    for f in hits:
        assert 4 <= f["line"] <= f["end_line"] <= 8     # document lines, not block lines
        assert MIXED[f["start"]:f["end"]] == f["match"]


def test_fenced_code_block_stays_one_span():
    doc = "intro paragraph.\n\n```\ncode line\n\nmore code\n```\n\noutro.\n"
    blocks = detector.segment_blocks(doc)
    fenced = [b for b in blocks if "```" in b["text"]]
    assert len(fenced) == 1 and "more code" in fenced[0]["text"]


def test_per_span_receipt_replays_to_match():
    rec = receipt.make_receipt(MIXED, "house", per_span=True)
    assert "blocks" in rec and len(rec["blocks"]) == 2
    assert receipt.verify_receipt(rec, MIXED)[0] == "Match"


def test_tampered_block_counts_are_drift():
    rec = receipt.make_receipt(MIXED, "house", per_span=True)
    rec["blocks"][1]["counts"]["high"] = 0
    assert receipt.verify_receipt(rec, MIXED)[0] == "Drift"


def test_default_receipt_has_no_blocks():
    rec = receipt.make_receipt(MIXED, "house")
    assert "blocks" not in rec                      # opt-in, backward compatible
    assert receipt.verify_receipt(rec, MIXED)[0] == "Match"
