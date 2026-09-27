"""An empty pair of quote marks ("" or a curly pair with nothing inside) is a
pair of its own. It must not lend its closing mark to the next quote on the
line, or the prose between the two is read as a quotation and the real
quotation after it is left open to the model and to the meaning guard.
"""
import pytest

from articulate import finders, guard, protect

LINE = 'Set the name to "" and write "the board approved it" in the log.\n'
CURLY = "Set the name to “” and write “the board approved it” in the log.\n"


@pytest.mark.parametrize("text,quote", [
    (LINE, '"the board approved it"'),
    (CURLY, "“the board approved it”"),
    ('"" x"', None),
    ('empty "" then "q"', '"q"'),
    ('two "" "" pairs', None),
])
def test_an_empty_pair_is_no_span_and_does_not_open_the_next(text, quote):
    spans = [text[s:e] for s, e, _ in finders.quote_spans(text)]
    assert spans == ([quote] if quote else [])


@pytest.mark.parametrize("text", [LINE, CURLY])
def test_the_quote_after_an_empty_pair_is_protected(text):
    masked, spans = protect.mask(text)
    assert [s["kind"] for s in spans] == ["quote"]
    assert "the board approved it" not in masked
    assert " and write " in masked


@pytest.mark.parametrize("text", [LINE, CURLY])
def test_an_edit_inside_the_quote_after_an_empty_pair_is_refused(text):
    edited = text.replace("approved", "rejected")
    with pytest.raises(guard.RewriteRefused):
        guard.RewriteGuard().check(text, edited)
    out = guard.RewriteGuard().run(lambda m: m.replace("approved", "rejected"), text)
    assert out == text
