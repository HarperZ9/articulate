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


def test_fix_refuses_a_rewrite_that_drops_a_math_span(work, monkeypatch):
    src = _write(work, "note.tex", TEX)
    out = os.path.join(work, "note.fixed.tex")
    # The model drops every placeholder, so the formulas would vanish on splice.
    monkeypatch.setattr(editor, "claude_call",
                        FakeModel(lambda t: "The bound holds for all t.\n"))
    assert editor.fix(src, out, passes=1) == 1
    assert not os.path.exists(out) or INLINE in _read(out)


def test_polish_refuses_a_rewrite_that_drops_a_math_span(work):
    src = _write(work, "note.tex", TEX)
    out = os.path.join(work, "note.polished.tex")
    scores = {"concreteness": 1, "commitment": 1, "economy": 1, "rhythm": 1,
              "restatable": 1, "worst": ["w"]}
    editor.polish(src, out, passes=1, bar=5,
                  rewrite_fn=lambda t, mech, worst: "The bound holds for all t.\n",
                  judge_fn=lambda t: dict(scores))
    result = _read(out)
    assert INLINE in result and DISPLAY in result


def test_polish_prompt_summary_never_quotes_math(work):
    src = _write(work, "note.tex", TEX)
    out = os.path.join(work, "note.polished.tex")
    seen = []

    def rewrite_fn(t, mech, worst):
        seen.append((t, mech))
        return t

    editor.polish(src, out, passes=1, bar=5, rewrite_fn=rewrite_fn,
                  judge_fn=lambda t: {"concreteness": 1, "commitment": 1, "economy": 1,
                                      "rhythm": 1, "restatable": 1, "worst": ["w"]})
    assert seen, "the rewrite was never called"
    for t, mech in seen:
        assert INLINE not in t and INLINE not in mech
        assert "leverage" in mech          # the summary still reports the finding


def test_mcp_fix_masks_math_when_the_text_is_latex(monkeypatch):
    fake = FakeModel(_hostile)
    monkeypatch.setattr(editor, "claude_call", fake)
    res = mcp_server.do_fix(TEX, is_tex=True)
    assert res["ok"], res
    assert all(INLINE not in s and DISPLAY not in s for s in fake.sent)
    assert all(INLINE not in i for i in fake.instructions)
    assert INLINE in res["rewrite"] and DISPLAY in res["rewrite"]


def test_mcp_polish_masks_math_when_the_text_is_latex(monkeypatch):
    fake = FakeModel(_hostile)
    monkeypatch.setattr(editor, "claude_call", fake)
    monkeypatch.setattr(editor, "quality_judge",
                        lambda t: {"concreteness": 1, "commitment": 1, "economy": 1,
                                   "rhythm": 1, "restatable": 1, "worst": ["w"]})
    res = mcp_server.do_polish(TEX, bar=5, passes=1, is_tex=True)
    assert res["ok"], res
    assert all(INLINE not in s and DISPLAY not in s for s in fake.sent)
    assert INLINE in res["final_text"] and DISPLAY in res["final_text"]


# --- item 2: --fix self-checks under the chosen mode ------------------------- #

# "robust" is a register-word tell under the default profile and a kept term of
# art under academic/explain. Everything else in this text is clean under both.
MODE_CLEAN = ("The robust estimate holds across 42 plots in every season we measured "
              "this year, from the dry spring to the wet autumn.\n")


def test_mode_clean_text_differs_by_profile():
    # Guards the premise of the next test: the text reads differently by profile.
    from articulate import modes
    assert editor.mechanical_text(MODE_CLEAN, modes.load("academic/explain"))[0]
    assert not editor.mechanical_text(MODE_CLEAN, None)[0]


def test_fix_self_check_uses_the_chosen_mode(work, monkeypatch, capsys):
    src = _write(work, "draft.md", "Some draft prose that needs a rewrite today.\n")
    out = os.path.join(work, "draft.fixed.md")
    monkeypatch.setattr(editor, "claude_call", FakeModel(lambda t: MODE_CLEAN))
    assert editor.fix(src, out, passes=1, mode="academic/explain") == 0
    printed = capsys.readouterr().out
    assert "pass 1: CLEAN" in printed
    assert "[fix] clean of mechanical tells" in printed


def test_fix_self_check_without_a_mode_still_uses_the_default(work, monkeypatch, capsys):
    src = _write(work, "draft.md", "Some draft prose that needs a rewrite today.\n")
    out = os.path.join(work, "draft.fixed.md")
    monkeypatch.setattr(editor, "claude_call", FakeModel(lambda t: MODE_CLEAN))
    editor.fix(src, out, passes=1)
    printed = capsys.readouterr().out
    assert "pass 1: still has tells" in printed
