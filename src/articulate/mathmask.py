#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.mathmask -- LaTeX math that no rewrite may touch.

Every math span is replaced by a numbered placeholder before a model call and
spliced back byte for byte after it. A rewrite that lost, doubled or invented a
placeholder is refused. Standard library only.
"""
import os
import re
from collections import Counter

# Math spans a rewrite must never touch: a changed symbol, quantifier order, or
# inequality direction changes a theorem. One pass, one alternation: at each
# position the environment form is tried first, then display, then inline. An
# environment that holds inline or display math is masked whole, so no span ever
# contains another span's placeholder and every span restores byte for byte.
_MATH_RX = re.compile(
    r"\\begin\{(?P<env>equation|align|gather|multline|eqnarray|split|theorem"
    r"|lemma|proof|definition|proposition|corollary|claim)\*?\}"
    r".*?\\end\{(?P=env)\*?\}"
    r"|\$\$.*?\$\$"
    r"|\\\[.*?\\\]"
    r"|\\\(.*?\\\)"
    r"|\$(?:\\.|[^$\\])*\$",
    re.S)
_MATH_PLACEHOLDER = "\u2983MATH{}\u2984"   # a distinctive bracket unlikely to be edited
_MATH_PLACEHOLDER_RX = re.compile("\u2983MATH(\\d+)\u2984")

# File types whose math every rewrite path masks before a model call.
MATH_EXTS = (".tex",)


class MathSpliceError(RuntimeError):
    """A rewrite dropped, duplicated, or invented a masked math placeholder, so the
    formulas cannot be restored byte for byte. The rewrite is refused."""


def is_math_file(path):
    """True when the file's type carries LaTeX math that a rewrite must mask."""
    return os.path.splitext(path)[1].lower() in MATH_EXTS


def mask_math(text):
    """Replace every LaTeX math span with a numbered placeholder and return
    (masked_text, spans). The model never sees the math, so it cannot alter a
    formula. This is a structural guarantee that holds whatever the model returns."""
    spans = []

    def repl(m):
        spans.append(m.group(0))
        return _MATH_PLACEHOLDER.format(len(spans) - 1)

    return _MATH_RX.sub(repl, text), spans


def splice_math(text, spans):
    """Restore masked math spans by placeholder, byte for byte. Each placeholder
    must appear exactly once. A rewrite that dropped one would delete a formula,
    and one that repeated or invented one would duplicate or corrupt it. Either
    case raises MathSpliceError, and the caller keeps the text it had."""
    found = Counter(_MATH_PLACEHOLDER_RX.findall(text))
    expected = Counter(str(i) for i in range(len(spans)))
    if found != expected:
        lost = sorted(int(k) for k in expected - found)
        extra = sorted(int(k) for k in found - expected)
        raise MathSpliceError(
            f"rewrite altered masked math (lost spans {lost}, extra placeholders "
            f"{extra}); the rewrite is refused and the math left as it was")
    for i, original in enumerate(spans):
        text = text.replace(_MATH_PLACEHOLDER.format(i), original)
    return text


def scrub_math_notes(notes):
    """Editor notes with every formula and every math placeholder replaced by
    '[math]'. A quality judge quotes the text it read, so its notes would carry a
    formula (or a placeholder) into the next rewrite prompt."""
    return [_MATH_PLACEHOLDER_RX.sub("[math]", mask_math(str(n))[0]) for n in notes]
