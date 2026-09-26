#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.rules_medium_register -- MEDIUM rules over word and phrase choice.

The register lists, stock phrases, openers, closers and the email and blog
phrase frames. Standard library only.
"""
import re

MEDIUM_REGISTER = [
    # --- inflated words (house pack): a long word where a short one serves #
    ("inflated-word", "inflated word",
     re.compile(r"\b(?:delve[sd]?|delving|utili[sz]e[sd]?|utili[sz]ing|showcas(?:e[sd]?|ing)|"
                r"seamless(?:ly)?|robust(?:ness)?|pivotal|crucial(?:ly)?|realm|landscape|"
                r"tapestry|testament|nuanced|multifaceted|holistic(?:ally)?|myriad|plethora|"
                r"endeavou?rs?|facilitate[sd]?|elevate[sd]?|elevating|embark(?:ing|ed)?|"
                r"unlock(?:s|ing|ed)?|spearhead(?:s|ing|ed)?|"
                r"resonate[sd]?|resonating|illuminat(?:e[sd]?|ing)|intricate(?:ly)?|"
                r"meticulous(?:ly)?|comprehensive(?:ly)?|vibrant|bustling|"
                r"garner(?:s|ing|ed)?|foster(?:s|ing|ed)?|cultivat(?:e[sd]?|ing)|"
                r"underpin(?:s|ning|ned)?|streamlin(?:e[sd]?|ing)|paramount)\b", re.I)),
    # More inflated words from the house standard's list. The list began as
    # vocabulary that one writer's editing pass removed, so it is house style
    # and never blocks outside a house profile. Generic dual-use words (key,
    # essential, enable, ensure, framework, domain, efficient, effective,
    # significant, robust as an adjective) stay out to protect precision.
    ("inflated-word", "inflated word (extended list)",
     re.compile(r"\b(?:ever[- ](?:evolving|changing|growing|expanding)|fast[- ]paced|"
                r"transformative|groundbreaking|unprecedented|profound(?:ly)?|"
                r"remark(?:able|ably)|versatile|cornerstone|hallmark|catalyst|"
                r"bedrock|linchpin|powerhouse|synerg(?:y|ies|i[sz]e[sd]?)|"
                r"wealth of|treasure trove|vast (?:array|majority|landscape)|"
                r"nurtur(?:e[sd]?|ing)|bolster(?:s|ing|ed)?|augment(?:s|ing|ed)?|"
                r"amplif(?:y|ies|ied|ying)|prowess|beacon|gateway to|springboard|"
                r"navigat(?:e[sd]?|ing) the (?:complexit|landscape|challeng|nuance|maze)|"
                r"intricac(?:y|ies)|complexities of|delve deeper|ripe for)\b", re.I)),
    # --- idioms and set-phrase cliches ----------------------------------- #
    ("idiom-cliche", "idiom / set-phrase cliche",
     re.compile(r"\b(?:low[- ]hanging fruit|move the needle|boil the ocean|"
                r"double[- ]edged sword|elephant in the room|rabbit hole|"
                r"deep[- ]dives?|tip of the iceberg|best of both worlds|"
                r"needle in a haystack|when push comes to shove|"
                r"the fact of the matter)\b", re.I)),
    # --- marketing superlatives ------------------------------------------- #
    ("marketing", "marketing superlative",
     re.compile(r"\b(?:game[- ]?chang(?:er|ing)|cutting[- ]edge|state[- ]of[- ]the[- ]art|"
                r"revolutioni[sz]e[sd]?|revolutionary|next[- ]level|world[- ]class|"
                r"supercharge[sd]?|best[- ]in[- ]class|unparalleled|top[- ]notch|"
                r"the power of\b)\b", re.I)),
    # --- stock transitions ------------------------------------------------ #
    ("stock-transition", "stock connective",
     re.compile(r"\b(?:moreover|furthermore|additionally|that being said|as such|"
                r"notably|importantly|ultimately|in essence|essentially|"
                r"consequently|nevertheless|nonetheless|henceforth)\b", re.I)),
    # --- throat-clearing openers ------------------------------------------ #
    ("throat-clearing", "throat-clearing opener",
     re.compile(r"(?i)\b(?:(?:it'?s|it is) (?:important|essential|crucial|worth|vital|necessary) to \w+|"
                r"needless to say|"
                r"at its core|when it comes to|in today'?s [a-z]+ (?:world|landscape|era)|"
                r"in the (?:realm|world|age) of|here'?s the thing|the (?:reality|truth) is|"
                r"make no mistake|let'?s (?:dive in|delve|explore|unpack)|"
                r"one thing is (?:clear|certain))\b")),
    # --- trailing participial closers (", ensuring ...", ", making it ...") - #
    ("participial-closer", "trailing participial clause",
     re.compile(r",\s+(?:ensuring|allowing|making(?:\s+it)?|providing|offering|"
                r"highlighting|underscoring|showcasing|enabling|empowering|fostering|"
                r"leveraging|reflecting|driving|delivering|paving the way|ushering|"
                r"cementing|solidifying)\b", re.I)),
    # --- "plays a ... role", "a testament to", correlative range ---------- #
    ("cliche", "plays a (vital) role / a testament to",
     re.compile(r"\b(?:plays? an? [a-z]* ?role|a testament to|stands? as a testament)\b", re.I)),
    ("sweeping-range", "sweeping 'from X to Y' range",
     re.compile(r"\bfrom [a-z][a-z ]{2,30} to [a-z][a-z ]{2,30}(?:,| and )", re.I)),
    # --- hedge stacking --------------------------------------------------- #
    ("hedge-stack", "stacked hedge",
     re.compile(r"\b(?:may|might|could|can)\s+(?:potentially|possibly|perhaps|arguably|conceivably)\b"
                r"|\b(?:potentially|possibly|conceivably)\s+(?:could|may|might)\b", re.I)),
    # --- self-referential meta -------------------------------------------- #
    ("meta", "self-referential framing",
     re.compile(r"(?i)\b(?:in this (?:essay|article|post|section|piece|guide),?\s*(?:we|i|you)|"
                r"this (?:essay|article|post|piece|guide) (?:explores|examines|delves|covers|will))\b")),
    # --- closers ----------------------------------------------------------- #
    ("closer", "landing / summary closer",
     re.compile(r"(?i)\b(?:in conclusion|in summary|to sum up|at the end of the day|"
                r"when all is said and done|the bottom line(?: is)?)\b")),
    # --- elevated-Latinate verb inflations (research spec #11) ------------ #
    ("inflated-word", "elevated-Latinate verb",
     re.compile(r"\b(?:commenc(?:e|es|ed|ing)|ascertain(?:s|ed|ing)?|"
                r"conceptuali[sz]e(?:s|d)?|cataly[sz]e(?:s|d)?|"
                r"galvani[sz]e(?:s|d)?|epitomi[sz]e(?:s|d)?)\b", re.I)),
    # --- fake-suspense self-answered question fragment (spec #10) ---------- #
    ("cadence", "fake-suspense question",
     re.compile(r"(?im)^\s*(?:the (?:result|answer|takeaway|verdict|catch|kicker|best part)"
                r"|so,? what does (?:this|that) mean(?: for you)?)\?\s*$")),
    # --- deferral preface: announces a point instead of stating it (#18) --- #
    ("opener", "deferral preface (what's important is)",
     re.compile(r"\bwhat'?s (?:important|key|interesting)(?: here)? is\b", re.I)),
    # --- marketing punch cadence "No X. No Y. Just Z." (spec #9) ----------- #
    ("cadence", "triplet negation (No X. No Y. Just Z.)",
     re.compile(r"\bno \w+\.\s*no \w+\.\s*just\b", re.I)),
    # --- stock email and blog phrases (house pack) ------------------------ #
    ("email-stock-phrase", "stock email opener (hope this finds you well)",
     re.compile(r"\bi (?:hope|trust) (?:this|that) (?:e-?mail|message|note)\b"
                r"[^.]{0,30}\bfinds you (?:well|in good)\b", re.I)),
    ("email-stock-phrase", "blanket permission closer (don't hesitate to reach out)",
     re.compile(r"\b(?:please )?(?:don'?t|do not) hesitate to (?:reach out|contact|ask)\b", re.I)),
    ("email-stock-phrase", "corporate follow-up jargon (circling back / touching base)",
     re.compile(r"\b(?:circl(?:e|ing) back|touch(?:ing)? base|loop(?:ing)? (?:in|back))\b", re.I)),
    ("email-stock-phrase", "pre-labeled excitement (thrilled to announce)",
     re.compile(r"\b(?:i'?m|i am|we'?re|we are) (?:so |really |very )?"
                r"(?:excited|thrilled|delighted|pleased) to "
                r"(?:announce|share|introduce|let you know)\b", re.I)),
    ("email-stock-phrase", "cold-outreach flattery (came across, impressed)",
     re.compile(r"\bi came across (?:your|the)\b[^.]{0,50}"
                r"\b(?:and (?:was|am) (?:impressed|inspired|blown away))\b", re.I)),
    # --- authority appeal with no citation nearby (research spec #3) ------- #
    ("unsupported-authority", "authority appeal, no citation nearby",
     re.compile(r"(?i)\b(?:studies (?:have )?show(?:n)?|research (?:shows|suggests|indicates)|"
                r"experts agree|scientists say|data shows?)\b"
                r"(?![^.]{0,80}(?:\d{4}|https?://|et al\.|\[\d))")),
    # --- false-inclusivity framing (research spec #13) -------------------- #
    ("blog-stock-phrase", "false-inclusivity (whether you're X or Y)",
     re.compile(r"\bwhether you'?re (?:an?\s+)?\w+(?:\s+\w+){0,3}\s+or\s+(?:an?\s+)?\w+", re.I)),
    # --- promotional descriptive filler (research spec #14) --------------- #
    ("blog-stock-phrase", "promotional filler (boasts a / nestled in)",
     re.compile(r"\bboasts (?:a |an )?\w+|\bnestled (?:in|amid|among|between)\b", re.I)),    # --- deletable padding circumlocutions ------------------------------- #
    # MEDIUM: it blocks under a strict profile and reports under the default.
    ("wordiness", "deletable padding circumlocution",
     re.compile(r"\b(?:in order to|due to the fact that|for the purpose of|"
                r"at this point in time|with regard to|with respect to(?!\s+(?:\$|\\\(|[b-zB-HJ-Z]\b(?!')))|"
                r"a wide range of|in the process of|in a timely manner|"
                r"it should be noted that)\b", re.I)),
]
