"""Protected spans on the shapes a plain pattern gets wrong: a span nested in
another, a URL with brackets, LaTeX environments and quotes, a block quote with
lazy lines, and freeze terms in either Unicode normalization.

Every case checks the byte-for-byte round trip. A generated set mixes all of
these shapes with CRLF line ends and placeholder-shaped text, and checks that an
identity rewrite comes back unchanged through the whole guard.
"""
import random

import pytest

from articulate import guard, protect


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


LAZY = "> The board approved the plan\nafter a long review of the filings.\n\nWe agree.\n"


@pytest.mark.parametrize("text", [LAZY, LAZY.replace("\n", "\r\n")])
def test_a_lazy_continuation_line_stays_inside_the_block_quote(text):
    # CommonMark keeps a non-blank line right after quoted paragraph text inside
    # the quote, with or without its '>'.
    masked, spans = protect.mask(text)
    nl = "\r\n" if "\r\n" in text else "\n"
    assert [s["text"] for s in spans] == [
        "> The board approved the plan" + nl + "after a long review of the filings."]
    assert guard.RewriteGuard().run(lambda m: m.replace("long", "short"), text) == text


@pytest.mark.parametrize("text", ["$$\na\n> b\nc\n$$\nDone.\n", "$$\na\n> b\n$$\nDone.\n"])
def test_a_quote_line_inside_display_math_leaves_the_math_whole(text):
    # A lazy line must not carry the quote over the closing $$, or the math
    # loses its closer and its body reaches the model.
    masked, spans = protect.mask(text)
    assert [s["text"] for s in spans] == [text[:text.index("\nDone")]]
    assert masked.endswith("\nDone.\n") and "a" not in masked.replace("Done", "")


def test_a_quote_line_in_a_tex_file_is_not_a_block_quote():
    text = "The set\n> is ordered by size\nand then by name.\n"
    masked, spans = protect.mask(text, tex=True)
    assert masked == text and spans == []


@pytest.mark.parametrize("after", ["\n\nNext.", "\n- item", "\n# Heading", "\n```\nx\n```",
                                   "\n---", "\n>\nNext.", "\n| a | b |", "\n<div>x</div>"])
def test_a_block_quote_ends_at_a_blank_line_or_a_new_block(after):
    masked, spans = protect.mask("> Quoted text." + after + "\n")
    assert spans[0]["text"] == ("> Quoted text.\n>" if after.startswith("\n>\n")
                                else "> Quoted text.")


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


FREEZE = ("Articulate", "Zo\u00eb")
ATOMS = ["a", " ", "\n", "\r\n", "\n\n", "> ", ">", "`", "``", "```", "~~~", "$", "$$",
         "\\[", "\\]", "\\(", "\\)", "\\begin{align}", "\\end{align}", "\\begin{proof}",
         "\\end{proof}", '"', "\u201c", "\u201d", "(", ")", "[", "]", "[1]", "[@k]", "[^n]",
         "(Smith, 2020)", "Smith et al.", "https://x.org/a_(b)", "www.e.com", "a@b.co",
         "doi:10.1000/x", "\u2983", "\u2984", "\u2983CODE_0_1a2b3c\u2984", "- ", "# ", "|",
         '<a href="https://e.com">', "</a>", "Zo\u00eb", "Zoe\u0308", "Articulate", "1.",
         "not", "3 ms", "\t", "*", "_"]


def test_an_identity_rewrite_of_generated_documents_comes_back_unchanged():
    # Before the nesting, literal, and lazy-quote fixes, 954 of these 3000 checks
    # failed: a duplicated tail, an invented placeholder, or a refusal of the
    # unchanged text.
    rng = random.Random(20260923)
    for _ in range(1500):
        text = "".join(rng.choice(ATOMS) for _ in range(rng.randint(0, 30)))
        for tex in (False, True):
            masked, spans = protect.mask(text, freeze=FREEZE, tex=tex)
            assert protect.restore(masked, masked, spans) == text, repr(text)
            assert guard.RewriteGuard(freeze=FREEZE).run(lambda m: m, text, tex=tex) == text
