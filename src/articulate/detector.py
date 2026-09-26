#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
articulate.detector -- the public face of the scanner.

The scanner lives in small modules: the rule tables (rules_high,
rules_medium_register, rules_medium_structure, rules_low), the auxiliary
regexes (lexicon), markup masks (markup), multi-line signals (advisories),
the line scanner (scan), cadence statistics (cadence), the library API (gate)
and the ruleset fingerprint (fingerprint). This module re-exports their public
names, so `from articulate.detector import check_text` keeps working, and it
carries the plain console report for `python -m articulate.detector`.

Usage:  python -m articulate.detector FILE [FILE ...] [--verbose] [--json] [--passes]

The console report reads each file under the profile its path resolves to, the
same way `articulate check` does.

Exit code is always 0 so a save is never blocked. A caller that wants a hard gate
reads the --json payload or uses `articulate check --gate`.
"""
import json
import os
import sys

from . import masking  # noqa: F401  (re-exported for callers)
from .advisories import (FRAGMENT_OPENER, PRONOUN_SUBJ, STOP4,  # noqa: F401
                         document_advisories, find_anaphora_runs,
                         find_contrast_pairs, find_fragment_openers,
                         find_repeated_ngrams, paragraph_word_counts)
from .binary import binary_reason  # noqa: F401
from .cadence import cadence_stats  # noqa: F401
from .fingerprint import (RULESET_SEMVER, known_categories,  # noqa: F401
                          ruleset_fingerprint)
from .gate import (GATE_TIERS, analyze_blocks,  # noqa: F401
                   check_text, detect_injection, segment_blocks)
from .lexicon import (ADVERB, BOLD_SPAN, BULLET, DIGIT, EMOJI,  # noqa: F401
                      EXPLETIVE, FIRSTWORD, HEADING, HEDGE_WORDS, NEG,
                      NGRAM_STOP, NOMINAL, OPENER_STOP, PASSIVE,
                      VAGUE_QUANT, WORD)
from .markup import (ALLOW_EXEMPT_CATEGORIES, ALLOW_TAG, FENCE,  # noqa: F401
                     INLINE_CODE, QUOTED, TAG, TEX, URL, allowed,
                     classify_fountain, is_md_hr, is_md_table_sep, mask_quotes,
                     read_allowlist, split_sentences, strip_markup)
from .logical import sentence_spans, units  # noqa: F401
from .rules_high import HIGH  # noqa: F401
from .rules_low import FICTION_SLOP, INJECTION, LOW, REGISTER_JARGON  # noqa: F401
from .scan import MEDIUM, scan, scan_lines  # noqa: F401
from .tool_text import DOES_NOT_PROVE  # noqa: F401

# Prose files carry em-dashes, emoji, and smart quotes. The Windows console
# defaults to cp1252 and would crash on them, so force a lossy UTF-8 stream.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass


def report_text(path, high, medium, low, doc, verbose):
    base = os.path.basename(path)
    n_hit = len(high) + len(medium)
    if n_hit == 0:
        print(f"[writing] {base}: no HIGH or MEDIUM findings")
    else:
        print(f"[writing] {base}: {n_hit} finding(s) to review "
              f"({len(high)} high, {len(medium)} medium):")
        for f in high:
            print(f"  L{f['line']} [HIGH {f['category']}] {f['label']}: {f['snippet']}")
        for f in medium:
            print(f"  L{f['line']} [MED  {f['category']}] {f['label']}: {f['snippet']}")
    # LOW advisories: summarise by category, expand only with --verbose.
    if low:
        by_cat = {}
        for f in low:
            by_cat.setdefault(f["category"], []).append((f["line"], f["label"], f["snippet"]))
        parts = ", ".join(f"{c} x{len(v)}" for c, v in sorted(by_cat.items()))
        print(f"[writing] {base}: advisories (LOW, report only): {parts}")
        if verbose:
            for cat, items in sorted(by_cat.items()):
                for line_no, label, snippet in items:
                    print(f"  L{line_no} [LOW {cat}] {label}: {snippet}")
    if doc.get("passive_rate", 0) >= 4:
        print(f"[writing] {base}: passive-heavy ({doc['passive_rate']}/100w); name the actor.")
    if doc.get("adverb_rate", 0) >= 5:
        print(f"[writing] {base}: adverb-heavy ({doc['adverb_rate']}/100w); prefer strong verbs.")
    return n_hit


def report_passes(path, high, medium, low, doc):
    """Editing-passes view (Ptacek): every category as a named pass with a count."""
    base = os.path.basename(path)
    by_cat = {}
    for tier, items in (("HIGH", high), ("MED", medium), ("LOW", low)):
        for f in items:
            key = (f["category"], tier if tier != "LOW" else "advisory")
            by_cat[key] = by_cat.get(key, 0) + 1
    print(f"[passes] {base}:")
    if not by_cat:
        print("  (all passes clear)")
    for (cat, tier), n in sorted(by_cat.items(), key=lambda kv: (-kv[1], kv[0][0])):
        print(f"  {n:>4}  {cat} [{tier}]")


def _check_file(path):
    from . import profiles
    with open(path, "rb") as fh:
        data = fh.read()
    reason = binary_reason(data, name=path)
    if reason:
        return None, reason
    text = data.decode("utf-8", errors="replace")
    return check_text(text, profile=profiles.resolve(path=path, text=text)), None


def main(argv):
    verbose = "--verbose" in argv or "-v" in argv
    as_json = "--json" in argv
    as_passes = "--passes" in argv
    files = [a for a in argv if not a.startswith("-") and os.path.isfile(a)]
    total, payload = 0, []
    for path in files:
        try:
            r, reason = _check_file(path)
        except OSError:
            r, reason = None, "cannot read"
        if reason:
            print(f"[writing] {os.path.basename(path)}: cannot screen ({reason})")
            continue
        total += len(r["high"]) + len(r["medium"])
        if as_json:
            payload.append(dict(r, file=path))
        elif as_passes:
            report_passes(path, r["high"], r["medium"], r["low"], r["cadence"])
        else:
            report_text(path, r["high"], r["medium"], r["low"], r["cadence"], verbose)
    if as_json:
        print(json.dumps({"files": payload, "total_hits": total}, ensure_ascii=False, indent=2))
    elif files:
        print(f"[writing] {DOES_NOT_PROVE}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
