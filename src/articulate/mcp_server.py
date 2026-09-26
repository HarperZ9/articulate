#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
articulate.mcp_server -- the fastmcp server for Articulate, and the tool bodies
both MCP transports share.

Exposes the local checks and the editor layer over the Model Context Protocol
(stdio). The checks (check, score) run entirely local, with no network call. The
editor tools (judge, fix, polish) need a model backend; today the only one is the
`claude` CLI, which sends the text to a hosted Anthropic model. They return a
clean "unavailable" result when the backend cannot be reached and never fail the
call. Tool descriptions come from articulate.tool_text, the same table the
zero-dependency server (local_mcp) reads.

Run:  python -m articulate.mcp_server   (needs the [mcp] extra; stdio)
stdout carries the MCP protocol; all logging goes to stderr.
"""
import os
import tempfile

from . import detector as core
from . import editor
from .tool_text import DOES_NOT_PROVE, TOOLS

HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND_NOTE = "the editor layer needs the claude CLI, which sends the text to a hosted model"
_REFUSED_NOTE = ("the rewrite dropped, repeated or invented a masked math span and was "
                 "refused; the text is unchanged")


def _scan_text(text):
    """Write text to a temp file and run the deterministic detector on it."""
    fd, path = tempfile.mkstemp(suffix=".md", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        return core.scan(path)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _mech_summary(text):
    fd, path = tempfile.mkstemp(suffix=".md", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        return editor.mechanical(path)          # (clean, summary_string)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


# --------------------------------------------------------------------------- #
# Plain, testable implementations. The MCP tools are thin wrappers over these.
# --------------------------------------------------------------------------- #

def do_check(text):
    """Named prose patterns with span records. Local, no network."""
    r = core.check_text(text)
    hits = sorted(r["high"] + r["medium"], key=lambda h: h["start"])
    return {
        "gate": r["gate"],
        "findings": r["findings"],
        "hits": hits,
        "advisory_count": len(r["low"]),
        "rule_counts": r["rule_counts"],
        "density": r["density"],
        "cadence": r["cadence"],
        "does_not_prove": DOES_NOT_PROVE,
    }


def do_score(text):
    """Per-rule counts, density with an interval and structural rates."""
    r = core.check_text(text)
    cad = r["cadence"]
    return {
        "gate": r["gate"],
        "words": r["words"],
        "rule_counts": r["rule_counts"],
        "density": r["density"],
        "passive_rate": cad["passive_rate"],
        "adverb_rate": cad["adverb_rate"],
        "uniform_cadence": cad["uniform"],
        "does_not_prove": DOES_NOT_PROVE,
    }


def do_judge(text):
    """Skilled-editor read of judgment-level failures. Needs the LLM backend."""
    _, mech = _mech_summary(text)
    from .prompts import judge_instructions
    instr = judge_instructions(mech)
    try:
        return {"ok": True, "read": editor.claude_call(instr, text)}
    except (RuntimeError, Exception) as e:  # noqa: BLE001 - report cleanly to the host
        return {"ok": False, "error": str(e),
                "note": "detection tools work offline; the editor layer needs the claude CLI, "
                        "which sends the text to a hosted model"}


def _rewrite(text, worst, is_html, is_tex):
    """One editor rewrite. With is_tex, every LaTeX math span is masked before the
    model call and spliced back byte for byte, as the CLI does for a .tex file."""
    if is_tex:
        return editor.masked_rewrite(
            text, lambda t, mech: editor.rewrite_once(t, mech, worst, is_html))
    return editor.rewrite_once(text, _mech_summary(text)[1], worst, is_html)


def do_fix(text, is_html=False, is_tex=False):
    """Rewrite to the standard, self-gated on the detector. Needs the LLM backend."""
    try:
        rewrite = _rewrite(text, [], is_html, is_tex)
    except editor.MathSpliceError as e:
        return {"ok": False, "error": str(e), "note": _REFUSED_NOTE}
    except (RuntimeError, Exception) as e:  # noqa: BLE001
        return {"ok": False, "error": str(e),
                "note": _BACKEND_NOTE}
    after = do_check(rewrite)
    return {"ok": True, "rewrite": rewrite,
            "findings_after": after["findings"], "gate_after": after["gate"],
            "note": "a suggestion; read it against the original before shipping"}


def _polish_scores(cur, is_tex):
    q = editor.quality_judge(editor.mask_math(cur)[0] if is_tex else cur)
    return q, {k: int(q.get(k, 0) or 0) for k in editor.QUALITIES}


def do_polish(text, bar=4, passes=3, is_html=False, is_tex=False):
    """The quality loop, with the CLI's acceptance rule (editor.accept): a pass is
    kept only when no quality score falls and the gate does not go from ok to
    blocked. With is_tex no model call sees a formula. A rewrite refused for
    altering masked math stops the loop and keeps the last accepted text."""
    scorecard, cur, refused = [], text, None
    try:
        chk = do_check(cur)
        q, sc = _polish_scores(cur, is_tex)
        for attempt in range(passes + 1):
            scorecard.append({"pass": attempt, "scores": sc, "gate": chk["gate"],
                              "overall": q.get("overall")})
            if (chk["gate"] == "ok" and min(sc.values()) >= bar) or attempt == passes:
                break
            worst = q.get("worst", [])
            try:
                cand = _rewrite(cur, editor.scrub_math_notes(worst) if is_tex else worst,
                                is_html, is_tex)
            except editor.MathSpliceError as e:
                refused = str(e)
                break
            c_chk = do_check(cand)
            cq, csc = _polish_scores(cand, is_tex)
            ok, _why = editor.accept(sc, csc, chk["gate"], c_chk["gate"], set(), None)
            if not ok:
                break
            cur, chk, q, sc = cand, c_chk, cq, csc
    except (RuntimeError, Exception) as e:  # noqa: BLE001
        return {"ok": False, "error": str(e), "scorecard": scorecard, "note": _BACKEND_NOTE}
    out = {"ok": True, "final_text": cur, "scorecard": scorecard,
           "note": "accepted on the reader's qualities and the gate, never on an outside score"}
    if refused:
        out.update(refused=refused, note=("a rewrite pass altered masked math and was "
                                          "refused; final_text is the last accepted text"))
    return out


def _described(fn, name):
    fn.__doc__ = TOOLS[name]
    return fn


def build_server():
    from fastmcp import FastMCP
    mcp = FastMCP("articulate")

    def check(text: str) -> dict:
        return do_check(text)

    def score(text: str) -> dict:
        return do_score(text)

    def judge(text: str) -> dict:
        return do_judge(text)

    def fix(text: str, is_html: bool = False, is_tex: bool = False) -> dict:
        return do_fix(text, is_html, is_tex)

    def polish(text: str, bar: int = 4, passes: int = 3, is_html: bool = False,
               is_tex: bool = False) -> dict:
        return do_polish(text, bar, passes, is_html, is_tex)

    # One description table serves both MCP servers (tool_text.TOOLS).
    for fn in (check, score, judge, fix, polish):
        mcp.tool(_described(fn, fn.__name__))
    return mcp


if __name__ == "__main__":
    build_server().run()
