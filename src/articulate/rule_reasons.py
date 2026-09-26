#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.rule_reasons -- why a pattern may block a writer who never chose a
house style.

A rule may gate outside the house pack only with a reader-cost reason: one
sentence on what the pattern costs a reader, and a published style guide or
readability source behind it. How often a model produces a pattern is never a
reason, and no text here states one. A rule whose only support is the
maintainer's taste belongs to the house pack. The house profiles (`house`,
`house-essay`) gate it; every other profile reports it at LOW and never blocks.

The sources are cited by work and principle, without page numbers. A second
reader, neither the maintainer nor a model, checks each reason before a release
that relies on it. That review has not happened yet for this table.

Standard library only.
"""
from __future__ import annotations

from .aliases import CATEGORY_ALIASES, resolve_all, resolve_category  # noqa: F401

# Categories in the house pack: one writer's standard, applied only by choice.
HOUSE_CATEGORIES = frozenset({
    # punctuation and contrast devices
    "em-dash", "antithesis", "corrective-negation", "substitution",
    "negative-parallel", "contrast-pair",
    # single words and word lists
    "intensifier", "corporate-verb", "inflated-word", "register-jargon",
    # structure that learners are taught, or that fires on ordinary speech
    "enumeration", "stock-transition", "closer", "both-sides", "cadence",
    "participial-closer", "sweeping-range", "setup", "reveal", "scaffold",
    "rhetorical-we", "delivery", "over-apology", "disclaimer", "evasive",
    # stock phrases of a genre
    "email-stock-phrase", "blog-stock-phrase", "cta", "continuation-cliche", "significance",
})

_PLAIN = "Federal Plain Language Guidelines (plainlanguage.gov, 2011)"
_WILLIAMS = "Williams and Bizup, Style: Lessons in Clarity and Grace"
_ORWELL = "Orwell, Politics and the English Language (1946)"
_STRUNK = "Strunk and White, The Elements of Style"

REASONS = {
    "chat-interface-text": (
        "Text addressed to a chat user, or a chat tool's internal token, speaks to "
        "someone other than the reader and gives them nothing to act on.",
        _PLAIN + ", write for your audience"),
    "invisible-unicode": (
        "A hidden character inside a run of Latin text breaks search, copy and paste "
        "and spell check, and can hide text the reader never sees.",
        "The Unicode Standard, chapter 23, layout controls (U+200B, U+2060)"),
    "wordiness": (
        "A padded phrase such as 'in order to' or 'due to the fact that' makes the "
        "reader process words that add no meaning.",
        _STRUNK + ", omit needless words; " + _PLAIN + ", omit unnecessary words"),
    "idiom-cliche": (
        "A worn figure of speech asks the reader to translate it back into a plain "
        "claim, and many readers of English as a second language cannot.",
        _ORWELL + ", rule 1; " + _PLAIN + ", avoid jargon"),
    "marketing": (
        "An unsupported superlative claims a comparison the text never makes, so "
        "the reader cannot check it.",
        _ORWELL + ", pretentious diction"),
    "throat-clearing": (
        "An opener that announces a point delays it; the reader holds the sentence "
        "open until the claim arrives.",
        _WILLIAMS + ", metadiscourse and concision"),
    "opener": (
        "A preface such as 'what is important is' announces a point the reader "
        "could have been given directly.",
        _WILLIAMS + ", metadiscourse and concision"),
    "meta": (
        "Text about the text, or about what the reader might be thinking, delays "
        "the content the reader came for.",
        _WILLIAMS + ", metadiscourse"),
    "cliche": (
        "A stock phrase such as 'plays a vital role' names a relation without saying "
        "what it is, so the reader learns nothing they could restate.",
        _ORWELL + ", rule 1"),
    "hedge-stack": (
        "Two hedges on one claim state the same doubt twice, and the reader cannot "
        "tell how sure the writer is.",
        _WILLIAMS + ", hedges and intensifiers"),
    "unsupported-authority": (
        "An appeal to unnamed studies or experts gives the reader no source to check.",
        "Publication Manual of the American Psychological Association (7th ed.), "
        "citing sources in the text"),
    "sycophancy": (
        "Praise of a question addresses a chat partner; in a document it tells the "
        "reader nothing about the subject.",
        _PLAIN + ", write for your audience"),
    "closing-boilerplate": (
        "A closing line such as 'I hope this helps' addresses a chat partner and "
        "adds nothing the reader can use.",
        _PLAIN + ", write for your audience"),
    "emoji-structure": (
        "An emoji used as a heading or bullet marker has no fixed meaning, and a "
        "screen reader reads its name aloud.",
        "W3C Web Content Accessibility Guidelines 2.1, success criterion 1.1.1"),
}

# Words that state a model-frequency reason. No reason may use them.
ORIGIN_WORDS = ("model", "ai ", "llm", "frontier", "machine", "generated", "chatgpt",
                "gpt", "detector")


# Retired category ids live in articulate.aliases; these names are re-exported
# for callers that import them from here.
ALIASES = CATEGORY_ALIASES


def is_house(category):
    return category in HOUSE_CATEGORIES


def reason_for(category):
    """(reason, source) for a category that may gate outside the house pack, or
    None for a house or report-only category."""
    return REASONS.get(category)
