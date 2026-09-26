#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.gate -- the library API: check_text, the per-block view and the
instruction-injection scan.

check_text returns the findings, whether each one blocks under the profile in
use, and one pass-or-block signal: the gate. It returns no score and no verdict
about the text. `findings` says only whether any HIGH or MEDIUM finding exists.

Standard library only.
"""
from .aliases import profile_field
from .density import density
from .markup import FENCE, _mk
from .rule_reasons import HOUSE_CATEGORIES, resolve_all
from .rules_low import INJECTION
from .scan import scan_lines
from .tool_text import DOES_NOT_PROVE

# gate level -> which tiers block. HIGH is the narrow tier; MEDIUM adds rules
# with a cited reader cost; LOW never blocks.
GATE_TIERS = {
    "off": frozenset(),
    "flavored": frozenset({"HIGH"}),
    "strict": frozenset({"HIGH", "MEDIUM"}),
}


def gate_level(profile):
    """A profile's gate level. The field's pre-0.7.0 name is read for one minor
    version (articulate.aliases)."""
    return profile_field(profile, "gate_level", "flavored")


def _finding(tier, f, gates=False):
    """Attach the tier, whether the finding blocks under the profile in use, and
    whether it belongs to the house pack, to a span-level record."""
    return {**f, "tier": tier, "gates": gates, "house": f["category"] in HOUSE_CATEGORIES}


def house_retier(high, medium, low, profile):
    """Outside a house profile, a house-pack finding reports at LOW and never
    blocks. Under a house profile it keeps its table tier."""
    if (profile or {}).get("house"):
        return high, medium, low
    moved = [f for f in high + medium if f["category"] in HOUSE_CATEGORIES]
    keep = lambda arr: [f for f in arr if f["category"] not in HOUSE_CATEGORIES]  # noqa: E731
    return keep(high), keep(medium), low + moved


def gates_finding(tier, category, profile):
    """True when a finding of this tier and category blocks under the profile:
    its tier is gated by the gate level, or a mode promotes its category."""
    if tier in GATE_TIERS.get(gate_level(profile), frozenset({"HIGH"})):
        return True
    return category in set(resolve_all((profile or {}).get("gate_promote", ())))


def _genre(p):
    return {
        "unit": p.get("unit", "sentence"),
        "structural_classify": p.get("structural_classify"),
        "dialogue_exempt": p.get("dialogue_exempt", False),
        "quote_exempt_all": p.get("quote_exempt_all", False),
        "fiction_slop": p.get("fiction_slop", False),
        "suppress_categories": p.get("suppress_categories", ()),
    }


def rule_counts(findings):
    out = {}
    for f in findings:
        out[f["rule_id"]] = out.get(f["rule_id"], 0) + 1
    return dict(sorted(out.items()))


def check_text(text, *, profile=None, allow=()):
    """The library API. Scan text under an optional profile (a dict from
    articulate.profiles.load or modes.load). Returns the findings, per-rule
    counts, the gate, density and cadence statistics. No filesystem, no network."""
    p = profile or {}
    keep = tuple(allow) + tuple(p.get("keep", ()))
    high, medium, low, doc = scan_lines(text.splitlines(keepends=True), keep,
                                        genre=_genre(p))
    high, medium, low = house_retier(high, medium, low, profile)
    # gate_promote lets a mode block a category its tier would not block. It only
    # adds gating, so it can never lift the HIGH tier.
    tiers = {tier: [_finding(tier, f, gates_finding(tier, f["category"], profile))
                    for f in arr]
             for tier, arr in (("HIGH", high), ("MEDIUM", medium), ("LOW", low))}
    blocking = sum(1 for arr in tiers.values() for f in arr if f["gates"])
    everything = tiers["HIGH"] + tiers["MEDIUM"] + tiers["LOW"]
    result = {
        "gate": "blocked" if blocking else "ok",
        "gate_level": gate_level(profile),
        "house": bool(p.get("house")),
        "blocking_count": blocking,
        "findings": "has_findings" if tiers["HIGH"] or tiers["MEDIUM"] else "no_findings",
        "clean": not (tiers["HIGH"] or tiers["MEDIUM"]),
        "words": doc.get("words", 0),
        "counts": {"high": len(high), "medium": len(medium), "low": len(low)},
        "rule_counts": rule_counts(everything),
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
        "does_not_prove": DOES_NOT_PROVE,
    }
    result["density"] = density(result)
    return result


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
    return [{"index": idx, "start_line": s + 1, "end_line": e + 1,
             "start": offsets[s], "end": offsets[e] + len(lines[e]),
             "text": "".join(lines[s:e + 1])} for idx, (s, e) in enumerate(ranges)]


def analyze_blocks(text, *, profile=None, allow=()):
    """Per-paragraph findings in document order: each block's line range, counts
    by tier and by rule, and its findings in document coordinates. It carries no
    per-paragraph gate, no label and no score; the gate belongs to the document."""
    out = []
    for b in segment_blocks(text):
        r = check_text(b["text"], profile=profile, allow=allow)
        for tier in ("high", "medium", "low"):
            for f in r[tier]:
                f["line"] += b["start_line"] - 1
                f["end_line"] += b["start_line"] - 1
                f["start"] += b["start"]
                f["end"] += b["start"]
        out.append({
            "index": b["index"],
            "start_line": b["start_line"], "end_line": b["end_line"],
            "start": b["start"], "end": b["end"],
            "counts": r["counts"], "rule_counts": r["rule_counts"],
            "high": r["high"], "medium": r["medium"], "low": r["low"],
            "snippet": b["text"].strip()[:100],
        })
    return out


def detect_injection(text):
    """Flag lines that read as instructions to a model reading the document, where
    prose to edit was expected. The editor calls this to warn before a rewrite and
    to keep the model on a content-as-data footing. Report-only and separate from
    check_text: it never gates and is not part of the pinned ruleset, because a
    document may quote these patterns legitimately (a paper about prompt
    injection, say).

    It is a literal-ASCII heuristic, so it will miss paraphrased jailbreaks,
    homoglyph or base64-obfuscated directives, and inline (mid-line) role headers.
    The content-as-data boundary in the editor is the guardrail; this warning is a
    reviewer-facing signal on top of it."""
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
