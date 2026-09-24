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
    # A long run of word characters mixed with dots or hyphens, with no "@". The
    # e-mail alternative of the URL mask used to retry every word boundary in the
    # run and rescan the rest of it each time: 14 s to 68 s per check_text call.
    "v1." * 10000,
    "1.1.1.1." * 5000,
    "twenty-" * 8000,
    # The same run with an "@" at the end and no domain after it. A fix that
    # only skips lines without "@" would still take about 40 s here.
    ("1.1.1.1." * 5000) + "@",
    # Unclosed "<": the tag mask rescanned to the end of the line from each one.
    # On 10000 of them the old code stayed under the 3 s budget, so a regression
    # would pass. On 40000 it took 13 s to 26 s per check_text call, and the
    # fixed code takes about 0.35 s.
    "<a " * 40000,
]


# The genre layer adds quote-masking, the fiction lexicon, and the Fountain
# classifier. Each runs over arbitrary input too, so they get the same budget.
GENRE_ADVERSARIAL = [
    '"' + ("x" * 40000),                       # an unterminated quote
    ("could not " * 5000) + "help but stop",   # the catenative near the lookbehind
    ("INT. " * 8000) + "ROOM",                 # slugline prefix repeated
    ("shivers ran down her spine " * 2000),    # the fiction lexicon, at length
    ("a mix of joy and " * 4000) + "fear washed over her",
    # Unclosed curly quotes: the dialogue mask rescanned to the end of the line
    # from each opening mark. On 10000 of them the old code took 3.3 s to 5.0 s
    # per check_text call, too close to the budget to fail reliably. On 20000 it
    # took 14 s to 21 s, and the fixed code takes under 0.5 s.
    "\u201ca " * 20000,
    "\u2018a " * 20000,
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


# The meaning guard extracts invariants from both sides of every rewrite, so its
# patterns and its per-token sentence-start check get the same budget. The entity
# cases are long single lines, where a per-token scan back to the line start was
# once quadratic.
MEANING_ADVERSARIAL = [
    "1" * 40000, "1," * 20000, "(" * 40000, "(Smith " * 8000, "[@" * 20000,
    "$" * 40000, "$a^" * 10000, "`" * 40000, "\\begin{proof}" * 5000,
    "http://" * 8000, "a@b." * 10000, "May " * 10000, "10 ms " * 8000,
    "Smith et al" * 5000, "doi:10.1234/" * 5000, "A " * 20000, "```\n" * 10000,
    "v1." * 10000, "1.1.1.1." * 5000, "twenty-" * 8000,
    # The URL finder trims unbalanced closers and trailing citations one at a
    # time; each trim step must stay constant time.
    "http://x" + ")" * 40000, "http://x" + "[1]" * 13000, "http://x(" * 5000 + "]" * 20000,
    # Quotes, inline code, URLs, and display math carry no length cap, so an
    # unclosed opener must not rescan to the end from each one.
    '"' + "x" * 40000, '"a' * 20000, "http://x/" + "a" * 200000, "\u201ca " * 20000,
    "``" + "a`" * 20000, "$$a" * 10000, "\\[" * 20000, "\\(a" * 20000,
    "\\begin{align}" * 5000, "\\begin{align}" + "\\begin{proof}x" * 5000,
    # A bound word counts only before a number, so each match looks ahead once.
    "up to " * 8000 + "5", "more than 5 " * 5000, "under  " * 8000,
]


# The protected-span layer masks, restores its own output as a self-check, and
# restores the model's output: three passes over every placeholder. A document
# with thousands of citations or code spans makes thousands of placeholders.
SPAN_ADVERSARIAL = ["[1] " * 20000, "`x` " * 20000, "a@b.co " * 10000,
                    "\u2983a" * 20000, "\u2983" * 40000, "\u2983CODE_0_1a2b3c\u2984 " * 8000,
                    "P [1].\n\n" * 10000, "\n \n\t\n" * 20000 + "x",
                    "> a\n" + "- - " * 10000 + "x", "> a\n" + "b\n" * 20000, "> " * 20000 + "x"]


def test_protected_spans_are_bounded():
    from articulate import guard
    for i, text in enumerate(SPAN_ADVERSARIAL + MEANING_ADVERSARIAL + ADVERSARIAL):
        start = time.perf_counter()
        guard.RewriteGuard().run(lambda m: m, text)
        elapsed = time.perf_counter() - start
        assert elapsed < 3.0, f"protected-span input {i} took {elapsed:.2f}s"


def test_meaning_guard_is_bounded():
    from articulate import meaning
    for i, text in enumerate(MEANING_ADVERSARIAL + ADVERSARIAL):
        start = time.perf_counter()
        meaning.compare(text, text[: len(text) // 2])
        elapsed = time.perf_counter() - start
        assert elapsed < 3.0, f"meaning.compare input {i} took {elapsed:.2f}s"


# The rule packs and project terminology (articulate.rules_ext) are timed on their
# own layer, so this budget measures them and not the core passes above.
PACK_ADVERSARIAL = [
    "button: " + "a " * 20000, '"k": "' + "x" * 40000, "<a " * 10000, "[here" * 10000,
    "MUST " * 10000, "MUST not " * 5000, "RFC 2119 " * 5000, "please " * 10000,
    "why did you " * 5000, "Open the and " * 5000, "out of the " * 8000,
    "This is " * 8000, "in order " * 8000, ("word " * 30 + ". ") * 400,
    "error: " + "oops " * 10000, "a. " * 20000, "\n".join(["- item"] * 20000),
]


def test_rule_packs_are_bounded():
    from articulate import rules_ext
    term = {"banned": [{"term": "whitelist"}],
            "preferred": [{"use": "sign in", "instead_of": ["log in"]}]}
    for name in ("ux-microcopy", "code-review", "plain-language", "normative-spec",
                 "controlled-english"):
        prof = dict(profiles.load(name), terminology=term)
        for i, text in enumerate(PACK_ADVERSARIAL + MEANING_ADVERSARIAL + ADVERSARIAL):
            start = time.perf_counter()
            rules_ext.scan(text, text.splitlines(keepends=True), prof)
            elapsed = time.perf_counter() - start
            assert elapsed < 3.0, f"{name} pack input {i} took {elapsed:.2f}s"


def test_empty_and_whitespace_are_clean():
    prof = profiles.load("flavored")
    for text in ("", "\n\n\n", "   ", "\t\t"):
        r = articulate.check_text(text, profile=prof)
        assert r["clean"] is True and r["gate"] == "ok"
