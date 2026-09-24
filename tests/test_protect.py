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


OWN_QUOTE = 'I said "this plan is really very good, not ready yet" and moved on.\n'


def test_unprotected_quotes_are_prose_to_the_meaning_guard_too():
    # --unprotect quotes shows the quote to the model; the meaning guard then
    # reads it as prose, so trimming a word inside it is no changed quote.
    g = guard.RewriteGuard(protect_opts={"quotes": False})
    out = g.run(lambda m: m.replace("really very good", "good"), OWN_QUOTE)
    assert out == OWN_QUOTE.replace("really very good", "good")
    assert g.log[-1]["report"]["by_kind"].get("quote") is None


def test_unprotected_quotes_still_keep_their_invariants():
    # The words inside the quote are checked as prose: a dropped negation there
    # still refuses the rewrite.
    g = guard.RewriteGuard(protect_opts={"quotes": False})
    with pytest.raises(guard.RewriteRefused) as info:
        g.run(lambda m: m.replace("not ready", "ready"), OWN_QUOTE)
    assert {r["kind"] for r in info.value.blocking} == {"negation"}


def test_protected_quotes_refuse_an_edit_inside_them():
    edited = OWN_QUOTE.replace("really very good", "good")
    with pytest.raises(guard.RewriteRefused) as info:
        guard.RewriteGuard().check(OWN_QUOTE, edited)
    assert {r["kind"] for r in info.value.blocking} == {"quote"}


def test_unprotect_rejects_unknown_kinds():
    assert guard.parse_unprotect("quotes") == {"quotes": False, "blockquotes": True}
    with pytest.raises(ValueError):
        guard.parse_unprotect("code")
