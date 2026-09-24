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
    assert [s["kind"] for s in spans] == ["literal", "code"]
    text = "A lone ⦄ and a lone ⦃ appear in prose, and `code` too.\n"
    masked, spans = protect.mask(text)
    assert protect.restore(masked, masked, spans) == text
    assert [s["kind"] for s in spans] == ["literal", "literal", "code"]
    # A mangled placeholder still shows: a stray bracket the model leaves behind
    # was not in the prose that went in.
    with pytest.raises(protect.ProtectError):
        protect.restore(masked.replace(spans[2]["placeholder"], spans[2]["placeholder"][1:]),
                        masked, spans)


def test_placeholder_shaped_text_in_the_document_is_masked_as_its_own_span():
    # The editor prompt shows this example placeholder, so a document about the
    # editor can quote it. It must not read as an invented placeholder.
    text = "A placeholder such as ⦃CODE_0_1a2b3c⦄ appears in logs.\n"
    masked, spans = protect.mask(text)
    assert "CODE_0_1a2b3c" not in masked
    assert [s["kind"] for s in spans] == ["literal"]
    out = guard.RewriteGuard().run(lambda m: m.replace("appears in", "shows up in"), text)
    assert out == text.replace("appears in", "shows up in")
    with pytest.raises(guard.RewriteRefused):
        guard.RewriteGuard().run(lambda m: m.replace(spans[0]["placeholder"], ""), text)


def test_a_self_referential_nonce_cannot_let_a_code_span_move(monkeypatch):
    # A text can be built so the hash nonce equals one written in the text. Force
    # that case: the first hash candidate is the nonce the text already holds.
    text = "Keep `SAFE_MODE=1` on. Legacy note: ⦃CODE_0_000000⦄ ref 7.\n"
    real = protect._candidate
    monkeypatch.setattr(protect, "_candidate",
                        lambda t, i: "000000" if i == 0 else real(t, i))
    masked, spans = protect.mask(text)
    nonce = spans[0]["placeholder"].rsplit("_", 1)[1][:-1]
    assert nonce != "000000" and nonce not in text
    assert [s["kind"] for s in spans] == ["code", "literal"]

    def drop_first(m):
        return m.replace(spans[0]["placeholder"], "it", 1)
    with pytest.raises(guard.RewriteRefused):
        guard.RewriteGuard().run(drop_first, text)


# A freeze term matches whatever Unicode normalization the document uses, and a
# term padded with spaces still matches the word.
NFC_ZOE, NFD_ZOE = "Zo\u00eb", "Zoe\u0308"


@pytest.mark.parametrize("term,doc_form", [(NFC_ZOE, NFD_ZOE), (NFD_ZOE, NFC_ZOE),
                                           (NFC_ZOE, NFC_ZOE)])
def test_a_freeze_term_matches_either_normalization(term, doc_form):
    text = f"Ask {doc_form} about it.\n"
    masked, spans = protect.mask(text, freeze=(term,))
    assert [s["text"] for s in spans] == [doc_form]
    with pytest.raises(guard.RewriteRefused):
        guard.RewriteGuard(freeze=(term,)).check(text, "Ask Zoe about it.\n")


def test_a_freeze_term_is_not_the_base_of_an_accented_word():
    masked, spans = protect.mask(f"Ask {NFD_ZOE} about it.\n", freeze=("Zoe",))
    assert spans == []


def test_a_freeze_term_with_surrounding_spaces_still_matches():
    masked, spans = protect.mask("Articulate is local.\n", freeze=(" Articulate ",))
    assert [s["text"] for s in spans] == ["Articulate"]


TRIAL = "Drug A lowers the risk [1].\n\nDrug B raises the risk.\n"


def _move_cite(m):
    ph = protect.PLACEHOLDER.search(m).group(0)
    return m.replace(" " + ph, "").replace("raises the risk.", "raises the risk " + ph + ".")


@pytest.mark.parametrize("text", [TRIAL, TRIAL.replace("\n", "\r\n")])
def test_a_citation_moved_to_another_paragraph_is_refused(text):
    g = guard.RewriteGuard()
    with pytest.raises(guard.RewriteRefused) as info:
        g.run(_move_cite, text)
    assert info.value.stage == "protected-span"
    assert [p["problem"] for p in info.value.blocking] == ["moved"]
    assert "moved placeholder citation '[1]'" in str(info.value)


def test_a_citation_moved_within_its_paragraph_is_accepted():
    text = "Drug A lowers the risk [1] in adults.\n\nDrug B raises the risk.\n"
    out = guard.RewriteGuard().run(
        lambda m: m.replace(" in adults", "").replace("the risk ", "the adult risk "), text)
    assert out == "Drug A lowers the adult risk [1].\n\nDrug B raises the risk.\n"


def test_a_move_across_merged_paragraphs_is_a_documented_limit():
    """A rewrite that merges or splits paragraphs is checked for order only, so
    a citation that moves while the paragraph count changes is not caught.
    docs/boundaries.md states this limit."""
    def merge_and_move(m):
        return _move_cite(m).replace(".\n\nDrug B", ". Drug B")
    out = guard.RewriteGuard().run(merge_and_move, TRIAL)
    assert out == "Drug A lowers the risk. Drug B raises the risk [1].\n"


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


# A URL can hold brackets. The ones it opens stay inside the span; a closer that
# ends a Markdown link or a parenthesis, trailing punctuation, and a citation
# written right after the URL stay outside it.
URLS = [
    ("See https://en.wikipedia.org/wiki/Mercury_(planet) for details.\n",
     ["https://en.wikipedia.org/wiki/Mercury_(planet)"]),
    ("Read [C](https://en.wikipedia.org/wiki/C_(programming_language)) first.\n",
     ["https://en.wikipedia.org/wiki/C_(programming_language)"]),
    ("Cited at https://doi.org/10.1016/S0140-6736(20)30183-5 in full.\n",
     ["https://doi.org/10.1016/S0140-6736(20)30183-5"]),
    ("See https://example.com/docs[1].\n", ["https://example.com/docs", "[1]"]),
    ("(See https://example.com/a.)\n", ["https://example.com/a"]),
    ("Read [the guide](https://example.com/guide), then go.\n",
     ["https://example.com/guide"]),
    ("Filter with https://example.com/q?a[0]=1 today.\n",
     ["https://example.com/q?a[0]=1"]),
]


@pytest.mark.parametrize("text,expected", URLS)
def test_urls_keep_their_own_brackets(text, expected):
    masked, spans = protect.mask(text)
    assert [s["text"] for s in spans] == expected
    assert protect.restore(masked, masked, spans) == text


def test_a_model_cannot_drop_the_closing_bracket_of_a_url():
    text = "See https://en.wikipedia.org/wiki/Mercury_(planet) for details.\n"
    out = guard.RewriteGuard().run(lambda m: m.replace(") for", " for"), text)
    assert out == text
    cut = text.replace(") for", " for")
    with pytest.raises(guard.RewriteRefused):
        guard.RewriteGuard().check(text, cut)


PAPER = ("\\documentclass{article}\n\\begin{document}\n\\begin{abstract}\n"
         "We show the method is fast.\n\\end{abstract}\n"
         "\\begin{itemize}\n\\item Use ``quick'' and ``slow'' modes.\n\\end{itemize}\n"
         "\\begin{align*}\nf(x) &\\le g(x)\n\\end{align*}\n"
         "\\begin{theorem}\nFor all $n$ there exists $m > n$.\n\\end{theorem}\n"
         "It is robust.\n\\end{document}\n")


def test_tex_prose_environments_reach_the_model():
    masked, spans = protect.mask(PAPER, tex=True)
    for prose in ("We show the method is fast.", "\\item Use ``quick'' and ``slow'' modes.",
                  "It is robust.", "\\begin{abstract}", "\\begin{document}"):
        assert prose in masked, prose
    hidden = [s["text"] for s in spans]
    assert "\\begin{align*}\nf(x) &\\le g(x)\n\\end{align*}" in hidden
    # Theorem-like environments stay protected, as the math mask in 0.4.1 had
    # them: a changed quantifier order changes a theorem.
    assert any(t.startswith("\\begin{theorem}") for t in hidden)
    assert protect.restore(masked, masked, spans) == PAPER


def test_tex_double_backticks_are_quotes_and_markdown_ones_are_code():
    tex_masked, _ = protect.mask("Use ``quick'' and ``slow'' modes.\n", tex=True)
    assert "``quick''" in tex_masked
    md_masked, _ = protect.mask("Run ``ls -la`` first.\n")
    assert "ls -la" not in md_masked


def test_guard_lets_a_tex_rewrite_edit_prose_between_latex_quotes():
    # The meaning guard reads the file as .tex too, so the words between two
    # LaTeX quotes are prose there as well, and not a code span that changed.
    def edit(m):
        return m.replace("It is robust.", "It holds.").replace("'' and ``", "'' or ``")
    out = guard.RewriteGuard().run(edit, PAPER, tex=True)
    assert out == edit(PAPER)


def test_unprotect_rejects_unknown_kinds():
    assert guard.parse_unprotect("quotes") == {"quotes": False, "blockquotes": True}
    with pytest.raises(ValueError):
        guard.parse_unprotect("code")
