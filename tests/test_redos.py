"""Regex-safety edge cases: the detector runs over arbitrary, possibly adversarial
documents, so no pattern may blow up on a crafted input. A catastrophic-backtracking
regression would hang a CI gate, which is an availability incident."""
import time

import articulate
from articulate import profiles

ADVERSARIAL = [
    "a" * 40000,
    "not " * 8000,
    "You can " * 4000,
    ("is not " * 4000) + "it is",
    ("word, " * 8000) + "and word",
    (" " * 40000) + "x",
    "a b " * 12000,
    "".join("<b>x</b>" for _ in range(5000)),
    "```\n" + ("x" * 40000) + "\n```",
    ("cutting-edge " * 6000),
]


# The genre layer adds quote-masking, the fiction lexicon, and the Fountain
# classifier. Each runs over arbitrary input too, so they get the same budget.
GENRE_ADVERSARIAL = [
    '"' + ("x" * 40000),                       # an unterminated quote
    ("could not " * 5000) + "help but stop",   # the catenative near the lookbehind
    ("INT. " * 8000) + "ROOM",                 # slugline prefix repeated
    ("shivers ran down her spine " * 2000),    # the fiction lexicon, at length
    ("a mix of joy and " * 4000) + "fear washed over her",
]


def test_no_catastrophic_backtracking():
    prof = profiles.load("flavored")
    for i, text in enumerate(ADVERSARIAL):
        start = time.perf_counter()
        articulate.check_text(text, profile=prof)
        elapsed = time.perf_counter() - start
        assert elapsed < 3.0, f"adversarial input {i} took {elapsed:.2f}s (possible ReDoS)"


def test_genre_patterns_are_bounded():
    for name in ("literary-fiction", "screenplay", "poetry", "memoir"):
        prof = profiles.load(name)
        for i, text in enumerate(ADVERSARIAL + GENRE_ADVERSARIAL):
            start = time.perf_counter()
            articulate.check_text(text, profile=prof)
            elapsed = time.perf_counter() - start
            assert elapsed < 3.0, f"{name} input {i} took {elapsed:.2f}s (possible ReDoS)"


# detect_injection runs over the full untrusted document on every editor call, so
# its patterns get the same wall-clock budget as the check_text passes.
INJECTION_ADVERSARIAL = [
    ("ignore " * 8000) + "instructions",
    ("you are now " * 5000) + "a",
    ("reveal " * 8000) + "the system prompt",
    ("System: " * 4000),
    ("no restrictions " * 5000),
    ("respond " * 8000) + "approved",
]


def test_detect_injection_is_bounded():
    from articulate import detector
    for i, text in enumerate(INJECTION_ADVERSARIAL + ADVERSARIAL):
        start = time.perf_counter()
        detector.detect_injection(text)
        elapsed = time.perf_counter() - start
        assert elapsed < 3.0, f"detect_injection input {i} took {elapsed:.2f}s (possible ReDoS)"


def test_empty_and_whitespace_are_clean():
    prof = profiles.load("flavored")
    for text in ("", "\n\n\n", "   ", "\t\t"):
        r = articulate.check_text(text, profile=prof)
        assert r["clean"] is True and r["gate"] == "ok"
