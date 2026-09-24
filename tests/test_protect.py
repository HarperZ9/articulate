"""Protected spans: masked before a rewrite, spliced back byte for byte after.

The model must never see protected content, and a rewrite is refused unless
every placeholder comes back exactly once and in order. Each refusal mode has a
control: the same text with the placeholders intact restores cleanly.
"""
import pytest

from articulate import guard, protect

DOC = ("Intro with `pip install x` and https://example.com/a?b=1 here.\n"
       "\n"
       "```python\nprint('hi')\n```\n"
       "\n"
       "> A quoted block\n> on two lines.\n"
       "\n"
       'He said "keep this" as cited [1] (Smith, 2020); see $x^2 \\le y$ and Articulate.\n')
PROTECTED = ["`pip install x`", "https://example.com/a?b=1", "```python\nprint('hi')\n```",
             "> A quoted block\n> on two lines.", '"keep this"', "[1]", "(Smith, 2020)",
             "$x^2 \\le y$", "Articulate"]


def _masked(**kw):
    return protect.mask(DOC, freeze=("Articulate",), **kw)


def test_every_protected_kind_is_hidden_from_the_model():
    masked, spans = _masked()
    for text in PROTECTED:
        assert text not in masked, text
    assert [s["text"] for s in spans] == PROTECTED       # document order
    assert {s["kind"] for s in spans} == {"code", "url", "blockquote", "quote",
                                         "citation", "math", "freeze"}


def test_round_trip_is_byte_identical():
    masked, spans = _masked()
    assert protect.restore(masked, masked, spans) == DOC


def test_prose_edits_land_and_spans_come_back_intact():
    masked, spans = _masked()
    out = protect.restore(masked.replace("Intro with", "Start with"), masked, spans)
    assert out == DOC.replace("Intro with", "Start with")


@pytest.mark.parametrize("mutate,problem", [
    (lambda m, ph: m.replace(ph[2], ""), "missing"),
    (lambda m, ph: m.replace(ph[2], ph[2] + ph[2]), "duplicated"),
    (lambda m, ph: m + ph[0].replace("_0_", "_99_"), "invented"),
    (lambda m, ph: m.replace(ph[0], "@@").replace(ph[1], ph[0]).replace("@@", ph[1]),
     "out-of-order"),
    (lambda m, ph: m.replace(ph[3], ph[3][:-1]), "mangled"),
    (lambda m, ph: m.replace(ph[3], ph[3][1:]), "mangled"),
])
def test_bad_placeholders_are_refused(mutate, problem):
    masked, spans = _masked()
    phs = [s["placeholder"] for s in spans]
    with pytest.raises(protect.ProtectError) as info:
        protect.restore(mutate(masked, phs), masked, spans)
    assert problem in {p["problem"] for p in info.value.problems}


def test_quotes_and_blockquotes_can_be_unprotected():
    masked, spans = _masked(quotes=False, blockquotes=False)
    assert '"keep this"' in masked and "> A quoted block" in masked
    assert "`pip install x`" not in masked                  # code stays protected
    assert protect.restore(masked, masked, spans) == DOC


def test_nonce_ties_placeholders_to_the_text():
    _, a = protect.mask("Use `x` now.")
    _, b = protect.mask("Use `y` now.")
    assert a[0]["placeholder"] != b[0]["placeholder"]


def test_document_that_uses_the_delimiters_itself_still_round_trips():
    text = "The ⦃ and ⦄ marks appear in prose, and `code` too.\n"
    masked, spans = protect.mask(text)
    assert protect.restore(masked, masked, spans) == text


def test_guard_hides_spans_and_restores_them():
    seen = []

    def rewrite(t):
        seen.append(t)
        return t.replace("Intro with", "Start with")
    out = guard.RewriteGuard(freeze=("Articulate",)).run(rewrite, DOC)
    assert out == DOC.replace("Intro with", "Start with")
    assert all(p not in seen[0] for p in PROTECTED)


def test_guard_refuses_a_dropped_placeholder_and_logs_the_stage():
    g = guard.RewriteGuard()
    with pytest.raises(guard.RewriteRefused) as info:
        g.run(lambda t: t.split("\n")[0], DOC)
    assert info.value.stage == "protected-span"
    assert g.log[-1]["stage"] == "protected-span" and not g.log[-1]["accepted"]


# A later pass can match across an earlier claim, because a claim is blanked to
# spaces: the quote around a code span, the attribute quote around a link, the
# citation around a URL, display math around a '>' line. Each pair is one span:
# the inner text travels inside the outer placeholder and stays hidden.
NESTED = [
    ('He said "run `ls -la` now" and left.\n', "ls -la"),
    ('<a href="https://example.com/guide">the guide</a>\n', "example.com"),
    ("As shown (Smith, 2020; https://example.com/data) here.\n", "example.com"),
    ("$$\na\n> b\n$$\nDone.\n", "> b"),
    ("\\begin{equation}\na\n> b\n\\end{equation}\nDone.\n", "> b"),
]


@pytest.mark.parametrize("text,inner", NESTED)
def test_nested_spans_round_trip_byte_for_byte(text, inner):
    masked, spans = protect.mask(text)
    assert inner not in masked
    assert protect.restore(masked, masked, spans) == text
    starts = [s["start"] for s in spans]
    assert all(a["end"] <= b["start"] for a, b in zip(spans, spans[1:])), starts


@pytest.mark.parametrize("text,inner", NESTED)
def test_guard_accepts_an_identity_rewrite_of_nested_spans(text, inner):
    assert guard.RewriteGuard().run(lambda m: m, text) == text


def test_a_partial_overlap_widens_the_outer_span():
    claims = [("code", 5, 15, None), ("quote", 0, 10, None), ("url", 2, 4, None),
              ("math", 20, 25, None)]
    assert protect._outermost(claims) == [("quote", 0, 15, None), ("math", 20, 25, None)]


def test_unprotect_rejects_unknown_kinds():
    assert guard.parse_unprotect("quotes") == {"quotes": False, "blockquotes": True}
    with pytest.raises(ValueError):
        guard.parse_unprotect("code")
