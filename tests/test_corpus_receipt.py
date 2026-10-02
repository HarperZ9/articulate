"""A corpus receipt replays: Match on the same texts, Drift when the findings
differ, Unverifiable when a text or the ruleset no longer matches."""
import copy
import importlib

from voice_fixtures import VARIED, templated_docs


def cr():
    return importlib.import_module("articulate.corpus_receipt")


def test_match_on_the_same_documents():
    docs = templated_docs()
    rec = cr().make_corpus_receipt(docs)
    assert rec["schema"] == "articulate/corpus-receipt/v1"
    assert rec["ai_detector_consulted"] is False
    verdict, _ = cr().verify_corpus_receipt(rec, docs)
    assert verdict == "Match"


def test_one_changed_byte_is_unverifiable_by_hash():
    docs = templated_docs()
    rec = cr().make_corpus_receipt(docs)
    docs[1]["text"] = docs[1]["text"].replace("ledger", "Ledger", 1) + " "
    verdict, detail = cr().verify_corpus_receipt(rec, docs)
    assert verdict == "Unverifiable" and "hash" in detail


def test_altered_findings_read_drift():
    docs = templated_docs()
    rec = cr().make_corpus_receipt(docs)
    forged = copy.deepcopy(rec)
    forged["findings"] = forged["findings"][1:]
    verdict, _ = cr().verify_corpus_receipt(forged, docs)
    assert verdict == "Drift"


def test_fingerprint_mismatch_is_unverifiable():
    docs = templated_docs()
    rec = cr().make_corpus_receipt(docs)
    rec["corpus_fingerprint"] = "sha256:0000000000000000"
    verdict, detail = cr().verify_corpus_receipt(rec, docs)
    assert verdict == "Unverifiable" and "fingerprint" in detail


def test_fingerprint_covers_the_detector_ruleset():
    from articulate import detector
    fp = cr().corpus_fingerprint()
    assert fp.startswith("sha256:") and fp != detector.ruleset_fingerprint()
    assert cr().CORPUS_RULESET_SEMVER == "0.8.0"


def test_existing_single_document_receipts_still_verify():
    from articulate import detector, receipt
    text = VARIED[0][2]
    rec = receipt.make_receipt(text)
    assert receipt.verify_receipt(rec, text)[0] == "Match"
    assert detector.ruleset_fingerprint() == "sha256:9f78a7484bb20f84"


def test_voice_compare_record_replays():
    from articulate import voice
    profile = voice.build_profile([t for _, _, t in VARIED])
    rec = voice.compare(templated_docs()[0]["text"], profile)
    assert rec["schema"] == "articulate/voice-compare/v1"
    assert cr().verify_voice_compare(rec, templated_docs()[0]["text"], profile)[0] == "Match"
    assert cr().verify_voice_compare(rec, "other text " * 40, profile)[0] == "Unverifiable"
