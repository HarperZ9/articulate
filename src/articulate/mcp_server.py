"""Shared MCP tool bodies and the optional FastMCP transport.

Detection and host planning/submission are local. Auto editing borrows the
connected caller's model only when sampling was advertised, otherwise it
returns a host plan. Explicit hosted backends can send text off this machine.
"""
import asyncio
from typing import Optional

from . import detector as core


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


def _edit(text, goal, **options):
    from .editing import run_edit
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


def do_edit_submit(text, rewrite, plan_id, scores=None, model=None):
    from .host_edit import edit_submit
    return edit_submit(text, rewrite, plan_id, scores=scores, model=model)


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

    @mcp.tool
    def check(text: str) -> dict:
        """Detect prose tells and return findings with cadence stats. Local, no network."""
        return do_check(text)

    @mcp.tool
    def score(text: str) -> dict:
        """Return machine-texture and structural rates. Local, no network."""
        return do_score(text)

    @mcp.tool
    async def judge(text: str, ctx: Context, backend: Optional[str] = None,
                    mode: Optional[str] = None, profile: Optional[str] = None,
                    is_html: bool = False, is_tex: bool = False) -> dict:
        """Assess prose using negotiated sampling or return a host edit plan; explicit hosted backends send text off the machine.
        When a plan is returned, follow its instructions and call edit_submit with the original text, assessment and plan_id."""
        return await _fast_edit(ctx, text, "judge", backend=backend, mode=mode,
                                profile=profile, is_html=is_html, is_tex=is_tex)

    @mcp.tool
    async def fix(text: str, ctx: Context, is_html: bool = False,
                  backend: Optional[str] = None, mode: Optional[str] = None,
                  profile: Optional[str] = None, is_tex: bool = False) -> dict:
        """Edit prose using negotiated sampling or return a host edit plan; explicit hosted backends send text off the machine.
        When a plan is returned, follow its instructions and call edit_submit with the original text, rewrite and plan_id."""
        return await _fast_edit(ctx, text, "fix", backend=backend, mode=mode,
                                profile=profile, is_html=is_html, is_tex=is_tex)

    @mcp.tool
    async def polish(text: str, ctx: Context, bar: int = 4, passes: int = 3,
                     is_html: bool = False, backend: Optional[str] = None,
                     mode: Optional[str] = None, profile: Optional[str] = None,
                     is_tex: bool = False) -> dict:
        """Polish prose with meaning and regression guards or return a host plan; explicit hosted backends send text off the machine.
        When a plan is returned, follow its instructions and call edit_submit with the original text, rewrite, plan_id and assessed scores."""
        return await _fast_edit(ctx, text, "polish", backend=backend, mode=mode,
                                profile=profile, is_html=is_html, is_tex=is_tex,
                                bar=bar, passes=passes)

    @mcp.tool
    def edit_plan(text: str, mode: Optional[str] = None, profile: Optional[str] = None,
                  goal: str = "fix", is_html: bool = False, is_tex: bool = False) -> dict:
        """Prepare local findings, protected spans and exact instructions for the calling model without a second account.
        Follow the instructions using masked_text and call edit_submit with the original text, rewrite or assessment, and plan_id."""
        return do_edit_plan(text, mode, profile, goal, is_html, is_tex)

    @mcp.tool
    def edit_submit(text: str, rewrite: str, plan_id: str,
                    scores: Optional[dict] = None, model: Optional[str] = None) -> dict:
        """Submit the original text and a host rewrite or assessment using the plan_id from edit_plan.
        Articulate restores masks, guards protected spans, checks the result and returns accepted text with a host receipt."""
        return do_edit_submit(text, rewrite, plan_id, scores, model)

    return mcp


if __name__ == "__main__":
    build_server().run()
