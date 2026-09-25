#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
articulate_mcp.py  --  MCP server for Articulate.

Exposes the local writing detector and the editor layer over the Model Context
Protocol (stdio), so any MCP-speaking agent host or editor can call Articulate
without a bespoke integration.

Privacy posture (the reason MCP is the first surface): the detection tools
(check, score, passes) run entirely local, with no network call, ever. The
editor tools (judge, fix, polish) need an LLM backend; today the only one is the
`claude` CLI, which sends the text to a hosted Anthropic model. They return a
clean "unavailable" result when the backend cannot be reached, and never fail the
call.

Run:  python articulate_mcp.py           (stdio; the host launches it)
Register in an MCP host (e.g. Claude Code .mcp.json / settings):
  {"mcpServers": {"articulate": {"command": "python",
     "args": ["C:/Users/Zain/.claude/hooks/articulate_mcp.py"]}}}

stdout carries the MCP protocol; all logging goes to stderr.
"""
import os
import tempfile

from . import detector as core
from . import editor

HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND_NOTE = "the editor layer needs the claude CLI, which sends the text to a hosted model"


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
    """Detect prose/AI tells with span records. Local, no network."""
    r = core.check_text(text)
    hits = sorted(r["high"] + r["medium"], key=lambda h: h["start"])
    return {
        "clean": r["clean"],
        "verdict": "clean" if r["clean"] else "flagged",
        "texture_score": r["texture_score"],
        "elevated": r["elevated"],
        "hits": hits,
        "advisory_count": len(r["low"]),
        "cadence": r["cadence"],
    }


def do_score(text):
    """Graded machine-texture score and structural rates. Local, no network."""
    r = core.check_text(text)
    cad = r["cadence"]
    return {
        "texture_score": r["texture_score"],
        "elevated": r["elevated"],
        "hard_hits": len(r["high"]) + len(r["medium"]),
        "advisories": len(r["low"]),
        "passive_rate": cad["passive_rate"],
        "adverb_rate": cad["adverb_rate"],
        "uniform_cadence": cad["uniform"],
        "words": cad["words"],
    }


def do_judge(text):
    """Skilled-editor read of judgment-level failures. Needs the LLM backend."""
    _, mech = _mech_summary(text)
    instr = (
        "You are a demanding copyeditor. Read the text piped on stdin and report "
        "only its judgment-level quality failures: confident emptiness (a fluent "
        "sentence with no fact a reader could restate), vague abstraction where a "
        "concrete term exists, hedging that never commits, a metaphor standing in "
        "for a literal term, a buried point, weak verbs, hidden-actor passive. "
        "Quote each offender, name the failure, and say in one line what a skilled "
        "writer would do. If the prose is strong, say so and stop.\n\n"
        f"The mechanical detector reports:\n{mech}"
    )
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
    except (RuntimeError, Exception) as e:  # noqa: BLE001
        return {"ok": False, "error": str(e),
                "note": _BACKEND_NOTE}
    after = do_check(rewrite)
    return {"ok": True, "rewrite": rewrite,
            "clean_after": after["clean"], "texture_after": after["texture_score"],
            "note": "a suggestion; read it against the original before shipping"}


def do_polish(text, bar=4, passes=3, is_html=False, is_tex=False):
    """Quality loop: rewrite and re-score five qualities until every one clears bar."""
    qualities = ("concreteness", "commitment", "economy", "rhythm", "restatable")
    scorecard = []
    cur = text
    try:
        for attempt in range(passes + 1):
            chk = do_check(cur)
            q = editor.quality_judge(cur)
            sc = {k: int(q.get(k, 0) or 0) for k in qualities}
            scorecard.append({"pass": attempt, "scores": sc,
                              "mechanical_clean": chk["clean"], "verdict": q.get("verdict")})
            if chk["clean"] and sc and min(sc.values()) >= bar:
                break
            if attempt == passes:
                break
            cur = _rewrite(cur, q.get("worst", []), is_html, is_tex)
    except (RuntimeError, Exception) as e:  # noqa: BLE001
        return {"ok": False, "error": str(e), "scorecard": scorecard,
                "note": _BACKEND_NOTE}
    return {"ok": True, "final_text": cur, "scorecard": scorecard,
            "note": "gated on writing quality, never on a detector score"}


def build_server():
    from fastmcp import FastMCP
    mcp = FastMCP("articulate")

    @mcp.tool
    def check(text: str) -> dict:
        """Detect AI and prose tells in text. Runs fully local with no network call.
        Returns each finding with its line, tier (HIGH/MEDIUM), category and snippet,
        a clean/flagged device gate, a 0-100 machine-texture score, and cadence stats."""
        return do_check(text)

    @mcp.tool
    def score(text: str) -> dict:
        """Return the graded 0-100 machine-texture score plus passive-voice and adverb
        rates and cadence flags for a passage. Local, no network."""
        return do_score(text)

    @mcp.tool
    def judge(text: str) -> dict:
        """A skilled-editor read of the judgment-level failures a regex cannot see:
        confident emptiness, vague abstraction, uncommitted hedging, weak verbs, a
        buried point. Flags, does not rewrite. Needs an LLM backend."""
        return do_judge(text)

    @mcp.tool
    def fix(text: str, is_html: bool = False, is_tex: bool = False) -> dict:
        """Rewrite the text to the plain-writing standard and self-check the rewrite
        against the detector so it introduces no new tell. Offers a suggestion; the
        human decides. With is_tex, LaTeX math is masked from the model and restored
        byte for byte. Needs an LLM backend."""
        return do_fix(text, is_html, is_tex)

    @mcp.tool
    def polish(text: str, bar: int = 4, passes: int = 3, is_html: bool = False,
               is_tex: bool = False) -> dict:
        """The quality loop: rewrite, then score five qualities (concreteness,
        commitment, economy, rhythm, restatable-fact-per-paragraph) and iterate until
        every one clears `bar` (1-5) and the detector is clean. Gated on writing
        quality, never on a detector score. With is_tex, LaTeX math is masked from
        the model and restored byte for byte. Needs an LLM backend."""
        return do_polish(text, bar, passes, is_html, is_tex)

    return mcp


if __name__ == "__main__":
    build_server().run()
