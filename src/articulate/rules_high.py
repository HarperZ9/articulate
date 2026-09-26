#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.rules_high -- the HIGH tier: devices a gate blocks on sight.

Each entry is (category, label, compiled regex), applied per prose line after
markup, code spans and URLs are masked. Standard library only.
"""
import re

HIGH = [
    # --- banned rhetorical devices --------------------------------------- #
    ("antithesis",   "not X but Y",
     re.compile(r"\bnot\b(?!\s+help\s+but\b)[^.\n;:]{0,90}?\bbut\b", re.I)),
    ("antithesis",   "not only ... but (also)",
     re.compile(r"\bnot only\b[^.\n]{0,90}?\bbut\b", re.I)),
    ("antithesis",   "it's not just X, it's Y",
     re.compile(r"\b(?:it'?s|its|is|isn'?t|was|it is)\s+not\s+just\b[^.\n]{0,80}?,?\s*\b(?:it'?s|its|it is|they'?re|but)\b", re.I)),
    ("corrective-negation", ", not Y",
     re.compile(r",\s+not\s+(?:a|an|the|by|to|of|from|because|only|merely|about|whether|that|its|his|her|their|our|your|my|an?other|some|simply|just)\b", re.I)),
    ("antithesis",   "is not X, it is Y",
     re.compile(r"\bis not\b[^.\n]{0,60}?\b(?:it is|they are|but rather)\b", re.I)),
    ("substitution", "instead / rather than",
     re.compile(r"\b(?:instead of|instead,|instead\b|rather than)\b", re.I)),
    ("substitution", "the opposite",
     re.compile(r"\bthe opposite\b", re.I)),
    ("negative-parallel", "never ... always",
     re.compile(r"\bnever\b[^.\n]{0,60}?\balways\b", re.I)),
    # --- punctuation ------------------------------------------------------- #
    ("em-dash",      "em-dash (\u2014)",
     re.compile(r"\u2014")),
    ("em-dash",      "spaced en-dash used as em",
     re.compile(r"\s\u2013\s")),
    # --- named filler intensifiers ---------------------------------------- #
    ("filler-intensifier", "genuinely / really / truly / actually",
     re.compile(r"\b(?:genuinely|really|truly|actually)\b", re.I)),
    # --- named corporate-register verbs ---------------------------------- #
    ("corporate-verb", "leverage / underscore / reflect (as corporate verb)",
     re.compile(r"\b(?:leverage[sd]?|leveraging|underscore[sd]?|underscoring)\b", re.I)),
    # --- deletable padding circumlocutions (from research spec #1) --------- #
    ("wordiness", "deletable padding circumlocution",
     re.compile(r"\b(?:in order to|due to the fact that|for the purpose of|"
                r"at this point in time|with regard to|with respect to|"
                r"a wide range of|in the process of|in a timely manner|"
                r"it should be noted that)\b", re.I)),
    # --- assistant-affirmation opener bleeding into prose (spec #4) -------- #
    # Line-initial affirmation plus punctuation is near-exclusive to assistant
    # residue. The word set is extended over the original; "sure" stays as "sure
    # thing" only (bare "Sure," is ordinary human chat).
    ("assistant-residue", "assistant affirmation opener",
     re.compile(r"(?im)^\s*(?:certainly|absolutely|great question|good question|"
                r"excellent question|excellent point|fantastic question|sure thing|"
                r"of course|happy to help|i'?d be happy to)[!,.]")),
    # --- vague-change blog intro (spec #7) -------------------------------- #
    ("blog-tell", "vague-change intro (as X continues to evolve)",
     re.compile(r"\bas (?:the )?[\w-]+(?:\s+\w+){0,2}\s+continues to "
                r"(?:evolve|grow|change|develop|advance|expand)\b", re.I)),
    # --- AI self-identification / knowledge-cutoff disclaimer ------------- #
    # Near-zero outside text that quotes or discusses AI systems. A hard, clean
    # tell of unedited model output leaking its own framing.
    ("assistant-residue", "AI self-identification / knowledge-cutoff disclaimer",
     re.compile(r"(?i)\bas\s+(?:an\s+ai(?:\s+language\s+model)?|a\s+(?:large\s+)?language\s+model)\b"
                r"|\bi'?m\s+(?:just\s+|only\s+)?an?\s+ai\b"
                r"|\bas\s+a\s+(?:helpful\s+)?(?:ai\s+)?assistant\b"
                r"|\bas\s+of\s+my\s+(?:last\s+)?(?:knowledge|training)\s+(?:update|cut[- ]?off|cutoff)\b"
                r"|\bmy\s+(?:training\s+data|knowledge\s+cut[- ]?off|knowledge\s+cutoff)\b"
                r"|\bi\s+(?:do\s+not|don'?t)\s+have\s+(?:access\s+to\s+)?real[- ]?time\b")),
    # --- leaked assistant / citation markup tokens (copy-paste leakage) --- #
    # Literal substrings emitted by chat UIs. Essentially never in natural prose.
    # Case-sensitive on purpose: these are exact machine tokens, not words.
    ("assistant-residue", "leaked assistant/citation markup token",
     re.compile(r"contentReference|oaicite|turn0search|turn0news|citeturn"
                r"|grok_render_citation_card_json|ppl-ai-file-upload"
                r"|:::writing|\[oai_citation")),
    # --- invisible-unicode artifacts (zero-width space / word joiner) ----- #
    # Zero-width space (U+200B) and word joiner (U+2060) in prose are near-
    # unambiguous machine artifacts. NBSP and ZWJ (emoji sequences) are excluded
    # because they have legitimate typographic and emoji uses.
    ("invisible-unicode", "zero-width / word-joiner artifact",
     re.compile("[​⁠]")),
]
