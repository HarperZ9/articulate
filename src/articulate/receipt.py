#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
articulate.receipt -- re-derivable screenings.

A receipt records a check result together with the exact text hash and
ruleset fingerprint that produced it. Anyone can replay it: recompute the
findings on the same text under the same ruleset and confirm they match, without
trusting whoever issued the receipt first. The verdict uses a closed lattice,
Match / Drift / Unverifiable, and there is deliberately no Trusted or Approved
value: the receipt certifies re-derivability, never authority.

  Match         same text, same ruleset, identical findings and gate.
  Drift         same text and ruleset, but the re-derived findings differ
                (the checker code changed outside the pinned patterns, or the
                receipt was altered).
  Unverifiable  the ruleset changed, the text does not match the receipt's hash,
                or the receipt schema is unknown. Re-derivation cannot be done,
                so nothing is asserted.

A content-free AUDIT receipt (schema `articulate/receipt/audit/v2`) keeps no verbatim
document text: it drops the per-finding `match` substring and the exact start/end/col
offsets, keeping only the rule id, tier, category, and line. A team retains and
replays such a record without storing the sensitive text. It is content-free, never
information-free: which rules fired and roughly where (line) remain, which for a
closed-vocabulary rule narrows the flagged token to that rule's small, public
candidate set. The "hash" mode keeps a sha256 of the match for an equality check
against a known string; it is not confidentiality, because most rules draw from a
public closed vocabulary a holder can enumerate and hash. Use "drop" when the flagged
word must stay secret.

A receipt records which rules fired, where, and whether the gate held. It does
not show who or what wrote the text, and it carries the does-not-prove line.

Standard library only; no network.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from . import detector, modes, profiles
from .tool_text import DOES_NOT_PROVE

SCHEMA = "articulate/receipt/v2"
AUDIT_SCHEMA = "articulate/receipt/audit/v2"
# Schema v1 receipts came from the physical-line scanner (SCAN_ALGO 1). They are
# still read, so a replay names the reason it cannot re-derive them. Their
# ruleset fingerprint never matches a v2 ruleset.
LEGACY = {"articulate/receipt/v1": SCHEMA, "articulate/receipt/audit/v1": AUDIT_SCHEMA}
KNOWN = (SCHEMA, AUDIT_SCHEMA) + tuple(LEGACY)


def _sha256(s: str) -> str:
    return "sha256:" + hashlib.sha256(s.encode("utf-8")).hexdigest()


def text_sha256(text: str) -> str:
    """The receipt's canonical text hash, so a caller can tell a source changed
    since screening apart from a re-derivation result."""
    return _sha256(text)


def _pkg_version() -> str:
    try:
        from . import __version__
        return __version__
    except Exception:  # noqa: BLE001
        return "0.0.0"


def _normalize(result, redaction=None) -> list:
    """The verified core of a receipt: findings reduced to what a replay must
    reproduce, ordered so comparison is stable. A full receipt (redaction None)
    keeps the verbatim `match` and exact offsets. A content-free receipt ("drop" or
    "hash") keeps only rule_id, tier, category, and line: the exact offsets are
    dropped too, because `end - start` is the match length and, with a rule_id that
    names the rule's small candidate set, that length reconstructs the flagged word.
    "hash" additionally keeps a sha256 of the match, which is an equality fingerprint,
    not confidentiality (see the module docstring). Verify projects the re-derived
    findings to the receipt's redaction mode, so `match` and offsets are never part of
    the Match/Drift decision for a content-free receipt."""
    content_free = redaction in ("drop", "hash")
    out = []
    for f in result["high"] + result["medium"] + result["low"]:
        rec = {"rule_id": f["rule_id"], "tier": f["tier"], "category": f["category"],
               "line": f["line"], "end_line": f.get("end_line", f["line"])}
        if not content_free:
            rec["col"] = f["col"]
            rec["start"] = f["start"]
            rec["end"] = f["end"]
            rec["match"] = f["match"]
        elif redaction == "hash":
            rec["match_sha256"] = _sha256(f["match"])
        out.append(rec)
    out.sort(key=lambda x: (x["line"], x.get("start", 0), x["rule_id"]))
    return out


def _block_receipt(text, prof) -> list:
    """Per-paragraph counts for the receipt: each block's line range, its own
    text hash, and its counts by tier and by rule, in document order. No block
    carries a gate or a label; the gate belongs to the document."""
    out = []
    for b in detector.analyze_blocks(text, profile=prof):
        out.append({
            "index": b["index"],
            "start_line": b["start_line"], "end_line": b["end_line"],
            "text_sha256": _sha256(text[b["start"]:b["end"]]),
            "counts": b["counts"], "rule_counts": b["rule_counts"],
        })
    return out


def _load_screening(profile_name=None, mode=None):
    """(profile_name, profile_dict) for a receipt's screening. A mode wins over a
    profile, as it does in `articulate check`; the recorded profile name is then the
    mode's base profile. Raises modes.ModeError or profiles.ProfileError."""
    if mode:
        prof = modes.load(mode)          # raises ModeError on an unknown mode
        return modes.MODES[mode]["base"], prof
    pname = profile_name or profiles.DEFAULT
    return pname, profiles.load(pname)


def make_receipt(text: str, profile_name: str = None, *, mode: str = None,
                 per_span: bool = False, redact: str = None, reviewer: str = None,
                 created_at: str = None) -> dict:
    """Build a receipt. `redact` None gives the full content-bearing receipt;
    "drop" or "hash" gives a content-free audit receipt (schema audit/v2) that keeps
    no verbatim document text. The per-span blocks are already content-free.

    `mode` (for example "academic/argue") screens under that writing mode, which
    wins over `profile_name`. The receipt records it in a `mode` field beside the
    mode's base profile, so verify replays the same screening. A mode can promote a
    category to the gate, so a receipt that dropped it would describe a screening
    the author never ran.

    `created_at` (ISO-8601, defaults to now in UTC) and `reviewer` are the "who and
    when" envelope. They are issuance provenance, not part of the verified core, so
    verify never re-derives them and they never affect the Match/Drift decision."""
    if redact not in (None, "drop", "hash"):
        raise ValueError(f"redact must be None, 'drop', or 'hash'; got {redact!r}")
    pname, prof = _load_screening(profile_name, mode)
    r = detector.check_text(text, profile=prof)
    content_free = redact in ("drop", "hash")
    rec = {
        "schema": AUDIT_SCHEMA if content_free else SCHEMA,
        "articulate_version": _pkg_version(),
        "created_at": created_at or datetime.now(timezone.utc).isoformat(),
        "reviewer": reviewer,
        "ruleset_version": detector.ruleset_fingerprint(),
        "profile": pname,
        **({"mode": mode} if mode else {}),
        "text_sha256": _sha256(text),
        "gate": r["gate"],
        "findings_state": r["findings"],
        "words": r["words"],
        "counts": r["counts"],
        "findings": _normalize(r, redact),
        "does_not_prove": DOES_NOT_PROVE,
    }
    if content_free:
        rec["redaction"] = redact
    if per_span:
        rec["blocks"] = _block_receipt(text, prof)
    return rec


def _replay_profile(receipt):
    """(profile_dict, None), or (None, reason) when the receipt's screening cannot
    be loaded. A mode receipt re-derives under the mode, and its recorded profile
    must be the mode's base, so the two fields cannot disagree about what ran."""
    pname = receipt.get("profile", profiles.DEFAULT)
    mode = receipt.get("mode")
    if mode is None:
        try:
            return profiles.load(pname), None
        except profiles.ProfileError:
            return None, f"receipt names an unknown profile {pname!r}"
    if not isinstance(mode, str) or not mode:
        return None, "receipt mode is not a non-empty string"
    try:
        base, prof = _load_screening(mode=mode)
    except modes.ModeError:
        return None, f"receipt names an unknown mode {mode!r}"
    if pname != base:
        return None, f"receipt profile {pname!r} is not the base of mode {mode!r}"
    return prof, None


def verify_receipt(receipt: dict, text: str):
    """Replay a receipt against text. Returns (verdict, detail)."""
    if not isinstance(receipt, dict) or receipt.get("schema") not in KNOWN:
        return "Unverifiable", "unknown or missing receipt schema"
    # The schema and redaction must be a consistent pair, so a full receipt cannot be
    # relabeled content-free (or the reverse) to smuggle a false claim past verify.
    schema, redaction = receipt.get("schema"), receipt.get("redaction")
    schema = LEGACY.get(schema, schema)
    if schema == AUDIT_SCHEMA and redaction not in ("drop", "hash"):
        return "Unverifiable", "audit-schema receipt has no valid redaction mode"
    if schema == SCHEMA and redaction is not None:
        return "Unverifiable", "full-schema receipt declares a redaction mode"
    # A content-free receipt must carry no verbatim text in its own payload.
    if redaction in ("drop", "hash") and any("match" in f for f in receipt.get("findings", [])):
        return "Unverifiable", "content-free receipt carries a verbatim match field"
    current = detector.ruleset_fingerprint()
    if receipt.get("ruleset_version") != current:
        return ("Unverifiable",
                f"ruleset changed ({receipt.get('ruleset_version')} -> {current}); "
                f"cannot re-derive under a different ruleset")
    if receipt.get("text_sha256") != _sha256(text):
        return "Unverifiable", "text does not match the receipt's text hash"
    prof, problem = _replay_profile(receipt)
    if problem:
        return "Unverifiable", problem
    r = detector.check_text(text, profile=prof)
    # Project the re-derived findings to the receipt's redaction mode, so a
    # content-free receipt reads Match and `match`/offsets never drive the verdict.
    same = (_normalize(r, redaction) == receipt.get("findings")
            and r["gate"] == receipt.get("gate"))
    if not same:
        return "Drift", "re-derived findings or gate differ from the receipt"
    # A per-span receipt also re-derives its per-paragraph counts.
    if "blocks" in receipt and _block_receipt(text, prof) != receipt["blocks"]:
        return "Drift", "re-derived per-paragraph counts differ from the receipt"
    n = len(r["high"]) + len(r["medium"]) + len(r["low"])
    span = f", {len(receipt['blocks'])} paragraphs" if "blocks" in receipt else ""
    return "Match", f"re-derived {n} findings, gate {r['gate']}{span}"
