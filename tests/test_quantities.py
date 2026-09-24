"""Meaning-guard regressions for quantities: magnitudes and units spelled as
words, and clock times.

Each unfaithful pair must read `changed` and each faithful pair `preserved`. The
key tests pin the normalization that makes the faithful pairs equal.
"""
import pytest

from articulate import meaning, quantities


def _keys(text):
    return [k for _s, _e, k in quantities.find(text)]


def _verdict(original, rewrite):
    return meaning.compare(original, rewrite)["verdict"]


def _report(original, rewrite):
    return meaning.format_report(meaning.compare(original, rewrite))


# "one million" and "a million" gave no quantity, since "one" is skipped and a
# magnitude word needed a numeral before it. Plural magnitudes were not read.
MAGNITUDE_CHANGED = [
    ("The fund holds one million dollars.", "The fund holds one billion dollars."),
    ("The table holds a million rows.", "The table holds a billion rows."),
    ("Keep one hundred rows.", "Keep one thousand rows."),
    ("Thousands of users signed up.", "Millions of users signed up."),
]
MAGNITUDE_PRESERVED = [
    ("It costs $5M.", "It costs $5 million."),
    ("It costs $5bn.", "It costs $5 billion."),
    ("Keep one hundred rows.", "Keep 100 rows."),
    ("The table holds a million rows.", "The table holds 1,000,000 rows."),
    ("Order two dozen boxes.", "Order 24 boxes."),
]
# Units spelled as words, and the symbols us, ns, PB, and EB, keyed as the bare
# number, so a swap passed and a symbol-to-word rewrite was refused.
UNIT_CHANGED = [
    ("The limit is 10 megabytes.", "The limit is 10 gigabytes."),
    ("The route is 5 kilometers long.", "The route is 5 miles long."),
    ("Latency stays under 40 microseconds.", "Latency stays under 40 nanoseconds."),
    ("Latency is 40 us.", "Latency is 40 ns."),
    ("The fee is 20 dollars.", "The fee is 20 euros."),
    ("The archive holds 2 PB.", "The archive holds 2 EB."),
    ("The box weighs 5 kilograms.", "The box weighs 5 pounds."),
]
UNIT_PRESERVED = [
    ("The limit is 10 MB.", "The limit is 10 megabytes."),
    ("The route is 5 km long.", "The route is 5 kilometers long."),
    ("The route is 5 kilometres long.", "The route is 5 kilometers long."),
    ("Latency is 40 us.", "Latency is 40 microseconds."),
    ("Latency is 40\u00b5s.", "Latency is 40 us."),
    ("The fee is $20.", "The fee is 20 dollars."),
    ("The fee is 20 EUR.", "The fee is 20 euros."),
    ("The clock runs at 3 GHz.", "The clock runs at 3 gigahertz."),
]


@pytest.mark.parametrize("original,rewrite", MAGNITUDE_CHANGED + UNIT_CHANGED)
def test_changed_magnitude_or_unit_is_caught(original, rewrite):
    assert _verdict(original, rewrite) == "changed", _report(original, rewrite)


@pytest.mark.parametrize("original,rewrite", MAGNITUDE_PRESERVED + UNIT_PRESERVED)
def test_same_magnitude_or_unit_is_preserved(original, rewrite):
    assert _verdict(original, rewrite) == "preserved", _report(original, rewrite)


@pytest.mark.parametrize("text,keys", [
    ("one million", ["1000000"]), ("a billion", ["1000000000"]),
    ("an hundred", ["100"]), ("a dozen", ["12"]),
    ("Thousands, then millions", ["approx:thousands", "approx:millions"]),
    ("$5M and $5bn and $2B", ["$5000000", "$5000000000", "$2000000000"]),
    # A magnitude letter needs a currency sign: bare 5B is five bytes.
    ("5B", ["5B"]),
    ("20 dollars, 20 euros, 20 EUR, 20 USD", ["$20", "\u20ac20", "\u20ac20", "20USD"]),
    ("3 megabits, 3 Mb", ["3Mb", "3Mb"]),
])
def test_word_magnitudes_and_units_normalize(text, keys):
    assert _keys(text) == keys


def test_one_alone_and_a_alone_stay_words():
    assert _keys("one of a kind, a few, and an hour") == []
