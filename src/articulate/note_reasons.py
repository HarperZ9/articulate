#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.note_reasons -- why each report-only note is worth a writer's look.

These notes never block under a default profile. Each still carries a reason,
so a writer can judge the note on what it costs a reader and ignore it where it
does not apply. The same rules as for the blocking reasons hold: one sentence on
the reader, a published source by work and principle, and no reason that rests
on how often a model produces a pattern. A second reader has not yet reviewed
this table either.

rule_reasons.REASONS merges this table. Standard library only.
"""
from __future__ import annotations

_PLAIN = "Federal Plain Language Guidelines (plainlanguage.gov, 2011)"
_WILLIAMS = "Williams and Bizup, Style: Lessons in Clarity and Grace"
_ORWELL = "Orwell, Politics and the English Language (1946)"
_STRUNK = "Strunk and White, The Elements of Style"
_WCAG = "W3C Web Content Accessibility Guidelines 2.1, success criterion 1.1.1"
_CONCRETE = _STRUNK + ", use definite, specific, concrete language"

NOTE_REASONS = {
    "affirmation-opener": (
        "An opening 'Certainly!' or 'Of course,' answers a request the reader never "
        "made, so the reader skips it to reach the content.",
        _PLAIN + ", write for your audience"),
    "anaphora": (
        "The same opening words on several sentences in a row can bury what each "
        "sentence adds; keep the repetition where it is the point.",
        _WILLIAMS + ", cohesion and emphasis"),
    "arrow-glyph": (
        "An arrow glyph in prose has no fixed spoken form, so a screen reader reads "
        "its name and the reader must guess the relation it stands for.",
        _WCAG),
    "bold-density": (
        "Bold on many phrases leaves no phrase standing out, so the reader cannot "
        "tell which words matter most.",
        _WILLIAMS + ", emphasis"),
    "bold-lead": (
        "A bold label before every list item repeats the item's first words and "
        "slows a reader who scans the list.",
        _PLAIN + ", use lists"),
    "bold-wrapup": (
        "A bold label such as 'Bottom line:' announces a summary in place of stating "
        "it, and the reader waits for the claim.",
        _WILLIAMS + ", metadiscourse"),
    "box-drawing": (
        "Box-drawing characters in prose draw a picture that a screen reader reads "
        "glyph by glyph and that breaks when the text reflows.",
        _WCAG),
    "closer-question": (
        "A rhetorical question hands the reader a question the writer could have "
        "answered, and the answer is what the reader came for.",
        _PLAIN + ", write for your audience"),
    "concessive-opener": (
        "A concession before the main clause makes the reader hold a qualification "
        "open until the claim arrives; keep it where the contrast is the point.",
        _WILLIAMS + ", cohesion and emphasis"),
    "correlative": (
        "A 'the more X, the more Y' frame claims a proportional relation that the "
        "reader cannot check unless the text gives the measure.",
        _CONCRETE),
    "editorial-adverb": (
        "An opening 'Interestingly,' or 'Remarkably,' tells the reader how to feel "
        "about a point before giving it; the point can show that itself.",
        _WILLIAMS + ", metadiscourse"),
    "ellipsis-char": (
        "The single ellipsis character differs from three periods in search and "
        "plain-text tools, so a reader searching for three periods misses it.",
        "The Unicode Standard, U+2026 horizontal ellipsis (compatibility "
        "decomposition to three full stops)"),
    "emoji": (
        "An emoji in running text has no fixed meaning across readers, and a screen "
        "reader reads its name aloud.",
        _WCAG),
    "expletive-opener": (
        "An opening 'It is important to' is metadiscourse that delays the subject; "
        "the reader waits for the claim it announces.",
        _WILLIAMS + ", metadiscourse"),
    "fiction-stock-phrase": (
        "A stock phrase of genre fiction gives the reader a worn image in place of "
        "the detail of this scene.",
        _ORWELL + ", rule 1"),
    "fragment-opener": (
        "A verbless fragment such as 'Strong foundation.' at a paragraph start names "
        "a quality without the claim that would let the reader check it.",
        _CONCRETE),
    "header-reflex": (
        "Many headings on a short text break it into labels the reader must "
        "reassemble; a short text often reads better as connected paragraphs.",
        _STRUNK + ", make the paragraph the unit of composition"),
    "hedge-cluster": (
        "Three or more hedges in one sentence leave the reader unable to tell what "
        "the writer claims.",
        _WILLIAMS + ", hedges and intensifiers"),
    "imperative-pair": (
        "A two-part imperative slogan compresses a claim into a rhythm, and the "
        "reader must unpack what each half asserts.",
        _CONCRETE),
    "list-reflex": (
        "When most lines are list items, the links between points drop out and the "
        "reader must supply the 'because' and 'so' that prose would carry.",
        _WILLIAMS + ", cohesion and coherence"),
    "ngram-repetition": (
        "A phrase repeated many times makes the reader meet the same words again; if "
        "it is your key term, keeping one term is plain-language practice.",
        _PLAIN + ", use the same terms consistently"),
    "nominalization": (
        "Four or more nouns made from verbs in one sentence hide who does what, and "
        "the reader must rebuild the actions.",
        _WILLIAMS + ", actions and characters"),
    "paragraph-uniformity": (
        "A paragraph break marks a new point; paragraphs of near-equal length can "
        "mean the breaks follow a length and not the ideas.",
        _STRUNK + ", make the paragraph the unit of composition"),
    "rule-of-three": (
        "A list of three can pad a point with an item that adds nothing new; check "
        "that each item carries its own meaning.",
        _STRUNK + ", omit needless words"),
    "superlative": (
        "'One of the most' claims a ranking without naming the comparison, so the "
        "reader cannot check it.",
        _CONCRETE),
    "vague-quantifier": (
        "'Several' or 'numerous' where the count is known withholds a number the "
        "reader could use.",
        _CONCRETE),
}
