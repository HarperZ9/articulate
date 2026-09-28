"""Shared MCP tool bodies and the optional FastMCP transport.

Detection and host planning/submission are local. Auto editing borrows the
connected caller's model only when sampling was advertised, otherwise it
returns a host plan. Explicit hosted backends can send text off this machine.
"""
import asyncio
from typing import Optional

from . import detector as core
from .tool_text import DOES_NOT_PROVE, TOOLS


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


def _edit(text, goal, **options):
    from .editing import run_edit
    result = run_edit(text, goal, context="mcp", **options)
    result["does_not_prove"] = DOES_NOT_PROVE + " " + result.get("does_not_prove", "")
    if result.get("status") != "host_edit_required":
        if goal == "judge":
            result["read"] = result.get("assessment", "")
        elif goal == "fix":
            result["rewrite"] = result["text"]
            # Detailed findings remain in remaining_findings; retain the public
            # state string that existing MCP callers read from findings_after.
            result["findings_after"] = (
                "has_findings" if any(f["tier"] in ("HIGH", "MEDIUM")
                                      for f in result["remaining_findings"])
                else "no_findings")
        else:
            result["final_text"] = result["text"]
    return result


def do_judge(text, backend=None, mode=None, profile=None, is_html=False,
             is_tex=False, **transport):
    return _edit(text, "judge", backend=backend, mode=mode, profile=profile,
                 is_html=is_html, is_tex=is_tex, **transport)


def do_fix(text, is_html=False, is_tex=False, backend=None, mode=None, profile=None,
           **transport):
    return _edit(text, "fix", backend=backend, mode=mode, profile=profile,
                 is_html=is_html, is_tex=is_tex, **transport)


def do_polish(text, bar=4, passes=3, is_html=False, is_tex=False, backend=None, mode=None,
              profile=None, **transport):
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

    def check(text: str) -> dict:
        """Report named prose patterns and the gate. Local, no network."""
        return do_check(text)

    def score(text: str) -> dict:
        """Return per-rule counts, density and structural rates. Local, no network."""
        return do_score(text)

    async def judge(text: str, ctx: Context, backend: Optional[str] = None,
                    mode: Optional[str] = None, profile: Optional[str] = None,
                    is_html: bool = False, is_tex: bool = False) -> dict:
        """Assess prose using negotiated sampling or return a host edit plan; explicit hosted backends send text off the machine.
        When a plan is returned, follow its instructions and call edit_submit with the original text, assessment and plan_id."""
        return await _fast_edit(ctx, text, "judge", backend=backend, mode=mode,
                                profile=profile, is_html=is_html, is_tex=is_tex)

    async def fix(text: str, ctx: Context, is_html: bool = False,
                  backend: Optional[str] = None, mode: Optional[str] = None,
                  profile: Optional[str] = None, is_tex: bool = False) -> dict:
        """Edit prose using negotiated sampling or return a host edit plan; explicit hosted backends send text off the machine.
        When a plan is returned, follow its instructions and call edit_submit with the original text, rewrite and plan_id."""
        return await _fast_edit(ctx, text, "fix", backend=backend, mode=mode,
                                profile=profile, is_html=is_html, is_tex=is_tex)

    async def polish(text: str, ctx: Context, bar: int = 4, passes: int = 3,
                     is_html: bool = False, backend: Optional[str] = None,
                     mode: Optional[str] = None, profile: Optional[str] = None,
                     is_tex: bool = False) -> dict:
        """Polish prose with meaning and regression guards or return a host plan; explicit hosted backends send text off the machine.
        When a plan is returned, follow its instructions and call edit_submit with the original text, rewrite, plan_id and assessed scores."""
        return await _fast_edit(ctx, text, "polish", backend=backend, mode=mode,
                                profile=profile, is_html=is_html, is_tex=is_tex,
                                bar=bar, passes=passes)

    def edit_plan(text: str, mode: Optional[str] = None, profile: Optional[str] = None,
                  goal: str = "fix", is_html: bool = False, is_tex: bool = False) -> dict:
        """Prepare local findings, protected spans and exact instructions for the calling model without a second account.
        Follow the instructions using masked_text and call edit_submit with the original text, rewrite or assessment, and plan_id."""
        return do_edit_plan(text, mode, profile, goal, is_html, is_tex)

    def edit_submit(text: str, rewrite: str, plan_id: str,
                    scores: Optional[dict] = None, model: Optional[str] = None) -> dict:
        """Submit the original text and a host rewrite or assessment using the plan_id from edit_plan.
        Articulate restores masks, guards protected spans, checks the result and returns accepted text with a host receipt."""
        return do_edit_submit(text, rewrite, plan_id, scores, model)

    for fn in (check, score, judge, fix, polish, edit_plan, edit_submit):
        fn.__doc__ = TOOLS[fn.__name__]
        mcp.tool(fn)
    return mcp


if __name__ == "__main__":
    build_server().run()
