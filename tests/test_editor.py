"""The monotonic no-regression contract, tested without an LLM by injecting the
rewrite and judge functions. Uses a project-local temp dir (the pytest tmp_path
fixture's symlink management is denied on this Windows host)."""
import os
import shutil

import pytest

from articulate import editor

_TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_tmp")


@pytest.fixture()
def work():
    os.makedirs(_TMP, exist_ok=True)
    yield _TMP
    shutil.rmtree(_TMP, ignore_errors=True)


def _scored(**kw):
    d = {"concreteness": 1, "commitment": 1, "economy": 1, "rhythm": 1,
         "restatable": 1, "worst": ["w"]}
    d.update(kw)
    return d


def _write(work, name, text):
    p = os.path.join(work, name)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)
    return p


def _read(p):
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def test_monotonic_accepts_improvement_then_rejects_regression(work):
    src = _write(work, "x.md", "v0 text\n")
    out = os.path.join(work, "x.polished.md")
    scores = {
        "v0 text": _scored(concreteness=2, commitment=2, economy=2, rhythm=2, restatable=2),
        "v1": _scored(concreteness=4, commitment=4, economy=4, rhythm=4, restatable=4),
        "v2": _scored(concreteness=3, commitment=4, economy=4, rhythm=4, restatable=4),  # regresses
    }
    outputs = iter(["v1", "v2"])
    editor.polish(src, out, passes=3, bar=5,
                  rewrite_fn=lambda t, mech, worst: next(outputs),
                  judge_fn=lambda t: scores.get(t.strip(), _scored()))
    # v0(2s) -> v1(4s) accepted -> v2 regresses concreteness (3<4) -> rejected, keep v1
    assert _read(out).strip() == "v1"


def test_bar_met_stops_early(work):
    src = _write(work, "y.md", "already good\n")
    out = os.path.join(work, "y.polished.md")

    def boom(*a):
        raise AssertionError("should not rewrite when the bar is already met")

    editor.polish(src, out, passes=3, bar=5, rewrite_fn=boom,
                  judge_fn=lambda t: _scored(concreteness=5, commitment=5, economy=5,
                                             rhythm=5, restatable=5))
    assert _read(out).strip() == "already good"


def test_narrative_mode_does_not_rewrite(work):
    src = _write(work, "n.md", "Some literary prose.\n")
    out = os.path.join(work, "n.polished.md")

    def boom(*a):
        raise AssertionError("narrative/narrate must not rewrite by default")

    editor.polish(src, out, passes=2, bar=5, mode="narrative/narrate",
                  rewrite_fn=boom, judge_fn=lambda t: _scored())
    assert _read(out) == "Some literary prose.\n"
