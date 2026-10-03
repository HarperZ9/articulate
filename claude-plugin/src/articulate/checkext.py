"""The check behind every command: the pinned detector, then the rule layer.

`check_text` runs articulate.detector.check_text unchanged. When the profile
switches on rules outside the detector (domain rule packs, project
terminology), it scans for them with articulate.rules_ext, adds the findings
by tier, and recomputes clean, gate, blocking_count and verdict with the same
logic the detector uses: GATE_TIERS for the profile's slop, gate_promote, and
MIN_WORDS_FOR_VERDICT. These findings never feed the texture score. With no
such rules the detector's result is returned as it is, so output stays
byte-identical.

`analyze_blocks` gives the per-paragraph view under the same rules.
Standard library only.
"""
from . import detector, rules_ext

_TIERS = (("high", "HIGH"), ("medium", "MEDIUM"), ("low", "LOW"))


def _regate(result, profile):
    slop = profile.get("slop", "flavored")
    gate = detector.GATE_TIERS.get(slop, frozenset({"HIGH"}))
    promote = set(profile.get("gate_promote", ()))
    blocking = 0
    for key, tier in _TIERS:
        if tier in gate:
            blocking += len(result[key])
        elif promote:
            blocking += sum(1 for f in result[key] if f["category"] in promote)
    n_dev = len(result["high"]) + len(result["medium"])
    if n_dev:
        verdict = "flagged"
    elif not result["sufficient"] and not result["low"]:
        verdict = "unverifiable"
    else:
        verdict = "clean"
    result.update(clean=n_dev == 0, gate="blocked" if blocking else "ok",
                  blocking_count=blocking, verdict=verdict)
    return result


def check_text(text, *, profile=None, allow=()):
    """detector.check_text plus the profile's rule packs and terminology."""
    result = detector.check_text(text, profile=profile, allow=allow)
    if not rules_ext.active(profile):
        return result
    extra = rules_ext.scan(text, text.splitlines(keepends=True), profile)
    for (key, tier), found in zip(_TIERS, extra):
        result[key] = result[key] + [detector._finding(tier, f) for f in found]
    return _regate(result, profile)


def analyze_blocks(text, *, profile=None, allow=()):
    """detector.analyze_blocks under the same rule layer as check_text."""
    if not rules_ext.active(profile):
        return detector.analyze_blocks(text, profile=profile, allow=allow)
    out = []
    for b in detector.segment_blocks(text):
        r = check_text(b["text"], profile=profile, allow=allow)
        for key, _tier in _TIERS:
            for f in r[key]:
                f["line"] += b["start_line"] - 1
                f["start"] += b["start"]
                f["end"] += b["start"]
        out.append({
            "index": b["index"],
            "start_line": b["start_line"], "end_line": b["end_line"],
            "start": b["start"], "end": b["end"],
            "gate": r["gate"], "clean": r["clean"],
            "verdict": r["verdict"], "sufficient": r["sufficient"],
            "blocking_count": r["blocking_count"],
            "texture_score": r["texture_score"], "elevated": r["elevated"],
            "counts": {"high": len(r["high"]), "medium": len(r["medium"]),
                       "low": len(r["low"])},
            "high": r["high"], "medium": r["medium"], "low": r["low"],
            "snippet": b["text"].strip()[:100],
        })
    return out
