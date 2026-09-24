"""The span finders: no length cap, the same spans as the uncapped reference
regexes, and a long span protected in full.

The references below are the lazy regexes the finders replace, with the caps
removed. They backtrack on long hostile input, so the comparison runs on short
generated strings; tests/test_redos.py holds the finders to a time budget on
long input.
"""
import random
import re

import pytest

from articulate import finders, guard, invariants, protect

ENVS = "|".join(invariants.MATH_ENVS)
REFERENCE = [
    re.compile(r"\$\$.+?\$\$", re.S),
    re.compile(r"\\\[.+?\\\]", re.S),
    re.compile(r"\\\(.+?\\\)", re.S),
    re.compile(r"\\begin\{((?:" + ENVS + r")\*?)\}.*?\\end\{\1\}", re.S),
]
QUOTE = re.compile("\"[^\"\\n]+\"|\u201c[^\u201d\\n]+\u201d")

ATOMS = list("a $\\[]()\n\"\u201c\u201d{}*") + [
    "$$", "\\[", "\\]", "\\(", "\\)", "\\begin{align}", "\\end{align}",
    "\\begin{align*}", "\\end{align*}", "\\begin{proof}", "\\end{proof}",
    "\\begin{itemize}", "\\end{itemize}", "\"\"", "\u201c\u201d"]


def _spans(rx, text):
    return [(m.start(), m.end(), None) for m in rx.finditer(text)]


def _check(text):
    for find, rx in zip(invariants.MATH, REFERENCE):
        assert find(text) == _spans(rx, text), (rx.pattern, text)
    assert finders.quote_spans(text) == _spans(QUOTE, text), text


def test_finders_match_the_uncapped_regexes_on_known_cases():
    for text in ('"" x"', '"a" "b', "$$$$$", "$$a$$ $$b", "\\begin{align}x\\end{align*}",
                 "\u201ca \u201cb\u201d", "\\(a\\) \\(", "\\begin{proof}\\end{proof}"):
        _check(text)


def test_finders_match_the_uncapped_regexes_on_generated_input():
    rng = random.Random(20260923)
    for _ in range(4000):
        _check("".join(rng.choice(ATOMS) for _ in range(rng.randint(0, 40))))


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
