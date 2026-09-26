#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.provenance -- the fixed words a writer's own declarations map to.

Everything here repeats what a writer declared about their own process: the
IPTC digital source type codes and labels, the assistance verbs, the input
methods, the review roles and the CRediT contributor roles. The tool never
infers origin; it may repeat origin a writer declares, and only through this
table. The origin-claim test exempts this module and no other.

IPTC codes and labels: IPTC NewsCodes digital source type vocabulary, copy
retrieved 26 September 2026 from cv.iptc.org/newscodes/digitalsourcetype.
minorHumanEdits was retired on 2024-09-17 and is never emitted.
CRediT roles: ANSI/NISO Z39.104-2022, 14 roles.

Standard library only.
"""
from __future__ import annotations

IPTC_BASE = "http://cv.iptc.org/newscodes/digitalsourcetype/"
IPTC = {
    "digitalCreation": "Digital creation",
    "humanEdits": "Human-edited media",
    "algorithmicallyEnhanced": "Algorithmically-altered media",
    "compositeWithTrainedAlgorithmicMedia": "Edited using Generative AI",
    "trainedAlgorithmicMedia": "Created using Generative AI",
}
RETIRED_IPTC = frozenset({"minorHumanEdits", "softwareImage", "digitalArt"})

# What the record says, and the IPTC code it maps to (PLAN section 5.5).
SOURCE_TYPE = {
    "written": "digitalCreation",            # typed or handwritten, no tool
    "human-edit": "humanEdits",               # later drafts by people, no generative tool
    "deterministic-fix": "algorithmicallyEnhanced",
    "edited": "compositeWithTrainedAlgorithmicMedia",   # a model edited the writer's text
    "generated": "trainedAlgorithmicMedia",
    "drafted": "trainedAlgorithmicMedia",
}
# A model translation of the writer's own draft: the writer picks one of these.
TRANSLATION_CHOICES = ("compositeWithTrainedAlgorithmicMedia", "trainedAlgorithmicMedia")

ASSIST_VERBS = ("generated", "drafted", "edited", "translated")
INPUT_METHODS = ("dictation", "handwriting-then-typed", "screen-reader", "switch-access",
                 "drafted-in-another-language")
REVIEW_ROLES = ("tutor", "supervisor", "peer", "editor")

CREDIT_ROLES = (
    "Conceptualization", "Data curation", "Formal analysis", "Funding acquisition",
    "Investigation", "Methodology", "Project administration", "Resources", "Software",
    "Supervision", "Validation", "Visualization", "Writing - original draft",
    "Writing - review and editing",
)

# Names a contributor file may not list as an author: model products and tools.
NOT_A_PERSON = ("claude", "gpt", "chatgpt", "gemini", "copilot", "llama", "mistral",
                "grok", "articulate", "openai", "anthropic", "language model", " ai")

# Statement wording that asserts no tool was used. Refused whenever an
# assistance entry exists.
NO_TOOL_CLAIMS = ("no ai", "without ai", "no generative", "no artificial intelligence",
                  "no tools were used", "entirely human", "no assistance")


# Headings of the disclosure statement. The credit section names the people a
# writer declares, in the CRediT vocabulary.
STATEMENT_TITLE = "Statement of tool use and authorship"
CREDIT_HEADING = "Authorship credit (CRediT)"
DISCLOSE_HELP = "a statement of tool use and authorship credit"
NOT_A_PERSON_REASON = "cannot hold an authorship role; only people can"


def iptc_uri(code):
    if code in RETIRED_IPTC or code not in IPTC:
        raise ValueError(f"not a current IPTC digital source type: {code!r}")
    return IPTC_BASE + code
