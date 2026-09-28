"""The span finders: no length cap, the same spans as their references, and a
long span protected in full.

The math references are the lazy regexes the finders replace, with the caps
removed. The quote and inline-code finders pair marks as the phrasing rules do
(ruleset 0.9.0), which a regex cannot state, so their references are direct
implementations of those rules. The references backtrack or loop on long
hostile input, so the comparison runs on short generated strings;
tests/test_redos.py holds the finders to a time budget on long input.
"""
import random
import re

import pytest

from articulate import finders, guard, invariants, protect, quotemarks

ENVS = "|".join(invariants.MATH_ENVS)
REFERENCE = [
    re.compile(r"\$\$.+?\$\$", re.S),
    re.compile(r"\\\[.+?\\\]", re.S),
    re.compile(r"\\\(.+?\\\)", re.S),
    re.compile(r"\\begin\{((?:" + ENVS + r")\*?)\}.*?\\end\{\1\}", re.S),
]
# The quote finder pairs marks as the phrasing rules do (articulate.quotemarks),
# so its reference is a direct implementation of those rules, written apart
# from the finder: one pass per family, character by character. A regex cannot
# state them. An empty pair ("") is consumed and dropped: it is no span and does
# not lend its closing mark to the next quote.
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


def _reference_quotes(text):
    """(start, end, None) of each non-empty quotation: every family paired on
    its own, a later opener replacing an open one, a line break dropping it;
    overlapping pairs merged."""
    pairs = []
    for fam in Q.FAMILIES.values():
        opened = None
        for i, ch in enumerate(text):
            if ch == NL:
                opened = None
            elif opened is not None and ch in opened[1] and _can_close(text, i, ch):
                pairs.append((opened[0], i + 1))
                opened = None
            elif ch in fam and _can_open(text, i, ch):
                opened = (i, fam[ch])
    merged = []
    for s, e in sorted(pairs):
        if merged and s < merged[-1][1]:
            merged[-1] = (merged[-1][0], max(e, merged[-1][1]))
        else:
            merged.append((s, e))
    return [(s, e, None) for s, e in merged if e - s > 2]

ATOMS = list("a $\\[]()\n\"\u201c\u201d{}*") + [
    "$$", "\\[", "\\]", "\\(", "\\)", "\\begin{align}", "\\end{align}",
    "\\begin{align*}", "\\end{align*}", "\\begin{proof}", "\\end{proof}",
    "\\begin{itemize}", "\\end{itemize}", "\"\"", "\u201c\u201d"]


def _spans(rx, text):
    return [(m.start(), m.end(), None) for m in rx.finditer(text)]


def _check(text):
    for find, rx in zip(invariants.MATH, REFERENCE):
        assert find(text) == _spans(rx, text), (rx.pattern, text)
    assert finders.quote_spans(text) == _reference_quotes(text), text


def test_finders_match_the_uncapped_regexes_on_known_cases():
    for text in ('"" x"', '"a" "b', "$$$$$", "$$a$$ $$b", "\\begin{align}x\\end{align*}",
                 "\u201ca \u201cb\u201d", "\\(a\\) \\(", "\\begin{proof}\\end{proof}"):
        _check(text)


def test_finders_match_the_uncapped_regexes_on_generated_input():
    rng = random.Random(20260923)
    for _ in range(4000):
        _check("".join(rng.choice(ATOMS) for _ in range(rng.randint(0, 40))))


# Every quotation mark the rules pair, the characters that decide a mark's
# direction, and code delimiters, so each branch of both rules is reached.
MARK_ATOMS = sorted(quotemarks.MARKS) + list("a9 ,(\n`") + ["6\"", " \"a", "a`b", "``"]


def _reference_code(text):
    """Inline code: a backtick between two letters is an apostrophe; then a
    double pair (which may hold a single backtick) or a single pair on one line,
    leftmost first, as the regex takes them."""
    seen = "".join("'" if ch == "`" and 0 < i < len(text) - 1 and text[i - 1].isalpha()
                   and text[i + 1].isalpha() else ch for i, ch in enumerate(text))
    out, i = [], 0
    while i < len(seen):
        if seen.startswith("``", i):
            j = seen.find("``", i + 3)
            nl = seen.find(NL, i)
            if j > 0 and (nl < 0 or nl > j):
                out.append((i, j + 2, None))
                i = j + 2
                continue
        if seen[i] == "`":
            j = i + 1
            while j < len(seen) and seen[j] not in "`" + NL:
                j += 1
            if j < len(seen) and seen[j] == "`" and j > i + 1:
                out.append((i, j + 1, None))
                i = j + 1
                continue
        i += 1
    return out


def test_quote_and_code_finders_match_their_references_on_generated_marks():
    rng = random.Random(20260927)
    for _ in range(4000):
        text = "".join(rng.choice(MARK_ATOMS) for _ in range(rng.randint(0, 30)))
        assert finders.quote_spans(text) == _reference_quotes(text), repr(text)
        assert finders.code_spans(text) == _reference_code(text), repr(text)


RULING = " ".join(["the board approved the plan after long review of every filing"] * 10)
LONG = [
    ('It reads "' + RULING + '" and ends.\n', '"' + RULING + '"'),
    ("It reads \u201c" + RULING + "\u201d and ends.\n", "\u201c" + RULING + "\u201d"),
    ("Fetch https://example.com/f?sig=" + "a1" * 1100 + " now.\n",
     "https://example.com/f?sig=" + "a1" * 1100),
    ("Run `" + "x " * 400 + "` first.\n", "`" + "x " * 400 + "`"),
    ("$$\n" + "a + " * 1500 + "b\n$$\nDone.\n", "$$\n" + "a + " * 1500 + "b\n$$"),
    ("\\begin{align}\n" + "f &= g \\\\\n" * 900 + "\\end{align}\n",
     "\\begin{align}\n" + "f &= g \\\\\n" * 900 + "\\end{align}"),
]


@pytest.mark.parametrize("text,span", LONG)
def test_a_long_span_is_protected_in_full(text, span):
    masked, spans = protect.mask(text)
    assert [s["text"] for s in spans] == [span]
    assert protect.restore(masked, masked, spans) == text


def test_an_edit_inside_a_long_quote_is_refused():
    text = LONG[0][0]
    edited = text.replace("approved", "rejected", 1)
    assert guard.RewriteGuard().run(lambda m: m.replace("approved", "rejected", 1),
                                    text) == text
    with pytest.raises(guard.RewriteRefused):
        guard.RewriteGuard().check(text, edited)
