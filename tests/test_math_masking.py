"""Math masking holds for nested math and for every model call a rewrite makes.

A theorem, lemma or proof environment usually contains inline or display math.
Masking must keep that nesting restorable, so a rewrite of an ordinary LaTeX
paper round-trips every formula byte for byte. Polish must also keep formulas out
of the quality-scoring call, not only the rewrite call.

No test here calls a model. Each one replaces ``editor.claude_call`` with a fake
that answers the quality-scoring prompt with score JSON and every other prompt
with a canned rewrite, and records every call. Uses a project-local temp dir (the
pytest tmp_path fixture's symlink management is denied on this Windows host).
"""
import json
import os
import shutil

import pytest

from articulate import editor, mcp_server

_TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_tmp_masking")

THEOREM = ("\\begin{theorem}\nLet $x > 0$ and $y > 0$. Then $x y > 0$, and we "
           "leverage it.\n\\end{theorem}")
PROOF = "\\begin{proof}\nSince \\[x \\cdot x = x^2\\] the claim follows.\n\\end{proof}"
TOP_INLINE = "$a \\le b$"
NESTED = (f"We leverage a simple bound here.\n{THEOREM}\n"
          f"The estimate {TOP_INLINE} holds.\n{PROOF}\n")
FORMULAS = ("$x > 0$", "$y > 0$", "$x y > 0$", "\\[x \\cdot x = x^2\\]", TOP_INLINE)

# Flat math with a detector finding on the math line, so the detector summary
# and a judge note that quotes the first line would both carry the formula.
INLINE = "$\\|u\\|_{L^2} \\le C$"
DISPLAY = "\\[ \\int_0^T \\|\\nabla u\\|^2 \\, dt < \\infty. \\]"
FLAT = (f"The estimate {INLINE} holds for all t, and we leverage it.\n"
        f"We bound the term {DISPLAY}\n")

LOW = {"concreteness": 1, "commitment": 1, "economy": 1, "rhythm": 1,
       "restatable": 1, "verdict": "revise"}


@pytest.fixture()
def work():
    os.makedirs(_TMP, exist_ok=True)
    yield _TMP
    shutil.rmtree(_TMP, ignore_errors=True)


def _write(work, name, text):
    p = os.path.join(work, name)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)
    return p


def _read(p):
    with open(p, encoding="utf-8") as fh:
        return fh.read()


class Model:
    """Stands in for claude_call. The quality-scoring prompt gets score JSON whose
    'worst' note quotes the first line of the text it was sent, as a real judge
    quotes an offender. Every other prompt gets transform(text)."""

    def __init__(self, transform):
        self.transform = transform
        self.calls = []

    def __call__(self, instructions, text, timeout=600):
        self.calls.append((instructions, text))
        if instructions.startswith("Score the text"):
            first = text.strip().splitlines()[0]
            return json.dumps(dict(LOW, worst=[f"tighten this line: {first}"]))
        return self.transform(text)

    def judge_calls(self):
        return [c for c in self.calls if c[0].startswith("Score the text")]

    def rewrite_calls(self):
        return [c for c in self.calls if not c[0].startswith("Score the text")]


def _benign(text):
    return text.replace("leverage", "use")


def _drop_all(text):
    return "The bound holds for all t.\n"


# --- nested math round-trips ------------------------------------------------- #

@pytest.mark.parametrize("doc", [THEOREM, PROOF, NESTED, FLAT])
def test_mask_then_splice_round_trips(doc):
    assert editor.splice_math(*editor.mask_math(doc)) == doc


def test_an_environment_is_masked_whole():
    masked, spans = editor.mask_math(NESTED)
    assert THEOREM in spans and PROOF in spans
    for s in spans:
        assert not editor._MATH_PLACEHOLDER_RX.search(s)
    for f in FORMULAS:
        assert f not in masked


def test_fix_identity_on_nested_math_returns_the_input(work, monkeypatch):
    src = _write(work, "paper.tex", NESTED)
    out = os.path.join(work, "paper.fixed.tex")
    fake = Model(lambda t: t)
    monkeypatch.setattr(editor, "claude_call", fake)
    assert editor.fix(src, out, passes=1, mode="academic/prove") == 0
    assert fake.rewrite_calls()
    assert _read(out) == NESTED


def test_fix_benign_rewrite_on_nested_math_keeps_every_formula(work, monkeypatch):
    src = _write(work, "paper.tex", NESTED)
    out = os.path.join(work, "paper.fixed.tex")
    monkeypatch.setattr(editor, "claude_call", Model(_benign))
    assert editor.fix(src, out, passes=1) == 0
    result = _read(out)
    assert result.startswith("We use a simple bound here.")
    assert THEOREM in result and PROOF in result and TOP_INLINE in result
    assert not editor._MATH_PLACEHOLDER_RX.search(result)


def test_polish_accepts_a_benign_rewrite_on_nested_math(work, monkeypatch, capsys):
    src = _write(work, "paper.tex", NESTED)
    out = os.path.join(work, "paper.polished.tex")
    fake = Model(_benign)
    monkeypatch.setattr(editor, "claude_call", fake)
    assert editor.polish(src, out, passes=1, bar=5) == 0
    assert "rewrite failed" not in capsys.readouterr().out
    assert len(fake.rewrite_calls()) == 1
    assert _read(out) == NESTED.replace("We leverage", "We use")


def test_mcp_fix_on_nested_math(monkeypatch):
    monkeypatch.setattr(editor, "claude_call", Model(lambda t: t))
    res = mcp_server.do_fix(NESTED, is_tex=True)
    assert res["ok"], res
    # rewrite_once strips surrounding whitespace, so compare without the final newline.
    assert res["rewrite"] == NESTED.rstrip()


def test_mcp_polish_on_nested_math(monkeypatch):
    monkeypatch.setattr(editor, "claude_call", Model(_benign))
    res = mcp_server.do_polish(NESTED, bar=5, passes=1, is_tex=True)
    assert res["ok"], res
    assert res["final_text"] == NESTED.replace("We leverage", "We use").rstrip()


# --- polish keeps formulas out of every model call --------------------------- #

def _assert_no_formula_in(calls):
    for instructions, text in calls:
        for f in (INLINE, DISPLAY):
            assert f not in text
            assert f not in instructions


def test_cli_polish_sends_no_formula_on_any_model_call(work, monkeypatch):
    src = _write(work, "note.tex", FLAT)
    out = os.path.join(work, "note.polished.tex")
    fake = Model(_benign)
    monkeypatch.setattr(editor, "claude_call", fake)
    assert editor.polish(src, out, passes=1, bar=5) == 0
    assert len(fake.judge_calls()) == 2 and len(fake.rewrite_calls()) == 1
    _assert_no_formula_in(fake.calls)
    # The detector summary still reports the finding, from the masked text.
    assert "leverage" in fake.rewrite_calls()[0][0]
    assert INLINE in _read(out) and DISPLAY in _read(out)


def test_mcp_polish_sends_no_formula_on_any_model_call(monkeypatch):
    fake = Model(_benign)
    monkeypatch.setattr(editor, "claude_call", fake)
    res = mcp_server.do_polish(FLAT, bar=5, passes=1, is_tex=True)
    assert res["ok"], res
    assert len(fake.judge_calls()) == 2 and len(fake.rewrite_calls()) == 1
    _assert_no_formula_in(fake.calls)
    assert INLINE in res["final_text"] and DISPLAY in res["final_text"]


def test_polish_without_tex_still_scores_the_full_text(work, monkeypatch):
    # Regression guard: masking applies to math files only.
    src = _write(work, "note.md", FLAT)
    fake = Model(_benign)
    monkeypatch.setattr(editor, "claude_call", fake)
    editor.polish(src, os.path.join(work, "note.polished.md"), passes=1, bar=5)
    assert INLINE in fake.judge_calls()[0][1]


# --- MCP reports a refused rewrite as a refusal, not a backend fault ---------- #

def test_mcp_fix_reports_a_refused_rewrite(monkeypatch):
    monkeypatch.setattr(editor, "claude_call", Model(_drop_all))
    res = mcp_server.do_fix(FLAT, is_tex=True)
    assert res["ok"] is False
    assert "altered masked math" in res["error"]
    assert "refused" in res["note"] and "claude CLI" not in res["note"]


def test_mcp_polish_keeps_the_best_text_when_a_rewrite_is_refused(monkeypatch):
    fake = Model(_drop_all)
    monkeypatch.setattr(editor, "claude_call", fake)
    res = mcp_server.do_polish(FLAT, bar=5, passes=2, is_tex=True)
    assert res["ok"] is True
    assert res["final_text"] == FLAT
    assert "refused" in res["note"] and "claude CLI" not in res["note"]
    assert len(fake.rewrite_calls()) == 1          # the loop stops at the refusal
    assert len(res["scorecard"]) == 1


def test_a_dropped_environment_span_is_still_refused():
    masked, spans = editor.mask_math(NESTED)
    i = spans.index(THEOREM)
    broken = masked.replace(editor._MATH_PLACEHOLDER.format(i), "")
    with pytest.raises(editor.MathSpliceError):
        editor.splice_math(broken, spans)
