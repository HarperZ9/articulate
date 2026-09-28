#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.tool_text -- the words the tool says about itself, in one place.

Both MCP servers, the CLI and every machine-readable output read from this
table, so the product description, the tool descriptions and the does-not-prove
line cannot drift apart between surfaces. A test scans every string here.

Standard library only.
"""
from __future__ import annotations

PRODUCT = ("Local prose checks: named writing patterns, where they occur, and what "
           "each costs a reader.")

DOES_NOT_PROVE = ("These findings name prose patterns and where they occur. They do not "
                  "show who or what wrote the text, and no finding or count is a basis "
                  "for an accusation.")

_EDITOR = ("Auto uses negotiated sampling or returns a host edit plan. Explicit hosted "
           "backends can send text off the machine; backend none runs deterministic edits. "
           "When a plan is returned, follow its instructions and call edit_submit "
           "with the original text, rewrite or assessment, and plan_id.")

TOOLS = {
    "check": ("Check a passage for named prose patterns. Runs fully local with no "
              "network call. Returns each finding with its rule, tier, line and span, "
              "whether it blocks under the profile, per-rule counts, the gate "
              "(ok or blocked) with the count of blocking findings, density with an "
              "interval at 250 words or more, and passive-voice and adverb rates. The "
              "`clean` field is deprecated and leaves in package 0.7.0. " + DOES_NOT_PROVE),
    "score": ("Per-rule counts, density per 1,000 words with an exact interval (shown "
              "at 250 words or more), and passive-voice and adverb rates for a passage. "
              "Local, no network. " + DOES_NOT_PROVE),
    "judge": ("A skilled-editor read of the judgment-level failures a pattern check "
              "cannot see: confident emptiness, vague abstraction, uncommitted hedging, "
              "weak verbs, a buried point. Reports; does not rewrite. " + _EDITOR),
    "fix": ("Rewrite the text so its intended reader can follow it on one read, then "
            "re-check the rewrite and return it with the findings and gate after the "
            "rewrite. Offers a suggestion; the writer decides. With is_tex, LaTeX math is masked from the model and "
            "restored byte for byte. " + _EDITOR),
    "polish": ("The quality loop: rewrite, then score five qualities (concreteness, "
               "commitment, economy, rhythm read aloud, a restatable fact per paragraph) "
               "and keep a pass only when no score falls and the gate does not go from "
               "ok to blocked. The "
               "target is the reader, never an outside score. With is_tex, LaTeX math "
               "is masked before every model call. " + _EDITOR),
    "articulate.status": ("Liveness and identity of the articulate MCP server (name, "
                          "version, protocol). Network-free health probe."),
    "articulate.doctor": ("Readiness diagnostic: identity, the tools exposed, and which "
                          "of them need a model backend and which run local."),
}

TOOLS.update({
    "edit_plan": ("Prepare local findings, protected spans and instructions for the calling model. "
                  "Follow the instructions using masked_text and call edit_submit with the original "
                  "text, rewrite or assessment, and plan_id."),
    "edit_submit": ("Submit the original text and a host rewrite or assessment with its plan_id. "
                    "Articulate restores masks, guards protected spans, checks the result and "
                    "returns accepted text with a host receipt."),
    "articulate.doctor": ("Local readiness and tool identity, including optional editor backends "
                          "and this session's sampling capability."),
})
