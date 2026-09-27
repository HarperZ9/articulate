#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.rules_low -- advisory tables, the fiction lexicon and the
instruction-injection table.

None of these gate under a default profile. INJECTION never enters check_text.
Standard library only.
"""
import re

# Abstract-metaphor jargon (house pack): a metaphor where a literal term exists.
# Several are also legitimate terms of art in a technical paper
# ("substrate", "load-bearing"); when a use is genuinely load-bearing, keep that
# one with a `writing-allow:` line rather than by suppressing the whole category.
REGISTER_JARGON = [
    ("register-jargon", "abstract-metaphor jargon",
     re.compile(r"\b(?:load[- ]bearing|substrates?|first[- ]class|north star|"
                r"table stakes|surface area|under the hood|out[- ]of[- ]the[- ]box|"
                r"crux|moving parts|at scale|paradigm(?: shift)?|in the weeds|"
                r"bird'?s[- ]eye view|10[,]?000[- ]foot view|"
                r"boils? down to|comes? down to|single source of truth)\b", re.I)),
]

# Formatting heuristics that fire on innocent prose too. Reported as advisories.
LOW = [
    ("rule-of-three", "possible triad (X, Y, and Z)",
     re.compile(r"\b\w+,\s+\w+,\s+and\s+\w+\b")),
    ("bold-lead", "bold list-item lead-in (**Term** :)",
     re.compile(r"^\s*(?:[-*+]|\d+\.)\s+\*\*[^*\n]{1,60}\*\*\s*[:\-\u2013\u2014]")),
    ("closer-question", "rhetorical question",
     re.compile(r"^\s*(?:so |but |and )?(?:what if|why|how|isn'?t it|could it be)\b[^?\n]*\?\s*$", re.I)),
    # Two-imperative parallel slogan used as an aphoristic closer ("Attest the
    # run, re-derive the answer."). HIGH false-positive risk (ordinary
    # instructions are imperative pairs too, e.g. "Open the door, grab the
    # keys."), so it is LOW/advisory and anchored tightly: the whole line is a
    # short clause pair, each clause a bare verb + article + object, comma-joined,
    # sentence-final, nothing else. A leading determiner/pronoun/preposition in
    # either clause (a declarative subject, not a bare imperative) blocks the match.
    ("imperative-pair", "two-imperative parallel slogan (Verb the X, verb the Y.)",
     re.compile(r"(?im)^\s*"
                r"(?!(?:the|a|an|and|or|but|so|this|that|these|those|it|he|she|"
                r"they|we|you|i|my|your|our|his|her|their|its|there|here|if|when|"
                r"as|for|to|of|in|on|at)\b)"
                r"[a-z][\w-]*\s+(?:the|a|an|your|our|my|their|its|his|her)\s+"
                r"\w+(?:\s+\w+){0,2}\s*,\s*"
                r"(?!(?:the|a|an|and|or|but|so|this|that|these|those|it|he|she|"
                r"they|we|you|i|my|your|our|his|her|their|its|there|here|if|when|"
                r"as|for|to|of|in|on|at)\b)"
                r"[a-z][\w-]*\s+(?:the|a|an|your|our|my|their|its|his|her)\s+"
                r"\w+(?:\s+\w+){0,2}\s*[.!?]?\s*$")),
    # --- comprehensive-set LOW advisories (higher FP; never gate) --------- #
    # Formatting glyphs. Word processors insert curly quotes and ellipses on
    # their own, so these are advisories and never block.
    ("ellipsis-char", "ellipsis character (U+2026)",
     re.compile(r"\u2026")),
    ("arrow-glyph", "arrow glyph in prose",
     re.compile(r"[\u2192\u21d2\u279c\u2794\u27a4\u2b95\u2799]")),
    ("curly-quote", "curly quotation mark / apostrophe",
     re.compile(r"[\u201c\u201d\u2018\u2019]")),
    ("box-drawing", "box-drawing glyph in prose",
     re.compile(r"[\u2500-\u257f]")),
    ("bold-wrapup", "bold wrap-up label (**Bottom line:** / **TL;DR:**)",
     re.compile(r"(?im)^\s*\*\*(?:bottom line|key takeaways?|tl;?dr|the takeaway|"
                r"pro ?tip|note|important)\b[^*\n]*\*\*\s*:?")),
    # Structural framing that is common in ordinary prose too.
    ("superlative", "hedged superlative (one of the most X)",
     re.compile(r"(?i)\bone of the (?:most|best|leading|largest|fastest|greatest|biggest)\b")),
    ("correlative", "correlative comparative (the more X, the more Y)",
     re.compile(r"(?i)\bthe (?:more|less|greater|bigger|better|harder|faster|deeper|higher)\b"
                r"[^.!?,\n]{1,40},?\s+the (?:more|less|greater|bigger|better|worse|"
                r"slower|easier|deeper|higher)\b")),
    ("concessive-opener", "concession-then-resolution opener (Despite X, Y)",
     re.compile(r"(?im)^\s*(?:despite|although|while|though|even though)\b[^.!?\n]{1,80},")),
    ("editorial-adverb", "sentence-initial editorial adverb",
     re.compile(r"(?im)^\s*(?:interestingly|remarkably|surprisingly|fundamentally|"
                r"undoubtedly|arguably)\s*,")),    # A spoken affirmation at a sentence start ("Of course, ...", "Absolutely.").
    # Ordinary speech and dictation produce it, so it only reports. The chat
    # reply that follows it with a deliverable is a HIGH rule (rules_high).
    # A reply opener that hands over a deliverable ("Certainly! Here is your
    # essay:") addresses whoever asked for the text. An email reply or a message
    # to a colleague does that on purpose, so it reports here; a document profile
    # (essay and the house profiles) promotes it to a blocking finding.
    ("reply-opener", "reply opener that hands over a deliverable",
     re.compile(r"(?i)(?:^|(?<=[.!?]\s))\s*(?:certainly|absolutely|of course|sure thing|great question|"
                r"good question|happy to help)[!,.]\s*(?:here(?:'s|\s+is|\s+are)\b|"
                r"below\s+(?:is|are)\b|i'?(?:ve|\s+have)\s+(?:written|drafted|prepared|"
                r"put\s+together|created|revised|rewritten)\b|i'?d\s+be\s+happy\s+to\b)")),
    ("affirmation-opener", "affirmation opener",
     re.compile(r"(?i)^\s*(?:certainly|absolutely|great question|good question|"
                r"excellent question|excellent point|fantastic question|sure thing|"
                r"of course|happy to help|i'?d be happy to)[!,.]")),
    # U+200B or U+2060 outside a Latin run: a word-boundary mark in Thai, Khmer,
    # Lao and Myanmar text. Reported so a writer can check it, never blocking.
    ("invisible-unicode", "zero-width character outside Latin text",
     re.compile("(?<![A-Za-z0-9!-/:-@\\[-`{-~])[\u200b\u2060]"
                "|[\u200b\u2060](?![A-Za-z0-9!-/:-@\\[-`{-~])")),
]

# Stock phrases of genre fiction (the shiver down the spine, the breath held
# unknowingly). A report-only advisory that stays on even where authorial voice
# governs (gate level off). It never gates, and the whole set is low-confidence
# until it runs against non-Western and translated corpora, so it is labeled
# optional review.
FICTION_SLOP = [
    ("fiction-stock-phrase", "somatic-emotion cliche",
     re.compile(r"\b(?:shiver|chill|tingle|jolt)s?\s+(?:ran|shot|went|crept|traced)?\s*"
                r"(?:down|up|through)\s+(?:his|her|their|my|its)\s+spine\b", re.I)),
    ("fiction-stock-phrase", "breath / whisper stock beat",
     re.compile(r"\b(?:breath (?:she|he|they|i) (?:did ?n'?t|had ?n'?t) (?:realize|know) "
                r"(?:she|he|they|i) (?:was|were) holding|barely above a whisper|"
                r"voice (?:barely )?(?:above|louder than) a whisper)\b", re.I)),
    ("fiction-stock-phrase", "ministrations / orbs / other stock fiction phrase",
     re.compile(r"\b(?:ministrations|(?:her|his|their) orbs|"
                r"a mix(?:ture)? of \w+ and \w+ (?:washed over|flooded|coursed through)|"
                r"the air (?:was |grew )?(?:thick|heavy) with|"
                r"little did (?:he|she|they|i) know)\b", re.I)),
    ("fiction-stock-phrase", "reflexive 'could not help but'",
     re.compile(r"\b(?:could|can|would|did)(?:\s*n'?t|\s+not)\s+help but\b", re.I)),
    ("fiction-stock-phrase", "scene-transition filler (in that moment)",
     re.compile(r"\b(?:in that (?:moment|instant)|as (?:the|a) [\w ]{0,20}?"
                r"(?:washed over|settled over|filled the room))\b", re.I)),
]

# Instruction injection: text that tries to steer a model reading the document,
# where prose to edit was expected. The editor treats the document strictly as
# data, so these never change a gate and are kept out of check_text. detect_injection surfaces them so the editor can warn
# before a rewrite. Detection, not a filter: a security paper may quote these in
# good faith, so the editor warns and proceeds under a content-as-data boundary,
# it does not refuse.
INJECTION = [
    ("prompt-injection", "override / ignore-instructions directive",
     re.compile(r"(?i)\b(?:ignore|disregard|forget|override|bypass)\b[^.\n]{0,40}?"
                r"\b(?:previous|prior|earlier|above|all|the|these|any)\b[^.\n]{0,24}?"
                r"\b(?:instruction|prompt|rule|standard|direction|constraint|guardrail|context)s?\b")),
    ("prompt-injection", "role reassignment (you are now / act as)",
     re.compile(r"(?i)\byou are (?:now (?:a|an|the|free|unrestricted|uncensored|in|going to)\b|"
                r"no longer (?:bound|restricted|required|an?\b|subject|allowed))|"
                r"\b(?:act|behave|respond|roleplay|pretend)(?:\s+\w+){0,2}\s+as (?:if|an?|the|though)\b|"
                r"\bnew (?:instructions?|rules?|system prompt)\s*:|"
                r"\b(?:no|without) (?:more )?restrictions?\b")),
    ("prompt-injection", "forced verdict / approval",
     re.compile(r"(?i)\b(?:reply|respond|answer|output|say|print|return|write)\b[^.\n]{0,24}?"
                r"\b(?:approved?|verified|accepted?|compliant)\b")),
    ("prompt-injection", "system-prompt or secret exfiltration",
     re.compile(r"(?i)\b(?:reveal|repeat|print|show|leak|disclose|output)\b[^.\n]{0,30}?"
                r"\b(?:your |the )?(?:system prompt|instructions?|prompt|guidelines|rules?|api key|secret|token)s?\b")),
    ("prompt-injection", "role header or model-addressed line",
     re.compile(r"(?im)^[ \t]{0,8}#{0,3}[ \t]{0,4}(?:system|assistant|developer|user)[ \t]{0,4}:[ \t]|"
                r"\b(?:as an ai|as a language model)\b")),
]
