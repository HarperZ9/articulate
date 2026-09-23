"""The linear-time masks must return exactly what re.sub returns with the
reference patterns they replace. Findings are computed on the masked line, so
any difference here would change a finding and break receipt replay under an
unchanged ruleset fingerprint. The reference patterns are only safe to run on
short input, so the comparison uses short generated strings, and a separate
test holds the masks to a time budget on long hostile lines."""
import random
import re
import time

from articulate import detector, masking


def _blank(m):
    return " " * (m.end() - m.start())


URL = re.compile(masking.URL_PATTERN)
TAG = re.compile(masking.TAG_PATTERN)
QUOTED = re.compile(masking.QUOTED_PATTERN)

# Pieces chosen to reach every branch of the three scanners. The list holds web
# prefixes and e-mail parts, runs of dots or hyphens, an "@" with no domain, tags,
# each quote kind with its closer, newlines, plus one non-ASCII word character.
ATOMS = list("a1._-@hsp:/ <>\n\"\u201c\u201d\u2018\u2019\u00e9\t+x") + [
    "http://", "https://", "http", "https:/", "a@b.com", "x.y@z.org", "<b>",
    "</i>", "@x.", ".-", "@@", "www.", "e.g.", "\u00e9@\u00e9.\u00e9", "__",
    "a.b", "--", "\r"]

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
    assert masking.mask_quoted(text) == QUOTED.sub(_blank, text), repr(text)


def test_masks_match_reference_on_known_cases():
    for text in CASES:
        _check(text)


def test_masks_match_reference_on_generated_input():
    rng = random.Random(20260923)
    for _ in range(4000):
        _check("".join(rng.choice(ATOMS) for _ in range(rng.randint(0, 60))))


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
    "<a " * 10000,
    ("<a " * 10000) + ">",
    "\u201ca " * 10000,
    "\u2018a " * 10000,
    "\"a\" " * 10000,
    "https://" * 5000,
]


def test_masks_are_linear_on_hostile_lines():
    for i, text in enumerate(HOSTILE):
        start = time.perf_counter()
        masking.mask_urls(text)
        masking.mask_tags(text)
        masking.mask_quoted(text)
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0, f"hostile line {i} took {elapsed:.2f}s"
