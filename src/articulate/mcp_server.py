#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
articulate.mcp_server -- the fastmcp server for Articulate, and the tool bodies
both MCP transports share.

Exposes the local checks and the editor layer over the Model Context Protocol
(stdio). The checks (check, score) and the meaning guard (compare) run entirely
local, with no network call. The
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
from typing import List, Optional

from . import detector as core
from . import editor, guard, meaning
from .local_only import LocalOnly
from .origin_guard import note as origin_note
from .origin_guard import strip_origin_guesses
from .tool_text import DOES_NOT_PROVE, TOOLS

HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND_NOTE = "the editor layer needs the claude CLI, which sends the text to a hosted model"
_REFUSED_NOTE = ("the rewrite dropped, repeated, moved or invented a protected span (code, "
                 "math, a link, a citation, a quote or a freeze term) and was refused; the "
                 "text is unchanged")
_GUARD_NOTE = ("the rewrite changed a surface invariant of the text and was refused; the "
               "text is unchanged. Pass allow_change to accept a named kind of change")
_LOCAL_ONLY_NOTE = ("local-only: the switch is on, so the text was not sent; the check and "
                    "score tools still run")


def _failure_note(err):
    """Why a hosted tool returned no result: the local-only switch or the backend."""
    return _LOCAL_ONLY_NOTE if isinstance(err, LocalOnly) else _BACKEND_NOTE


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
    r = core.check_text(text, house_notes=False)
    hits = sorted(r["high"] + r["medium"], key=lambda h: h["start"])
    return {
        "gate": r["gate"],
        "findings": r["findings"],
        "blocking": r["blocking"],
        # Deprecated: no HIGH or MEDIUM finding. Kept until package 0.7.0.
        "clean": r["clean"],
        "hits": hits,
        "advisory_count": len(r["low"]),
        "rule_counts": r["rule_counts"],
        "density": r["density"],
        "cadence": r["cadence"],
        "does_not_prove": DOES_NOT_PROVE,
    }


def do_score(text):
    """Per-rule counts, density with an interval and structural rates."""
    r = core.check_text(text, house_notes=False)
    cad = r["cadence"]
    return {
        "gate": r["gate"],
        "words": r["words"],
        "rule_counts": r["rule_counts"],
        "density": r["density"],
        "passive_rate": cad["passive_rate"],
        "adverb_rate": cad["adverb_rate"],
        "does_not_prove": DOES_NOT_PROVE,
    }


def do_judge(text):
    """Skilled-editor read of judgment-level failures. Needs the LLM backend."""
    _, mech = _mech_summary(text)
    from .prompts import judge_instructions
    instr = judge_instructions(mech)
    try:
        read, removed = strip_origin_guesses(editor.claude_call(instr, text))
        out = {"ok": True, "read": read, "does_not_prove": DOES_NOT_PROVE}
        if removed:
            out["note"] = origin_note(removed)
        return out
    except (RuntimeError, Exception) as e:  # noqa: BLE001 - report cleanly to the host
        return {"ok": False, "error": str(e), "note": _failure_note(e)}


def _refusal(e):
    """A refused rewrite as data: the check that refused it, why, and what blocked it."""
    return {"stage": e.stage, "reason": editor.refusal_text(e), "blocking": e.blocking}


def _refused_note(e):
    return _GUARD_NOTE if e.stage == "meaning" else _REFUSED_NOTE


def do_compare(original, rewrite, freeze=None, allow_change=""):
    """The meaning guard: which surface invariants a rewrite kept, dropped, added,
    or changed. Local, no network."""
    if isinstance(freeze, str):
        freeze = [freeze]
    if any(not isinstance(t, str) for t in (freeze or ())):
        raise ValueError("'freeze' must be a list of strings")
    report = meaning.compare(original, rewrite, freeze=tuple(freeze or ()))
    report["blocking"] = len(meaning.blocking(report, guard.parse_allow(allow_change)))
    return report


def _rewrite(text, worst, is_html, is_tex, g):
    """One editor rewrite through the guard: every protected span is masked before
    the model call and spliced back byte for byte, and the findings summary is
    built from the masked text. With is_tex, every LaTeX math span is math, as
    the CLI reads a .tex file."""
    return editor.masked_rewrite(
        text, lambda m, mech: editor.rewrite_once(m, mech, worst, is_html), guard=g, tex=is_tex)


def do_fix(text, is_html=False, is_tex=False, allow_change=""):
    """Rewrite to the standard, self-gated on the detector and the meaning guard.
    Needs the LLM backend. An unknown allow_change kind raises ValueError."""
    g = guard.RewriteGuard(allow=allow_change)
    try:
        rewrite = _rewrite(text, [], is_html, is_tex, g)
    except guard.RewriteRefused as e:
        return {"ok": False, "error": editor.refusal_text(e), "note": _refused_note(e),
                "refused": _refusal(e)}
    except (RuntimeError, Exception) as e:  # noqa: BLE001
        return {"ok": False, "error": str(e), "note": _failure_note(e)}
    after = do_check(rewrite)
    return {"ok": True, "rewrite": rewrite,
            "findings_after": after["findings"], "gate_after": after["gate"],
            "meaning": g.log[-1]["report"]["verdict"],
            "note": "a suggestion; read it against the original before shipping",
            "does_not_prove": DOES_NOT_PROVE}


def _polish_scores(cur, is_tex):
    q = editor.quality_judge(editor.mask_math(cur)[0] if is_tex else cur)
    return q, {k: int(q.get(k, 0) or 0) for k in editor.QUALITIES}


def do_polish(text, bar=4, passes=3, is_html=False, is_tex=False, allow_change=""):
    """The quality loop, with the CLI's acceptance rule (editor.accept): a pass is
    kept only when no quality score falls and the gate does not go from ok to
    blocked. Every candidate passes the meaning guard. With is_tex no model call
    sees a formula. A refused rewrite stops the loop and keeps the last accepted
    text. An unknown allow_change kind raises ValueError."""
    g = guard.RewriteGuard(allow=allow_change)
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
                                is_html, is_tex, g)
            except guard.RewriteRefused as e:
                refused = e
                break
            c_chk = do_check(cand)
            cq, csc = _polish_scores(cand, is_tex)
            ok, _why = editor.accept(sc, csc, chk["gate"], c_chk["gate"], set(),
                                     {"ok": g.log[-1]["accepted"]})
            if not ok:
                break
            cur, chk, q, sc = cand, c_chk, cq, csc
    except (RuntimeError, Exception) as e:  # noqa: BLE001
        return {"ok": False, "error": str(e), "scorecard": scorecard,
                "note": _failure_note(e)}
    out = {"ok": True, "final_text": cur, "scorecard": scorecard,
           "note": "accepted on the reader's qualities and the gate, never on an outside score",
           "does_not_prove": DOES_NOT_PROVE}
    if refused is not None:
        out.update(refused=_refusal(refused),
                   note=f"a rewrite pass was refused ({_refused_note(refused)}); final_text "
                        "is the last accepted text")
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

    def compare(original: str, rewrite: str, freeze: Optional[List[str]] = None,
                allow_change: str = "") -> dict:
        return do_compare(original, rewrite, freeze, allow_change)

    def fix(text: str, is_html: bool = False, is_tex: bool = False,
            allow_change: str = "") -> dict:
        return do_fix(text, is_html, is_tex, allow_change)

    def polish(text: str, bar: int = 4, passes: int = 3, is_html: bool = False,
               is_tex: bool = False, allow_change: str = "") -> dict:
        return do_polish(text, bar, passes, is_html, is_tex, allow_change)

    # One description table serves both MCP servers (tool_text.TOOLS).
    for fn in (check, score, judge, compare, fix, polish):
        mcp.tool(_described(fn, fn.__name__))
    return mcp


if __name__ == "__main__":
    build_server().run()
