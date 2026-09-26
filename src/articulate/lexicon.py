#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.lexicon -- the auxiliary regexes and word sets the scanner and the
advisories count over. Standard library only.
"""
import re

# Emoji: a coarse but serviceable set of the ranges frontier models reach for.
EMOJI = re.compile(
    "["
    "\U0001F300-\U0001FAFF"   # symbols & pictographs, extended
    "\U00002600-\U000027BF"   # misc symbols + dingbats
    "\U0001F000-\U0001F0FF"   # tiles
    "\U00002B00-\U00002BFF"   # arrows/stars
    "\U0000FE00-\U0000FE0F"   # variation selectors
    "\U00002190-\U000021FF"   # arrows (⇒ etc.)
    "\U00002700-\U000027BF"
    "]"
)

# Vague quantifier where a writer who knew the count would give it. Advisory,
# and suppressed when the same line already carries a digit (spec #23).
VAGUE_QUANT = re.compile(r"\b(?:various|numerous|a number of|several)\b", re.I)
DIGIT = re.compile(r"\d")

# SOFT signals: dual-use words too common to hard-flag one at a time (they fire
# on legitimate human prose), but whose DENSITY is diagnostic. Counted only for
# the graded texture score, never as a HIGH/MEDIUM hit. This is how a real
# detector accumulates weak evidence instead of convicting on a single word.
SOFT = re.compile(r"(?i)\b(?:essential|significant(?:ly)?|enhance[sd]?|enhancing|"
                  r"accelerate[sd]?|deliver(?:s|ed|ing)?|ensure[sd]?|ensuring|"
                  r"crucial(?:ly)?|vital(?:ly)?|optimi[sz]e[sd]?|streamlin(?:e[sd]?|ing)|"
                  r"effective(?:ly)?|efficient(?:ly)?|innovat(?:e|es|ed|ive|ion)|"
                  r"solutions?|impact(?:ful)?|meaningful|valuable|powerful|"
                  r"comprehensive|thoughtful(?:ly)?|significantly|productivity|"
                  r"outcomes?|workflows?|capabilit(?:y|ies))\b")
WORD = re.compile(r"\b\w+\b")
# Orwell/Williams structural signals, measured as document rates (length-
# independent, unlike raw type-token ratio, which is why TTR is not used here).
ADVERB = re.compile(r"\b\w{3,}ly\b", re.I)
PASSIVE = re.compile(r"\b(?:is|are|was|were|be|been|being)\s+(?:\w+ly\s+)?\w+ed\b(?!\s+by\b)", re.I)
# Keyword-free contrast pair / negative parallelism: two short adjacent sentences
# with the same subject where one affirms and the next negates ("You can watch
# what a model does. You cannot watch what it is."). The antithesis regex misses
# this because there is no "not X but Y" keyword to anchor on.
NEG = re.compile(r"\b(?:cannot|can ?not|can't|is ?n't|is not|are ?n't|are not|"
                 r"does ?n't|does not|do ?n't|do not|will not|won't|never|"
                 r"no longer|not)\b", re.I)
FIRSTWORD = re.compile(r"^\W*(\w+)")

# Williams, "Style: Lessons in Clarity and Grace" (the basis Ptacek names).
# Expletive opener: a sentence that starts with empty "there is" / "it is
# important" instead of a real subject. Advisory (existential "there is" is
# often the clearest phrasing), matched on the stripped-markup line start.
EXPLETIVE = re.compile(r"(?i)^(?:there (?:is|are|was|were)|"
                       r"it (?:is|was) (?:important|worth|crucial|essential|necessary))\b")
# Nominalization: action buried in an abstract noun. Advisory, and only when
# several stack in one line, because this domain uses "verification",
# "evaluation", "attribution" as real terms.
NOMINAL = re.compile(r"\b\w{4,}(?:tion|ment|ance|ence|ancy|ency)\b", re.I)

# Structural-heuristic constants (comprehensive set). Markdown structure markers
# and the token sets the statistical advisories count over. These feed report-only
# LOW advisories and the local-anaphora MEDIUM, never the HIGH device gate.
HEADING = re.compile(r"^\s{0,3}#{1,6}\s")
BULLET = re.compile(r"^\s*(?:[-*+]|\d+\.)\s")
BOLD_SPAN = re.compile(r"\*\*[^*\n]+\*\*|__[^_\n]+__")
# Stopword-only n-grams are not repetition tells, so they are excluded.
NGRAM_STOP = frozenset({
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for", "with",
    "as", "at", "by", "is", "are", "was", "were", "be", "been", "it", "its",
    "this", "that", "these", "those", "you", "we", "they", "i", "he", "she",
    "from", "into", "than", "then", "so", "if", "not", "no", "do", "does",
    "can", "will", "would", "your", "our", "their", "there", "here", "which",
})
# Hedge tokens; several in one sentence is a hedge cluster (Orwell caution excess).
HEDGE_WORDS = re.compile(r"(?i)\b(?:may|might|could|can|perhaps|possibly|potentially|"
                         r"likely|probably|maybe|generally|typically|usually|often|"
                         r"somewhat|arguably|seemingly|presumably|conceivably)\b")

# Function-word sentence openers everyone reuses; excluded from opener-variety.
OPENER_STOP = {
    "the", "a", "an", "it", "this", "that", "these", "those", "there", "in",
    "on", "for", "and", "but", "so", "to", "as", "we", "you", "i", "they",
    "he", "she", "its", "their", "our", "his", "her", "at", "of", "by", "with",
    "from", "or", "if", "when", "while", "then", "now", "here", "no", "one",
    "each", "every", "some", "most", "all", "both", "what", "how", "why",
}
