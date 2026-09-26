#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.gate -- the library API: check_text, the per-block view and the
instruction-injection scan. Standard library only.
"""
from .markup import FENCE, _mk
from .rules_low import INJECTION
from .scan import scan_lines

# slop level -> which precision tiers hard-gate (block). HIGH is the precise
# device tier; MEDIUM adds the frontier-model register tells; LOW never gates.
GATE_TIERS = {
    "off": frozenset(),
    "flavored": frozenset({"HIGH"}),
    "strict": frozenset({"HIGH", "MEDIUM"}),
}

# Below this many prose words there are too few tokens to assert a clean verdict;
# the texture score already returns 0 under the same floor. The floor governs a
# clean verdict only, never a reading of who or what wrote the text. A short
# text with no findings at all reads "unverifiable" rather than a confident "clean".
# A banned device is unambiguous at any length, so a finding still reads "flagged".
MIN_WORDS_FOR_VERDICT = 30


def _finding(tier, f, gates=False):
    """Attach the precision tier, and whether the finding blocks under the
    profile in use, to a span-level finding record."""
    return {**f, "tier": tier, "gates": gates}


def gates_finding(tier, category, profile):
    """True when a finding of this tier and category blocks under the profile:
    its tier is gated by the slop level, or a mode promotes its category."""
    slop = (profile or {}).get("slop", "flavored")
    if tier in GATE_TIERS.get(slop, frozenset({"HIGH"})):
        return True
    return category in set((profile or {}).get("gate_promote", ()))


def check_text(text, *, profile=None, allow=()):
    """The library API. Scan text under an optional register profile (a dict from
    articulate.profiles.load). Returns findings, a profile-aware gate verdict, the
    graded texture score, and cadence. No filesystem, no network."""
    keep = tuple(allow)
    if profile:
        keep += tuple(profile.get("keep", ()))
    # Genre-layer options, read straight off the profile/mode dict. A plain
    # register profile carries none of these, so the scan is unchanged for it.
    p = profile or {}
    genre = {
        "unit": p.get("unit", "sentence"),
        "structural_classify": p.get("structural_classify"),
        "dialogue_exempt": p.get("dialogue_exempt", False),
        "quote_exempt_all": p.get("quote_exempt_all", False),
        "fiction_slop": p.get("fiction_slop", False),
        "suppress_categories": p.get("suppress_categories", ()),
    }
    lines = text.splitlines(keepends=True)
    high, medium, low, doc = scan_lines(lines, keep, genre=genre)
    slop = (profile or {}).get("slop", "flavored")
    # gate_promote: a mode may block a specific category even when its tier is not
    # gated by the slop level (porting the flywheel per-category `hard` tuple). It
    # only ADDS gating, so the HIGH banned-device floor can never be removed.
    tiers = {}
    blocking = 0
    for tier, arr in (("HIGH", high), ("MEDIUM", medium), ("LOW", low)):
        tiers[tier] = [_finding(tier, f, gates_finding(tier, f["category"], profile))
                       for f in arr]
        blocking += sum(1 for f in tiers[tier] if f["gates"])
    # Calibrated three-way verdict, separate from the device gate. A device is
    # valid at any length, so it reads "flagged"; a device-clean text with no
    # findings and too few words reads "unverifiable"; otherwise "clean".
    words = doc.get("words", 0)
    sufficient = words >= MIN_WORDS_FOR_VERDICT
    n_dev = len(high) + len(medium)
    if n_dev:
        verdict = "flagged"
    elif not sufficient and (n_dev + len(low)) == 0:
        verdict = "unverifiable"
    else:
        verdict = "clean"
    return {
        "clean": len(high) + len(medium) == 0,
        "gate": "blocked" if blocking else "ok",
        "verdict": verdict,
        "sufficient": sufficient,
        "slop": slop,
        "blocking_count": blocking,
        "texture_score": doc.get("score", 0),
        "elevated": doc.get("elevated", False),
        "high": tiers["HIGH"],
        "medium": tiers["MEDIUM"],
        "low": tiers["LOW"],
        "cadence": {
            "words": doc.get("words", 0),
            "mean_sentence_len": doc.get("mean_len"),
            "cv": doc.get("cv"),
            "uniform": doc.get("uniform", False),
            "repetitive_openers": doc.get("repetitive_openers", False),
            "passive_rate": doc.get("passive_rate", 0),
            "adverb_rate": doc.get("adverb_rate", 0),
        },
    }


def segment_blocks(text):
    """Split text into paragraph blocks on blank-line boundaries, keeping each
    block's document line range and character offset. A fenced code block stays
    one block even when it contains blank lines, so a fence is never cut in half."""
    lines = text.splitlines(keepends=True)
    offsets, acc = [], 0
    for ln in lines:
        offsets.append(acc)
        acc += len(ln)
    ranges, start = [], None
    in_fence = False
    for i, ln in enumerate(lines):
        if FENCE.match(ln):
            in_fence = not in_fence
            if start is None:
                start = i
            continue
        if ln.strip() == "" and not in_fence:
            if start is not None:
                ranges.append((start, i - 1))
                start = None
        elif start is None:
            start = i
    if start is not None:
        ranges.append((start, len(lines) - 1))
    out = []
    for idx, (s, e) in enumerate(ranges):
        out.append({
            "index": idx,
            "start_line": s + 1, "end_line": e + 1,
            "start": offsets[s], "end": offsets[e] + len(lines[e]),
            "text": "".join(lines[s:e + 1]),
        })
    return out


def analyze_blocks(text, *, profile=None, allow=()):
    """Per-block (paragraph) verdicts. Each block is scanned on its own, so one
    paragraph that carries findings is flagged in place with its line range instead
    of smearing a whole-file texture score, and a clean document is not moved by an
    aggregate. Findings are translated back to document coordinates. This is a
    reporting view over the same ruleset; it changes no gate. A block verdict says
    where the findings are, never who or what wrote the block."""
    out = []
    for b in segment_blocks(text):
        r = check_text(b["text"], profile=profile, allow=allow)
        for tier in ("high", "medium", "low"):
            for f in r[tier]:
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


def detect_injection(text):
    """Flag lines that read as an instruction to an assistant rather than prose to
    edit. The editor calls this to warn before a rewrite and to keep the model on
    a content-as-data footing. Report-only and separate from check_text: it never
    gates a verdict and is not part of the pinned ruleset, because a document may
    quote these patterns legitimately (a paper about prompt injection, say).

    It is a literal-ASCII heuristic, so it will miss paraphrased jailbreaks,
    homoglyph or base64-obfuscated directives, and inline (mid-line) role headers.
    The content-as-data boundary in the editor, not this warning, is the actual
    guardrail; the warning is a reviewer-facing signal on top of it."""
    lines = text.splitlines(keepends=True)
    offsets, acc = [], 0
    for raw in lines:
        offsets.append(acc)
        acc += len(raw)
    out = []
    for i, raw in enumerate(lines, 1):
        snippet = raw.strip()[:100]
        for cat, label, rx in INJECTION:
            m = rx.search(raw)
            if m:
                out.append(_mk(i, offsets[i - 1], cat, label, m.start(), m.end(), raw, snippet))
                break   # one flag per line is enough to warn
    return out
