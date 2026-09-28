"""Unit.locate maps an index in a logical line back to its file offset and line.

The scanner calls it for every raw match, before a match is kept or dropped, so
its cost multiplies by the number of matches. A scan from the last piece made a
long unit quadratic: one paragraph of 20,000 short lines, each holding an
unmatched opening quote, took 14 s to check and reported nothing. These tests
hold locate to the linear scan's answers at every index and bound its time on a
unit of 50,000 lines, where the linear scan would take minutes.
"""
import time

import articulate
from articulate.logical import Unit


def _linear(unit, i):
    """The answer the first implementation gave, scanning from the last piece."""
    for log_start, doc_start, line_no, length in reversed(unit.pieces):
        if i >= log_start:
            return doc_start + min(i - log_start, length), line_no
    return unit.pieces[0][1], unit.pieces[0][2]


def _unit(lines):
    unit, offset = Unit("prose", None), 0
    for number, content in enumerate(lines, 1):
        unit.add(number, offset, content)
        offset += len(content) + 1
    return unit


def test_locate_gives_the_linear_answer_at_every_index():
    # A hyphen at a line end joins with no space; the other breaks become one space.
    unit = _unit(["The state-of-the-", "art tools work", "", "x", "well-", "known"])
    assert unit.text.startswith("The state-of-the-art tools work")
    for i in range(-2, len(unit.text) + 3):
        assert unit.locate(i) == _linear(unit, i), i


def test_span_is_unchanged_across_a_line_break():
    unit = _unit(["alpha beta", "gamma"])
    start = unit.text.index("beta")
    assert unit.span(start, start + len("beta gamma")) == (6, 16, 1, 2)


def test_locate_stays_fast_on_a_unit_of_many_lines():
    unit = _unit(["x “y"] * 50_000)
    began = time.perf_counter()
    for i in range(0, len(unit.text), 3):
        unit.locate(i)
    assert time.perf_counter() - began < 2.0


def test_building_a_unit_of_many_lines_stays_fast():
    """Growing the text by += copied it on every line, which is quadratic too."""
    began = time.perf_counter()
    unit = _unit(["x “y"] * 100_000)
    elapsed = time.perf_counter() - began
    assert len(unit.text) == 100_000 * 5 - 1
    assert elapsed < 1.0, elapsed


def test_a_long_unit_of_open_quotes_checks_in_linear_time():
    """The review's input: one unit of short lines with an unmatched opening quote."""
    text = "x “y\n" * 20_000
    began = time.perf_counter()
    result = articulate.check_text(text)
    elapsed = time.perf_counter() - began
    assert result["gate"] == "ok"
    assert elapsed < 8.0, elapsed
