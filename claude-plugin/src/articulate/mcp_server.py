"""Shared MCP tool bodies and the optional FastMCP transport.

Detection and host planning/submission are local. Auto editing borrows the
connected caller's model only when sampling was advertised, otherwise it
returns a host plan. Explicit hosted backends can send text off this machine.
"""
import asyncio
import json
from typing import Optional

from . import detector as core
from .tool_meta import fastmcp_options, offline
from .tool_text import description


HITS_BUDGET = 30_000


def _within_budget(hits, budget=HITS_BUDGET):
    kept, used = [], 0
    for hit in hits:
        used += len(json.dumps(hit, separators=(",", ":"), ensure_ascii=False)) + 1
        if used > budget:
            break
        kept.append(hit)
    return kept


def do_check(text, max_hits=None):
    """Detect prose/AI tells with span records. Local, no network."""
    if max_hits is not None and (type(max_hits) is not int or not 0 <= max_hits <= 1000):
        raise ValueError("max_hits must be a whole number from 0 to 1000")
    r = core.check_text(text)
    hits = sorted(r["high"] + r["medium"], key=lambda h: h["start"])
    shown = hits if max_hits is None else _within_budget(hits[:max_hits])
    out = {
        "clean": r["clean"],
        "verdict": "clean" if r["clean"] else "flagged",
        "texture_score": r["texture_score"],
        "elevated": r["elevated"],
        "hits": shown,
        "advisory_count": len(r["low"]),
        "cadence": r["cadence"],
    }
    if len(shown) < len(hits):
        out["hits_omitted"] = len(hits) - len(shown)
    return out


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


def _edit(text, goal, **options):
    if offline():
        backend = options.get("backend")
        if backend not in (None, "auto", "host", "none"):
            return {"ok": False, "error": "%s backend %r is not available in local-only mode" % (goal, backend),
                    "note": "This local-only server allows host plans and backend none only."}
        from .host_edit import edit_plan, deterministic_edit
        bar, passes = options.get("bar", 4), options.get("passes", 3)
        if not 1 <= bar <= 5 or passes < 1:
            raise ValueError("bar must be 1-5 and passes must be positive")
        settings = {key: options[key] for key in ("mode", "profile", "is_html", "is_tex") if key in options}
        result = (deterministic_edit if backend == "none" else edit_plan)(text, goal=goal, **settings)
        if goal == "polish":
            result.update(scores=None, quality_met=False)
        return result
    try:
        from .editing import run_edit
    except ImportError:
        # The Claude plugin carries only the local tools and leaves editing out.
        return {"ok": False, "error": "%s needs a model backend, which this build does not include" % goal,
                "note": "Use the local tool set: host plans and backend none."}
    return run_edit(text, goal, context="mcp", **options)


def do_judge(text, backend=None, mode=None, profile=None, is_html=False,
             is_tex=False, **transport):
    return _edit(text, "judge", backend=backend, mode=mode, profile=profile,
                 is_html=is_html, is_tex=is_tex, **transport)


def do_fix(text, is_html=False, backend=None, mode=None, profile=None,
           is_tex=False, **transport):
    return _edit(text, "fix", backend=backend, mode=mode, profile=profile,
                 is_html=is_html, is_tex=is_tex, **transport)


def do_polish(text, bar=4, passes=3, is_html=False, backend=None, mode=None,
              profile=None, is_tex=False, **transport):
    return _edit(text, "polish", bar=bar, passes=passes, backend=backend,
                 mode=mode, profile=profile, is_html=is_html, is_tex=is_tex,
                 **transport)


def do_edit_plan(text, mode=None, profile=None, goal="fix", is_html=False, is_tex=False):
    from .host_edit import edit_plan
    return edit_plan(text, mode=mode, profile=profile, goal=goal,
                     is_html=is_html, is_tex=is_tex)


def do_edit_submit(text, rewrite, plan_id, scores=None, model=None, author_text=None):
    from .host_edit import edit_submit, plan_settings
    origin = "host-supplied" if author_text is not None else None
    if plan_settings(text, plan_id).get("voice_profile_sha256"):
        # A voice apply plan: check the bound profile is unchanged and report its counts.
        from .voice_apply import submit
        return submit(text, rewrite, plan_id, scores=scores, model=model,
                      author_text=author_text, author_text_origin=origin)
    return edit_submit(text, rewrite, plan_id, scores=scores, model=model,
                       author_text=author_text, author_text_origin=origin)


async def _fast_edit(ctx, text, goal, **options):
    """Bridge synchronous editing to the negotiated SDK session without an account."""
    from mcp.types import ClientCapabilities, SamplingCapability, SamplingMessage, TextContent
    loop = asyncio.get_running_loop()
    try:
        session = ctx.session
        advertised = session.check_client_capability(ClientCapabilities(sampling=SamplingCapability()))
    except (AttributeError, RuntimeError):
        session, advertised = None, False

    def sampling(instructions, passage, timeout):
        async def complete():
            result = await session.create_message(
                messages=[SamplingMessage(role="user", content=TextContent(type="text", text=passage))],
                system_prompt=instructions, max_tokens=4096, include_context="none")
            return result.model_dump(by_alias=True)
        future = asyncio.run_coroutine_threadsafe(complete(), loop)
        try:
            return future.result(timeout=timeout)
        except TimeoutError:
            future.cancel()
            raise RuntimeError("sampling timed out") from None
        except Exception:
            raise RuntimeError("sampling request failed") from None

    return await asyncio.to_thread(_edit, text, goal, sampling=sampling if advertised else None,
                                   sampling_advertised=advertised, **options)


def build_server():
    from fastmcp import FastMCP, Context
    mcp = FastMCP("articulate")

    @mcp.tool(description=description("check"), **fastmcp_options("check"))
    def check(text: str, max_hits: int = 50) -> dict:
        """Detect prose tells and return findings with cadence stats. Local, no network."""
        return do_check(text, max_hits)

    @mcp.tool(description=description("score"), **fastmcp_options("score"))
    def score(text: str) -> dict:
        """Return machine-texture and structural rates. Local, no network."""
        return do_score(text)

    @mcp.tool(description=description("judge"), **fastmcp_options("judge"))
    async def judge(text: str, ctx: Context, backend: Optional[str] = None,
                    mode: Optional[str] = None, profile: Optional[str] = None,
                    is_html: bool = False, is_tex: bool = False) -> dict:
        """Assess prose using negotiated sampling or return a host edit plan; explicit hosted backends send text off the machine.
        When a plan is returned, follow its instructions and call edit_submit with the original text, assessment and plan_id."""
        return await _fast_edit(ctx, text, "judge", backend=backend, mode=mode,
                                profile=profile, is_html=is_html, is_tex=is_tex)

    @mcp.tool(description=description("fix"), **fastmcp_options("fix"))
    async def fix(text: str, ctx: Context, is_html: bool = False,
                  backend: Optional[str] = None, mode: Optional[str] = None,
                  profile: Optional[str] = None, is_tex: bool = False) -> dict:
        """Edit prose using negotiated sampling or return a host edit plan; explicit hosted backends send text off the machine.
        When a plan is returned, follow its instructions and call edit_submit with the original text, rewrite and plan_id."""
        return await _fast_edit(ctx, text, "fix", backend=backend, mode=mode,
                                profile=profile, is_html=is_html, is_tex=is_tex)

    @mcp.tool(description=description("polish"), **fastmcp_options("polish"))
    async def polish(text: str, ctx: Context, bar: int = 4, passes: int = 3,
                     is_html: bool = False, backend: Optional[str] = None,
                     mode: Optional[str] = None, profile: Optional[str] = None,
                     is_tex: bool = False) -> dict:
        """Polish prose with meaning and regression guards or return a host plan; explicit hosted backends send text off the machine.
        When a plan is returned, follow its instructions and call edit_submit with the original text, rewrite, plan_id and assessed scores."""
        return await _fast_edit(ctx, text, "polish", backend=backend, mode=mode,
                                profile=profile, is_html=is_html, is_tex=is_tex,
                                bar=bar, passes=passes)

    @mcp.tool(description=description("edit_plan"), **fastmcp_options("edit_plan"))
    def edit_plan(text: str, mode: Optional[str] = None, profile: Optional[str] = None,
                  goal: str = "fix", is_html: bool = False, is_tex: bool = False) -> dict:
        """Prepare local findings, protected spans and exact instructions for the calling model without a second account.
        Follow the instructions using masked_text and call edit_submit with the original text, rewrite or assessment, and plan_id."""
        return do_edit_plan(text, mode, profile, goal, is_html, is_tex)

    @mcp.tool(description=description("edit_submit"), **fastmcp_options("edit_submit"))
    def edit_submit(text: str, rewrite: str, plan_id: str, scores: Optional[dict] = None,
                    model: Optional[str] = None, author_text: Optional[str] = None) -> dict:
        """Submit the original text and a host rewrite or assessment using the plan_id from edit_plan.
        Articulate restores masks, guards protected spans, checks the result and returns accepted text with a host receipt."""
        return do_edit_submit(text, rewrite, plan_id, scores, model, author_text)

    from .mcp_local_tools import register
    register(mcp)
    return mcp


if __name__ == "__main__":
    build_server().run()
