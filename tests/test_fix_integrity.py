"""The rewrite paths keep math intact and self-check under the chosen mode.

No test here calls a model. Each one replaces ``editor.claude_call`` with a fake
that records what the model would have been sent and returns a canned rewrite.
Uses a project-local temp dir (the pytest tmp_path fixture's symlink management
is denied on this Windows host).
"""
import os
import shutil

import pytest

from articulate import editor, mcp_server

_TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_tmp_fix")

INLINE = "$\\|u\\|_{L^2} \\le C$"
DISPLAY = "\\[ \\int_0^T \\|\\nabla u\\|^2 \\, dt < \\infty. \\]"
# "leverage" puts a detector finding on the math line, so the detector summary
# in the prompt quotes that line. Masking must cover the summary too.
TEX = (f"The estimate {INLINE} holds for all t, and we leverage it.\n"
       f"We bound the term {DISPLAY}\n")


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


class FakeModel:
    """Stands in for claude_call. `transform` maps the stdin text to the rewrite."""

    def __init__(self, transform):
        self.transform = transform
        self.sent = []
        self.instructions = []

    def __call__(self, instructions, text, timeout=600):
        self.sent.append(text)
        self.instructions.append(instructions)
        return self.transform(text)


def _hostile(text):
    # Would strip every '$' and backslash if it could see the math.
    return text.replace("estimate", "bound").replace("$", "").replace("\\", "")


# --- item 1: --fix masks math ------------------------------------------------ #

def test_fix_never_sends_math_to_the_model(work, monkeypatch):
    src = _write(work, "note.tex", TEX)
    out = os.path.join(work, "note.fixed.tex")
    fake = FakeModel(_hostile)
    monkeypatch.setattr(editor, "claude_call", fake)
    assert editor.fix(src, out, passes=1) == 0
    assert fake.sent, "the fake model was never called"
    for sent in fake.sent:
        assert INLINE not in sent and DISPLAY not in sent
        assert "$" not in sent
    # The detector summary in the prompt quotes document lines, so it must be
    # built from the masked text too.
    for instr in fake.instructions:
        assert INLINE not in instr and DISPLAY not in instr


def test_fix_splices_math_back_byte_for_byte(work, monkeypatch):
    src = _write(work, "note.tex", TEX)
    out = os.path.join(work, "note.fixed.tex")
    monkeypatch.setattr(editor, "claude_call", FakeModel(_hostile))
    editor.fix(src, out, passes=1)
    result = _read(out)
    assert INLINE in result
    assert DISPLAY in result
    assert "bound" in result            # the prose rewrite did land


def test_fix_refuses_a_rewrite_that_drops_a_math_span(work, monkeypatch, capsys):
    src = _write(work, "note.tex", TEX)
    out = os.path.join(work, "note.fixed.tex")
    # The model drops every placeholder, so the formulas would vanish on splice.
    fake = FakeModel(lambda t: "The bound holds for all t.\n")
    monkeypatch.setattr(editor, "claude_call", fake)
    assert editor.fix(src, out, passes=1) == 1
    assert fake.sent, "the fake model was never called"
    assert "altered masked math" in capsys.readouterr().out
    assert not os.path.exists(out)      # refused before any write


def test_polish_refuses_a_rewrite_that_drops_a_math_span(work, capsys):
    src = _write(work, "note.tex", TEX)
    out = os.path.join(work, "note.polished.tex")
    scores = {"concreteness": 1, "commitment": 1, "economy": 1, "rhythm": 1,
              "restatable": 1, "worst": ["w"]}
    calls = []

    def rewrite_fn(t, mech, worst):
        calls.append(t)
        return "The bound holds for all t.\n"

    assert editor.polish(src, out, passes=2, bar=5, rewrite_fn=rewrite_fn,
                         judge_fn=lambda t: dict(scores)) == 0
    assert len(calls) == 1              # the refusal stops the loop
    printed = capsys.readouterr().out
    assert "[polish] rewrite failed" in printed
    assert "altered masked math" in printed
    assert _read(out) == TEX            # the original is kept


def test_mcp_fix_masks_math_when_the_text_is_latex(monkeypatch):
    fake = FakeModel(_hostile)
    monkeypatch.setattr(editor, "claude_call", fake)
    res = mcp_server.do_fix(TEX, is_tex=True)
    assert res["ok"], res
    assert all(INLINE not in s and DISPLAY not in s for s in fake.sent)
    assert all(INLINE not in i for i in fake.instructions)
    assert INLINE in res["rewrite"] and DISPLAY in res["rewrite"]


# --- item 2: --fix self-checks under the chosen mode ------------------------- #

# "may potentially" is a stacked hedge (MEDIUM) under the default profile, and
# "may" is a kept term of art under technical-docs/argue (normative-spec base).
MODE_CLEAN = ("The estimate may potentially hold across 42 plots in every season we "
              "measured this year.\n")


def test_mode_clean_text_differs_by_profile():
    # Guards the premise of the next test: the text reads differently by profile.
    from articulate import modes
    assert editor.mechanical_text(MODE_CLEAN, modes.load("technical-docs/argue"))[0]
    assert not editor.mechanical_text(MODE_CLEAN, None)[0]


def test_fix_self_check_uses_the_chosen_mode(work, monkeypatch, capsys):
    src = _write(work, "draft.md", "Some draft prose that needs a rewrite today.\n")
    out = os.path.join(work, "draft.fixed.md")
    monkeypatch.setattr(editor, "claude_call", FakeModel(lambda t: MODE_CLEAN))
    assert editor.fix(src, out, passes=1, mode="technical-docs/argue") == 0
    printed = capsys.readouterr().out
    assert "pass 1: CLEAN" in printed
    assert "[fix] no HIGH or MEDIUM findings" in printed


def test_fix_self_check_without_a_mode_still_uses_the_default(work, monkeypatch, capsys):
    src = _write(work, "draft.md", "Some draft prose that needs a rewrite today.\n")
    out = os.path.join(work, "draft.fixed.md")
    monkeypatch.setattr(editor, "claude_call", FakeModel(lambda t: MODE_CLEAN))
    editor.fix(src, out, passes=1)
    printed = capsys.readouterr().out
    assert "pass 1: findings remain" in printed
