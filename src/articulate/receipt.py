#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
articulate.receipt -- re-derivable verdicts.

A receipt records a detection result together with the exact text hash and
ruleset fingerprint that produced it. Anyone can replay it: recompute the
findings on the same text under the same ruleset and confirm they match, without
trusting whoever issued the receipt first. The verdict uses a closed lattice,
Match / Drift / Unverifiable, and there is deliberately no Trusted or Approved
value: the receipt certifies re-derivability, never authority.

  Match         same text, same ruleset, identical findings and gate.
  Drift         same text and ruleset, but the re-derived findings differ
                (the detector code changed outside the pinned patterns, or the
                receipt was altered).
  Unverifiable  the ruleset changed, the text does not match the receipt's hash,
                or the receipt schema is unknown. Re-derivation cannot be done,
                so nothing is asserted.

A content-free AUDIT receipt (schema `articulate/receipt/audit/v1`) keeps no verbatim
document text: it drops the per-finding `match` substring and the exact start/end/col
offsets, keeping only the rule id, tier, category, and line. A team retains and
replays such a record without storing the sensitive text. It is content-free, never
information-free: which rules fired and roughly where (line) remain, which for a
closed-vocabulary rule narrows the flagged token to that rule's small, public
candidate set. The "hash" mode keeps a sha256 of the match for an equality check
against a known string; it is not confidentiality, because most rules draw from a
public closed vocabulary a holder can enumerate and hash. Use "drop" when the flagged
word must stay secret.

Standard library only; no network.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from . import detector, modes, profiles

SCHEMA = "articulate/receipt/v1"
AUDIT_SCHEMA = "articulate/receipt/audit/v1"


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
               "line": f["line"]}
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
    """Per-span (per-paragraph) verdicts for the receipt: which block is flagged,
    its line range, its own text hash, and its localized texture. This is what
    makes the receipt reportable per span, beyond the whole-document verdict."""
    out = []
    for b in detector.analyze_blocks(text, profile=prof):
        out.append({
            "index": b["index"],
            "start_line": b["start_line"], "end_line": b["end_line"],
            "text_sha256": _sha256(text[b["start"]:b["end"]]),
            "gate": b["gate"], "clean": b["clean"], "verdict": b["verdict"],
            "texture_score": b["texture_score"], "elevated": b["elevated"],
            "counts": b["counts"],
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
    "drop" or "hash" gives a content-free audit receipt (schema audit/v1) that keeps
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
        "clean": r["clean"],
        "verdict": r["verdict"],
        "sufficient": r["sufficient"],
        "texture_score": r["texture_score"],
        "counts": {"high": len(r["high"]), "medium": len(r["medium"]),
                   "low": len(r["low"])},
        "findings": _normalize(r, redact),
    }
    if content_free:
        rec["redaction"] = redact
    if per_span:
        rec["blocks"] = _block_receipt(text, prof)
    return rec


def verify_receipt(receipt: dict, text: str):
    """Replay a receipt against text. Returns (verdict, detail)."""
    if not isinstance(receipt, dict) or receipt.get("schema") not in (SCHEMA, AUDIT_SCHEMA):
        return "Unverifiable", "unknown or missing receipt schema"
    # The schema and redaction must be a consistent pair, so a full receipt cannot be
    # relabeled content-free (or the reverse) to smuggle a false claim past verify.
    schema, redaction = receipt.get("schema"), receipt.get("redaction")
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
    pname = receipt.get("profile", profiles.DEFAULT)
    mode = receipt.get("mode")
    if mode is not None:
        # A mode receipt re-derives under the mode. Its recorded profile must be the
        # mode's base, so the two fields cannot disagree about what ran.
        if not isinstance(mode, str) or not mode:
            return "Unverifiable", "receipt mode is not a non-empty string"
        try:
            base, prof = _load_screening(mode=mode)
        except modes.ModeError:
            return "Unverifiable", f"receipt names an unknown mode {mode!r}"
        if pname != base:
            return ("Unverifiable",
                    f"receipt profile {pname!r} is not the base of mode {mode!r}")
    else:
        try:
            prof = profiles.load(pname)
        except profiles.ProfileError:
            return "Unverifiable", f"receipt names an unknown profile {pname!r}"
    r = detector.check_text(text, profile=prof)
    # Project the re-derived findings to the receipt's redaction mode, so a
    # content-free receipt reads Match and `match`/offsets never drive the verdict.
    same = (_normalize(r, redaction) == receipt.get("findings")
            and r["gate"] == receipt.get("gate")
            and r["texture_score"] == receipt.get("texture_score"))
    if not same:
        return "Drift", "re-derived findings or verdict differ from the receipt"
    # Below the word floor a device-clean text with no findings has too little
    # signal to assert; the receipt abstains and makes no confident clean claim.
    if r["verdict"] == "unverifiable":
        return ("Unverifiable",
                f"below the {detector.MIN_WORDS_FOR_VERDICT}-word signal floor; "
                f"no confident clean verdict on this little text")
    # A per-span receipt also re-derives its per-block verdicts.
    if "blocks" in receipt and _block_receipt(text, prof) != receipt["blocks"]:
        return "Drift", "re-derived per-span block verdicts differ from the receipt"
    n = len(r["high"]) + len(r["medium"]) + len(r["low"])
    span = f", {len(receipt['blocks'])} spans" if "blocks" in receipt else ""
    return "Match", f"re-derived {n} findings, gate {r['gate']}, texture {r['texture_score']}{span}"
