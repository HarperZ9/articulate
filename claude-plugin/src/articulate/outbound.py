"""The outbound check: a message to be sent in the author's name, placed
against two references, his own writing and the register of the person who
will read it.

reference(samples) keeps one row of feature values per sample, no text.
compare(draft, author, recipient) places each feature of the draft against
the band each reference spans. A feature is reported only where no reference
holds the draft inside its band, so a register the reader shares is never
flagged as drift. Each reported feature carries the line that pushes it
furthest, found by leaving one sentence out at a time.

The check never applies the house prose rules or the writing linter to the
author's voice: those rules govern documents, and applied to his voice they
push it toward the shape of model text. There is no total and no detector.
Standard library only.
"""
from collections import Counter

from . import outbound_features as of

SCHEMA = "articulate/outbound-reference/v1"
REPORT_SCHEMA = "articulate/voice-outbound/v1"
RARE_CLASS = 0.05
MIN_CLASS_SAMPLES = 5
MIN_BAND_SAMPLES = 1
SCOPE = ("Places each feature of the draft against the author's writing and, when given, the "
         "reader's own messages. A feature is named only where the draft sits outside both. The "
         "nine tells were measured on English news and web prose; the reader reference is what "
         "keeps a shared register from being read as drift.")
TELLS = {
    "noun_carry": "tell 1, nouns carried from one sentence to the next",
    "vocab_variety": "tell 2, vocabulary variety",
    "words_per_clause": "tell 3, words per clause",
    "sentence_words": "tell 4, words per sentence",
    "proper_names_per_100": "tell 5, proper names and IDs",
    "repeated_trigram_share": "tell 6, repeated three-word runs",
    "common_word_share": "tell 7, share of the commonest words",
    "word_length_spread": "tell 7, spread of word lengths (a proxy for frequency band)",
    "numbers_per_100": "tell 8, numbers",
    "vague_quantity_per_100": "tell 8, vague quantities (many, several, a few)",
    "new_abstract_share": "tell 9, sentences that add a new abstract noun",
    "facts_per_sentence": "tell 9, checkable facts per sentence",
    "clause_spread": "spread of clause lengths",
    "stance_per_100": "stance and plain-speech words",
    "softener_per_100": "softened framing (one small thing, quick note, happy to)",
    "ask_per_100": "pitch or ask phrases",
    "surface_marks_per_100": "surface marks (.., slashes, abbreviations, lower-case starts)",
    "semicolon_colon_per_100": "semicolons and colons",
    "opener": "how the message opens",
    "signoff": "a sign-off word before the name",
    "greeting": "a greeting line",
}


# The side of the band on which a value moves toward the shape of model text.
# A value outside the band on the other side is listed but is not a finding:
# an email about dates carries more numbers than his posts, and that is the
# subject, not drift.
MODEL_SIDE = {"noun_carry": "below", "vocab_variety": "above", "words_per_clause": "below",
              "sentence_words": "below", "proper_names_per_100": "below",
              "repeated_trigram_share": "below", "common_word_share": "below",
              "word_length_spread": "below", "numbers_per_100": "below",
              "vague_quantity_per_100": "above", "new_abstract_share": "above",
              "facts_per_sentence": "below", "clause_spread": "below", "stance_per_100": "below",
              "softener_per_100": "above", "ask_per_100": "above",
              "surface_marks_per_100": "below", "semicolon_colon_per_100": "above"}


def _split_messages(text):
    parts, cur = [], []
    for line in text.replace("\r\n", "\n").split("\n"):
        if line.strip() in ("---", "----", "-----"):
            parts.append("\n".join(cur))
            cur = []
        else:
            cur.append(line)
    parts.append("\n".join(cur))
    return [p.strip() for p in parts if p.strip()]


def reference(samples, *, basis):
    """Feature rows from sample texts. basis names whose writing it is."""
    if isinstance(samples, str):
        samples = _split_messages(samples)
    if not samples or not all(isinstance(s, str) and s.strip() for s in samples):
        raise ValueError("a reference needs one or more non-empty messages")
    rows = [of.measure(s) for s in samples]
    return {"schema": SCHEMA, "basis": basis, "samples": len(rows), "rows": rows}


def _quantile(ordered, p):
    pos = p * (len(ordered) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def band(ref, feature):
    """(low, high, n) of the middle 80 percent of the reference, widened a
    little and more for few samples; None when no sample measures it."""
    values = sorted(r[feature] for r in ref["rows"] if r.get(feature) is not None)
    if len(values) < MIN_BAND_SAMPLES:
        return None
    lo, hi = _quantile(values, 0.1), _quantile(values, 0.9)
    mid = abs(lo + hi) / 2
    margin = max(0.1 * (hi - lo), (0.05 + 0.2 / len(values)) * mid)
    return round(max(0.0, lo - margin), 3), round(hi + margin, 3), len(values)


def _place_numeric(value, ref, feature):
    b = band(ref, feature) if ref else None
    if value is None or b is None:
        return {"verdict": "unknown"}
    low, high, n = b
    out = {"low": low, "high": high, "samples": n}
    if low <= value <= high:
        return dict(out, verdict="inside")
    scale = (high - low) or max(abs(high), 1.0)
    edge = high if value > high else low
    return dict(out, verdict="above" if value > high else "below",
                excess=round(abs(value - edge) / scale, 2))


def _place_class(value, ref, feature):
    if not ref:
        return {"verdict": "unknown"}
    seen = Counter(r.get(feature) for r in ref["rows"] if r.get(feature) is not None)
    total = sum(seen.values())
    share = round(seen.get(value, 0) / total, 3) if total else 0.0
    if total < MIN_CLASS_SAMPLES:
        verdict = "inside" if seen.get(value) else "unknown"
    else:
        verdict = "inside" if share >= RARE_CLASS else "rare"
    return {"verdict": verdict, "share": share, "samples": total}


def _flagged(places, feature):
    verdicts = [p["verdict"] for p in places if p]
    outside = [v for v in verdicts if v not in ("unknown", "inside")]
    side = MODEL_SIDE.get(feature, "rare")
    return "inside" not in verdicts and bool(outside) and all(v == side for v in outside)


def _excess_of(value, place):
    if place.get("verdict") not in ("above", "below") or value is None:
        return 0.0
    edge = place["high"] if place["verdict"] == "above" else place["low"]
    return abs(value - edge)


def _locate(draft, feature, place):
    """The sentence whose removal moves the value furthest back toward the band."""
    rows = of.sentence_rows(draft)
    if len(rows) < 2:
        return rows[0] if rows else (None, "")
    base = _excess_of(of.measure(draft)[feature], place)
    best, gain = rows[0], -1.0
    for i, row in enumerate(rows):
        rest = " ".join(s for j, (_, s) in enumerate(rows) if j != i)
        value = of.measure(rest, floor=1)[feature]
        if value is None:
            continue
        g = base - _excess_of(value, place)
        if g > gain:
            best, gain = row, g
    return best


def _class_line(draft, feature):
    lines = draft.replace("\r\n", "\n").strip("\n").split("\n")
    _, _, greeting, signoff = of.body(draft)
    if feature == "opener":
        rows = of.sentence_rows(draft)
        return rows[0] if rows else (1, lines[0])
    if feature == "greeting":
        return 1, greeting or lines[0]
    hits = [i for i, line in enumerate(lines) if signoff and signoff in line]
    n = hits[-1] if hits else len(lines) - 1
    return n + 1, signoff or lines[n]


def _finding(draft, feature, value, places):
    if feature in of.CATEGORICAL:
        line, excerpt = _class_line(draft, feature)
    else:
        primary = next(p for p in places if p and p["verdict"] in ("above", "below"))
        line, excerpt = _locate(draft, feature, primary)
    excerpt = " ".join(excerpt.split())
    return {"feature": feature, "about": TELLS[feature], "value": value, "line": line,
            "excerpt": excerpt[:140] + ("..." if len(excerpt) > 140 else "")}


def compare(draft, author, recipient=None):
    """Per-feature placement of the draft; findings only where no reference holds it."""
    if not isinstance(draft, str) or not draft.strip():
        raise ValueError("the outbound check needs draft text")
    for ref in (author, recipient):
        if ref is not None and (not isinstance(ref, dict) or ref.get("schema") != SCHEMA):
            raise ValueError("not an articulate outbound reference")
    values = of.measure(draft)
    features, findings = [], []
    for feature in of.FEATURES:
        place = _place_class if feature in of.CATEGORICAL else _place_numeric
        a = place(values[feature], author, feature)
        r = place(values[feature], recipient, feature) if recipient else None
        features.append({"feature": feature, "value": values[feature], "author": a,
                         "recipient": r})
        if _flagged([a, r], feature):
            findings.append(_finding(draft, feature, values[feature],
                                     [p for p in (a, r) if p]))
    return {"schema": REPORT_SCHEMA, "features": features, "findings": findings,
            "outside_author": [f["feature"] for f in features
                               if f["author"]["verdict"] not in ("inside", "unknown")],
            "recipient_given": recipient is not None,
            "house_rules_applied": False, "ai_detector_consulted": False, "scope": SCOPE}


def format_report(report):
    out = []
    for f in report["findings"]:
        out.append(f"line {f['line']}: {f['about']}: draft {f['value']}, outside "
                   f"{'both references' if report['recipient_given'] else 'your range'}"
                   f"\n    {f['excerpt']}")
    if not out:
        out.append("No feature sits outside both references.")
    if not report["recipient_given"]:
        out.append("No reader messages given, so this is against your writing alone.")
    out.append(report["scope"])
    return "\n".join(out)
