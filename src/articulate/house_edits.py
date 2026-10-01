"""The closed list of edits the house transform may make, and the verifier
that checks a candidate holds those edits and nothing else.

Four rules, each exact:

- dash: an em dash, or an en dash with a space on each side, becomes ", ";
- space: a run of two or more spaces or tabs between two words becomes one;
- residue: a sentence on the closed opener or closer list is deleted. Openers
  count only at the start of the first prose paragraph, closers only at the
  end of the last one;
- residue-paragraph: a first or last paragraph that holds nothing but such
  sentences is deleted with one paragraph break.

Nothing inside a protected span (code, quotes, links, citations, numbers,
disclosures) is touched. Every other change to wording is left to the model,
through the brief, and is never made here.
"""
import re

from .house_spec import spec
from .meaning_guard import _PARAGRAPH, guard_rewrite, protected_spans

DASH = re.compile(r"[ \t]*—[ \t]*|[ \t]+–[ \t]+")
SPACE = re.compile(r"(?<=\S)[ \t]{2,}(?=\S)")
_SENTENCE = re.compile(r"[^.!?\n]+[.!?]+[\"'”’)]*")
RULES = ("dash", "space", "residue", "residue-paragraph")


def _compiled(kind):
    return [re.compile(p, re.I) for p in spec()["residue"][kind]]


OPENERS, CLOSERS = _compiled("openers"), _compiled("closers")


def is_residue(sentence, patterns):
    s = " ".join(sentence.split())
    return bool(s) and any(p.fullmatch(s) for p in patterns)


def residue_run(text, patterns):
    """Sentences of text if every one is on the list, else None."""
    found = [m for m in _SENTENCE.finditer(text)]
    if not found or "".join(m.group() for m in found).replace(" ", "") != text.strip().replace(" ", ""):
        return None
    return found if all(is_residue(m.group(), patterns) for m in found) else None


def paragraphs(text):
    """(start, end) of every paragraph; separators lie between them."""
    out, pos = [], 0
    for part in _PARAGRAPH.split(text):
        if _PARAGRAPH.fullmatch(part):
            pos += len(part)
            continue
        out.append((pos, pos + len(part)))
        pos += len(part)
    return out


def _overlaps(a, b, spans):
    return any(s["start"] < b and a < s["end"] for s in spans)


def _prose(text, para, spans):
    a, b = para
    body = text[a:b]
    return body.strip() and not any(s["kind"] in ("disclosure", "code", "quote", "html")
                                    and s["start"] <= a + len(body) - len(body.lstrip())
                                    and s["end"] >= b - (len(body) - len(body.rstrip()))
                                    for s in spans)


def _residue_edits(text, spans, at_start, at_end):
    paras = [p for p in paragraphs(text) if _prose(text, p, spans)]
    edits = []
    if at_start and paras:
        edits += _edge(text, paras, spans, OPENERS, first=True)
    if at_end and paras:
        for e in _edge(text, paras, spans, CLOSERS, first=False):
            if not any(x["start"] < e["end"] and e["start"] < x["end"] for x in edits):
                edits.append(e)
    return edits


def _edge(text, paras, spans, patterns, first):
    """Edits that remove residue at the start (first) or end of the prose."""
    edits = []
    order = paras if first else list(reversed(paras))
    for a, b in order:
        if _overlaps(a, b, [s for s in spans if s["kind"] in ("code", "disclosure")]):
            break
        if residue_run(text[a:b], patterns):
            if first:
                end = b + len(_PARAGRAPH.match(text, b).group()) if _PARAGRAPH.match(text, b) else b
                edits.append({"rule": "residue-paragraph", "start": a, "end": end, "new": ""})
            else:
                sep = re.search(r"\s*$", text[:a])
                edits.append({"rule": "residue-paragraph", "start": sep.start(), "end": b, "new": ""})
            continue
        found = list(_SENTENCE.finditer(text, a, b))
        run = found if first else list(reversed(found))
        cut = []
        for m in run:
            if not is_residue(m.group(), patterns) or _overlaps(m.start(), m.end(), spans):
                break
            cut.append(m)
        if cut and len(cut) < len(found):
            if first:
                start, end = a, cut[-1].end()
                end += len(re.match(r"[ \t]*", text[end:]).group())
            else:
                start, end = cut[-1].start(), b
                start -= len(re.search(r"[ \t]*$", text[:start]).group())
            edits.append({"rule": "residue", "start": start, "end": end, "new": ""})
        break
    return edits


def compute(text, no_em_dash=True):
    """The edit list for text, in original offsets, sorted and non-overlapping."""
    spans = protected_spans(text)
    edits = _residue_edits(text, spans, at_start=True, at_end=True)
    return _inline_edits(text, spans, edits, no_em_dash)


def compute_part(text, at_start, at_end, no_em_dash=True):
    spans = protected_spans(text)
    edits = _residue_edits(text, spans, at_start, at_end)
    return _inline_edits(text, spans, edits, no_em_dash)


def _inline_edits(text, spans, edits, no_em_dash):
    taken = [(e["start"], e["end"]) for e in edits]
    patterns = ([("dash", DASH, ", ")] if no_em_dash else []) + [("space", SPACE, " ")]
    for rule, pattern, new in patterns:
        for m in pattern.finditer(text):
            a, b = m.start(), m.end()
            if _overlaps(a, b, spans) or any(x < b and a < y for x, y in taken):
                continue
            edits.append({"rule": rule, "start": a, "end": b, "new": new})
            taken.append((a, b))
    return sorted(edits, key=lambda e: e["start"])


def apply(text, edits):
    out, pos = [], 0
    for e in sorted(edits, key=lambda e: e["start"]):
        out.append(text[pos:e["start"]])
        out.append(e["new"])
        pos = e["end"]
    out.append(text[pos:])
    return "".join(out)


def _rule_ok(text, e, spans):
    old = text[e["start"]:e["end"]]
    rule, new = e.get("rule"), e.get("new")
    if rule == "dash":
        return new == ", " and DASH.fullmatch(old) and not _overlaps(e["start"], e["end"], spans)
    if rule == "space":
        return new == " " and re.fullmatch(r"[ \t]{2,}", old) and not _overlaps(e["start"], e["end"], spans)
    if rule == "residue":
        return new == "" and bool(residue_run(old, OPENERS) or residue_run(old, CLOSERS))
    if rule == "residue-paragraph":
        return new == "" and bool(residue_run(old, OPENERS) or residue_run(old, CLOSERS))
    return False


def verify_edits(original, candidate, edits):
    """{ok, reasons}: candidate is original with exactly these edits, each on
    the closed list, and the paragraphs left in place pass the meaning guard."""
    reasons, spans, last = [], protected_spans(original), 0
    for e in sorted(edits, key=lambda e: e.get("start", -1)):
        if not (isinstance(e.get("start"), int) and isinstance(e.get("end"), int)
                and last <= e["start"] <= e["end"] <= len(original)):
            reasons.append("edit offsets overlap or fall outside the text")
            break
        if not _rule_ok(original, e, spans):
            reasons.append("edit %s at %d is not on the closed list" % (e.get("rule"), e["start"]))
        last = e["end"]
    if not reasons and apply(original, edits) != candidate:
        reasons.append("candidate differs from the original with the listed edits")
    if not reasons:
        kept = apply(original, [e for e in edits if e["rule"] == "residue-paragraph"])
        refused = guard_rewrite(kept, candidate)["refused"]
        reasons += ["meaning guard: " + ", ".join(r["reasons"]) for r in refused]
    return {"ok": not reasons, "reasons": reasons}
