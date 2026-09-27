"""The linear-time masks must return exactly what their reference returns.
The URL and tag masks replace re.sub with a reference pattern. The quotation and
inline-code masks follow rules a regex cannot state (SCAN_ALGO 7), so their
reference is a direct implementation of those rules, written differently (one
pass per family, character by character, a blank map for the union). Findings
are computed on the masked line, so any difference here would change a finding
and break receipt replay under an unchanged ruleset fingerprint. The references
are only safe to run on short input, so the comparison uses short generated
strings, and a separate test holds the masks, and the detector functions that
apply them, to a time budget on long hostile lines."""
import random
import re
import time

import pytest

from articulate import detector, masking, quotemarks


def _blank(m):
    return " " * (m.end() - m.start())


URL = re.compile(masking.URL_PATTERN)
TAG = re.compile(masking.TAG_PATTERN)
QUOTED = re.compile(masking.QUOTED_PATTERN)
Q = quotemarks
NL = chr(10)


def _can_open(text, i, mark):
    if mark == Q.LSQ:
        after = text[i + 1] if i + 1 < len(text) else " "
        if after.isdigit() or (i > 0 and text[i - 1].isalpha()):
            return False
    if mark not in Q.POSITIONAL:
        return True
    before = text[i - 1] if i > 0 else " "
    after = text[i + 1] if i + 1 < len(text) else " "
    return (before.isspace() or before in Q.OPEN_AFTER) and not after.isspace()


def _can_close(text, i, mark):
    if mark == Q.DQ:
        return not text[i - 1].isspace()
    if mark == Q.RSQ:
        return not (0 < i < len(text) - 1 and text[i - 1].isalpha()
                    and text[i + 1].isalpha())
    return True


def _reference_quoted(text):
    """The quotation rules, one family at a time: an opener waits for one of its
    closers, a later opener of the family replaces it, a line break drops it."""
    blank = [False] * len(text)
    for fam in Q.FAMILIES.values():
        opened = None      # (index, closers)
        for i, ch in enumerate(text):
            if ch == NL:
                opened = None
                continue
            if opened is not None and ch in opened[1] and _can_close(text, i, ch):
                for k in range(opened[0], i + 1):
                    blank[k] = True
                opened = None
            elif ch in fam and _can_open(text, i, ch):
                opened = (i, fam[ch])
    return "".join(" " if b else c for c, b in zip(text, blank))


def _reference_code(text):
    """Backtick pairs on one line, a backtick between two letters left alone."""
    out, opened = list(text), None
    for i, ch in enumerate(text):
        if ch == NL:
            opened = None
        elif ch == "`":
            if 0 < i < len(text) - 1 and text[i - 1].isalpha() and text[i + 1].isalpha():
                continue
            if opened is None:
                opened = i
            else:
                out[opened:i + 1] = " " * (i + 1 - opened)
                opened = None
    return "".join(out)

# Pieces chosen to reach every branch of the three scanners. The list holds web
# prefixes and e-mail parts, runs of dots or hyphens, an "@" with no domain, tags,
# each quote kind with its closer, newlines, plus one non-ASCII word character.
ATOMS = list("a1._-@hsp:/ <>\n\"\u201c\u201d\u2018\u2019\u00e9\t+x") + [
    "http://", "https://", "http", "https:/", "a@b.com", "x.y@z.org", "<b>",
    "</i>", "@x.", ".-", "@@", "www.", "e.g.", "\u00e9@\u00e9.\u00e9", "__",
    "a.b", "--", "\r"] + [chr(c) for c in (
        0x201E, 0x201A, 0xAB, 0xBB, 0x2039, 0x203A, 0x300C, 0x300D, 0x300E, 0x300F,
        0x60, 0x2014, 0x28, 0x3A)] + ["9", "a`b", "6" + chr(34), " " + chr(34) + "a"]

CASES = [
    "mail jo.smith@example.com or visit https://example.com/a?b=c today",
    "a@b.c.-d@e.fg",            # the second match starts inside the first's run
    "-.foo@x.com",              # the local part starts at the first word boundary
    "x.https://y and a@x.http://z",
    "user+tag@example.com",     # "+" is outside the local-part class
    "if a < b then <em>c</em> > d",
    "<>< a >",
    "\u201cHe said \u2018no\u2019 and left.\u201d \u201cunclosed",
    "\"one\" \"two\" \"three",
]


def _check(text):
    assert masking.mask_urls(text) == URL.sub(_blank, text), repr(text)
    spans = masking.url_spans(text)
    assert masking.blank_spans(text, spans) == URL.sub(_blank, text), repr(text)
    assert masking.mask_tags(text) == TAG.sub(_blank, text), repr(text)
    assert masking.mask_quoted(text) == _reference_quoted(text), repr(text)
    assert masking.mask_code(text) == _reference_code(text), repr(text)


def test_masks_match_reference_on_known_cases():
    for text in CASES:
        _check(text)


def test_masks_match_reference_on_generated_input():
    rng = random.Random(20260923)
    for _ in range(4000):
        _check("".join(rng.choice(ATOMS) for _ in range(rng.randint(0, 60))))


DQ = chr(34)
SPEC = [
    # (text, the quoted parts that must be blanked)
    ("He is 6" + DQ + " tall, so she called it " + DQ + "fine" + DQ + " and left.",
     [DQ + "fine" + DQ]),
    ("the " + DQ + "top 10" + DQ + " list", [DQ + "top 10" + DQ]),
    ("stop " + DQ + "go and then " + DQ + "run" + DQ + " away", [DQ + "run" + DQ]),
    ("it" + Q.RSQ + "s " + Q.LSQ + "90s and " + Q.LSQ + "fine" + Q.RSQ + " now",
     [Q.LSQ + "fine" + Q.RSQ]),
    ("wrote: " + Q.LOW_DQ + "Wort" + Q.LDQ + " und", [Q.LOW_DQ + "Wort" + Q.LDQ]),
    ("wrote: " + Q.RDQ + "ord" + Q.RDQ + " och", [Q.RDQ + "ord" + Q.RDQ]),
    ("dit " + Q.LGUIL + " mot " + Q.RGUIL + " et", [Q.LGUIL + " mot " + Q.RGUIL]),
    ("sagt " + Q.RGUIL + "Wort" + Q.LGUIL + " und", [Q.RGUIL + "Wort" + Q.LGUIL]),
    ("a " + Q.LCORNER + "yes" + Q.RCORNER + " b", [Q.LCORNER + "yes" + Q.RCORNER]),
    (Q.LDQ + "He said " + Q.LSQ + "no" + Q.RSQ + " and left." + Q.RDQ,
     [Q.LDQ + "He said " + Q.LSQ + "no" + Q.RSQ + " and left." + Q.RDQ]),
    ("open " + DQ + "never closed", []),
    ("line one " + DQ + "a" + NL + "b" + DQ + " two", []),
]


@pytest.mark.parametrize("text,quoted", SPEC)
def test_each_quotation_rule(text, quoted):
    masked = masking.mask_quoted(text)
    gone = [text[s:e] for s, e in masking.quote_spans(text)]
    assert gone == quoted
    assert len(masked) == len(text)
    assert masked == _reference_quoted(text)


@pytest.mark.parametrize("text,code", [
    ("I didn`t know, and it wasn`t clear.", []),
    ("run `make` then `test` now", ["`make`", "`test`"]),
    ("a lone ` tick and didn`t", []),
])
def test_each_code_span_rule(text, code):
    assert [text[s:e] for s, e in masking.code_spans(text)] == code


def test_detector_keeps_the_reference_patterns():
    assert detector.URL.pattern == masking.URL_PATTERN
    assert detector.TAG.pattern == masking.TAG_PATTERN
    assert detector.QUOTED.pattern == masking.QUOTED_PATTERN


HOSTILE = [
    "v1." * 10000,
    "1.1.1.1." * 5000,
    ("1.1.1.1." * 5000) + "@",
    "twenty-" * 8000,
    "a@" * 20000,
    # The quadratic tag pattern takes about 0.09 s per call on 10000 unclosed
    # "<", under any budget that is safe on a slow runner. On 40000 it took
    # 1.4 s to 4.4 s, so these lines use 40000. The quote pattern took about
    # 0.4 s on 10000 unclosed curly quotes and 1.7 s on 20000.
    "<a " * 40000,
    ("<a " * 40000) + ">",
    "\u201ca " * 20000,
    "\u2018a " * 20000,
    "\"a\" " * 10000,
    "https://" * 5000,
    (Q.LGUIL + "a ") * 20000,
    (Q.RGUIL + "a ") * 20000,
    ("`a ") * 20000,
    ("a`b ") * 20000,
    (" " + DQ + "a") * 20000,
]

# The masks, plus the detector functions that apply them. Timing the detector
# functions as well catches a call site that goes back to URL.sub, TAG.sub, or
# QUOTED.sub, in addition to a regression inside the masking module.
MASKERS = [masking.mask_urls, masking.mask_tags, masking.mask_quoted, masking.mask_code,
           detector.strip_markup, detector.mask_quotes]


def test_masks_are_linear_on_hostile_lines():
    # The linear code takes at most about 0.01 s per call on these lines. On
    # each of the seven lines where a reference pattern is quadratic, that
    # pattern took 1.3 s or more per call, so the 0.25 s budget separates them.
    for i, text in enumerate(HOSTILE):
        for fn in MASKERS:
            start = time.perf_counter()
            fn(text)
            elapsed = time.perf_counter() - start
            assert elapsed < 0.25, f"{fn.__name__} on hostile line {i} took {elapsed:.2f}s"
