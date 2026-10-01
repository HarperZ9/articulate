"""Shared descriptions for the 0.5.1 MCP tools."""
from .tool_meta import EDITORS, offline

DOES_NOT_PROVE = ("These findings name prose patterns and where they occur. They "
                  "do not establish factual correctness, quality, or who or what wrote "
                  "the text, and no finding or count is a basis for an accusation.")

_EDIT = ("Use negotiated sampling or return a host plan. Explicit backends may send "
         "text to a hosted model; backend none is deterministic. It edits none of your "
         "files. When a plan returns, follow its instructions and call edit_submit "
         "with the original text, rewrite or assessment, and plan_id.")
_LOCAL_EDIT = ("Local, no network. Default, auto and host return a host edit plan; "
               "backend none applies deterministic edits. Other backends, including "
               "sampling, are refused. It edits none of your files. Follow the plan "
               "instructions, then call edit_submit with the original text, rewrite "
               "or assessment, and plan_id.")
TOOLS = {
    "check": ("Check a passage for named prose patterns. Local, no network. Returns "
              "up to max_hits HIGH and MEDIUM findings (50 by default), with span "
              "records capped at about 30,000 characters. The clean/flagged verdict, "
              "texture score, advisory count and cadence cover the full text. " + DOES_NOT_PROVE),
    "score": ("Return the 0-100 machine-texture score, finding counts, passive-voice "
              "and adverb rates, and cadence flags. Local, no network. " + DOES_NOT_PROVE),
    "judge": "Assess prose. " + _EDIT,
    "fix": "Suggest a rewrite. " + _EDIT,
    "polish": "Polish prose with meaning and regression guards. " + _EDIT,
    "edit_plan": ("Prepare local findings, protected spans and instructions for the "
                  "calling model. No network call; it edits none of your files. Use "
                  "masked_text to write the rewrite or assessment, then call edit_submit "
                  "with the original text, result, and plan_id."),
    "edit_submit": ("Check a local host rewrite or assessment against its edit_plan. "
                    "Restores masks, guards protected spans and returns checked text "
                    "with a host receipt. No network call; it edits none of your files. "
                    "Protected-span checks do not establish semantic equivalence."),
    "articulate.status": "Local server identity and liveness. No network call.",
    "articulate.doctor": ("Local readiness report: version, tools, optional backends "
                          "and session sampling capability. No network call."),
}


def description(name, environ=None):
    return _LOCAL_EDIT if name in EDITORS and offline(environ) else TOOLS[name]
