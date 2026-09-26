"""P0-d: per-span (per-paragraph) writing-quality verdict.

One paragraph that carries the findings, in an otherwise clean document, must be
flagged in place with its line range, instead of an aggregate texture score
smearing across the whole file. The receipt is reportable per span and re-derives per block.
"""
import articulate
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


def test_findings_localize_to_the_flagged_paragraph():
    blocks = detector.analyze_blocks(MIXED, profile=profiles.load("house"))
    clean, flagged = blocks[0], blocks[1]
    assert clean["gate"] == "ok"                 # the clean paragraph is not flagged
    assert flagged["gate"] == "blocked"          # the flagged paragraph carries a HIGH device
    assert flagged["texture_score"] > clean["texture_score"]
    assert flagged["elevated"] is True and clean["texture_score"] == 0
    # the flag names the flagged paragraph's own line range, not the whole file
    assert (flagged["start_line"], flagged["end_line"]) == (4, 8)


def test_whole_file_score_does_not_smear_the_concentration():
    whole = articulate.check_text(MIXED, profile=profiles.load("house"))
    flagged = detector.analyze_blocks(MIXED, profile=profiles.load("house"))[1]
    # the paragraph that carries the findings scores at least as high on its own as
    # the diluted whole-document aggregate, so the signal is localized, not averaged away
    assert flagged["texture_score"] >= whole["texture_score"]


def test_span_finding_offsets_are_document_relative():
    blocks = detector.analyze_blocks(MIXED, profile=profiles.load("house"))
    hits = blocks[1]["high"] + blocks[1]["medium"]
    assert hits, "the flagged paragraph must produce findings"
    for f in hits:
        assert 4 <= f["line"] <= 8                 # document line, not block line
        assert MIXED[f["start"]:f["end"]] == f["match"]


def test_fenced_code_block_stays_one_span():
    doc = "intro paragraph.\n\n```\ncode line\n\nmore code\n```\n\noutro.\n"
    blocks = detector.segment_blocks(doc)
    fenced = [b for b in blocks if "```" in b["text"]]
    assert len(fenced) == 1 and "more code" in fenced[0]["text"]


# --- the per-span receipt --------------------------------------------------- #

def test_per_span_receipt_replays_to_match():
    rec = receipt.make_receipt(MIXED, "house", per_span=True)
    assert "blocks" in rec and len(rec["blocks"]) == 2
    verdict, _ = receipt.verify_receipt(rec, MIXED)
    assert verdict == "Match"


def test_tampered_block_verdict_is_drift():
    rec = receipt.make_receipt(MIXED, "house", per_span=True)
    rec["blocks"][1]["texture_score"] = 0          # forge the flagged paragraph clean
    verdict, _ = receipt.verify_receipt(rec, MIXED)
    assert verdict == "Drift"


def test_default_receipt_has_no_blocks():
    rec = receipt.make_receipt(MIXED, "house")
    assert "blocks" not in rec                      # opt-in, backward compatible
    assert receipt.verify_receipt(rec, MIXED)[0] == "Match"
