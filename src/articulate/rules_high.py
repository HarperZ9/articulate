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
    # --- named filler intensifiers (house pack) ---------------------------- #
    # "Yours truly" and "truly yours" close a letter; they are never an intensifier.
    ("filler-intensifier", "genuinely / really / truly / actually",
     re.compile(r"\b(?:genuinely|really|actually|(?<!yours )truly(?!\s+yours))\b", re.I)),
    # --- named corporate-register verbs (house pack) ---------------------- #
    ("corporate-verb", "leverage / underscore (as corporate verb)",
     re.compile(r"\b(?:leverage[sd]?|leveraging|underscore[sd]?|underscoring)\b", re.I)),
    # --- an affirmation that hands over a deliverable --------------------- #
    # A bare "Of course," or "Absolutely." is ordinary spoken English and is a LOW
    # advisory (rules_low). This rule needs the delivery line that follows it in
    # a chat reply: "Certainly! Here is your essay:".
    ("assistant-residue", "chat reply opener that hands over a deliverable",
     re.compile(r"(?i)(?:^|(?<=[.!?]\s))\s*(?:certainly|absolutely|of course|sure thing|great question|"
                r"good question|happy to help)[!,.]\s*(?:here(?:'s|\s+is|\s+are)\b|"
                r"below\s+(?:is|are)\b|i'?(?:ve|\s+have)\s+(?:written|drafted|prepared|"
                r"put\s+together|created|revised|rewritten)\b|i'?d\s+be\s+happy\s+to\b)")),
    # --- vague-change blog intro (house pack) ----------------------------- #
    ("blog-tell", "vague-change intro (as X continues to evolve)",
     re.compile(r"\bas (?:the )?[\w-]+(?:\s+\w+){0,2}\s+continues to "
                r"(?:evolve|grow|change|develop|advance|expand)\b", re.I)),
    # --- first-person self-identification of a chat tool ------------------- #
    # First person only. "as an AI system" in a quoted law or a policy essay is a
    # third-person description and raises nothing.
    ("assistant-residue", "chat tool self-identification / knowledge-cutoff line",
     re.compile(r"(?i)\bas\s+(?:an\s+ai(?:\s+language\s+model)?|a\s+(?:large\s+)?language"
                r"\s+model|an?\s+(?:helpful\s+)?(?:ai\s+)?assistant),?\s+i\b"
                r"|\bi'?m\s+(?:just\s+|only\s+)?an?\s+ai\b"
                r"|\bas\s+of\s+my\s+(?:last\s+)?(?:knowledge|training)\s+(?:update|cut[- ]?off|cutoff)\b"
                r"|\bmy\s+(?:training\s+data|knowledge\s+cut[- ]?off|knowledge\s+cutoff)\b"
                r"|\bi\s+(?:do\s+not|don'?t)\s+have\s+(?:access\s+to\s+)?real[- ]?time\b")),
    # --- leaked chat interface / citation markup tokens -------------------- #
    # Literal substrings chat interfaces emit. Case-sensitive on purpose: these
    # are exact interface tokens, not words.
    ("assistant-residue", "leaked chat interface / citation markup token",
     re.compile(r"contentReference|oaicite|turn0search|turn0news|citeturn"
                r"|grok_render_citation_card_json|ppl-ai-file-upload"
                r"|:::writing|\[oai_citation")),
    # --- zero-width space or word joiner inside Latin text ----------------- #
    # Both neighbours must be Latin letters, digits or ASCII punctuation. Thai,
    # Khmer, Lao and Myanmar text marks word boundaries with U+200B; there it is
    # a LOW advisory (rules_low). ZWNJ (U+200C) and ZWJ are never matched.
    ("invisible-unicode", "zero-width character inside Latin text",
     re.compile("(?<=[A-Za-z0-9!-/:-@\\[-`{-~])[\u200b\u2060](?=[A-Za-z0-9!-/:-@\\[-`{-~])")),
]
