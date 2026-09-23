#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.pack_reasons -- why each domain rule-pack finding costs a reader.

The domain packs (articulate.rules_ext) run only under a profile that switches
them on: `normative-spec` for the BCP 14 checks, and `ux-microcopy`,
`code-review`, `plain-language` and `controlled-english`, which a writer or a
project config chooses. The same rules hold as for every other reason: one
sentence on the reader, a published source by work and principle, and no reason
that rests on how often a model produces a pattern. The sources match the
defaults docs/features.md cites. A second reader has not yet reviewed this
table.

rule_reasons.REASONS merges this table. Standard library only.
"""
from __future__ import annotations

_PLAIN = "Federal Plain Language Guidelines (plainlanguage.gov, 2011)"
_STRUNK = "Strunk and White, The Elements of Style"
_GOVUK = "GOV.UK, writing for GOV.UK, clear language (sentences of 25 words or fewer)"
_REVIEW = "Google Engineering Practices, how to write code review comments"
_MS_GLOBAL = "Microsoft Style Guide, global communications, writing tips"
_STE = "ASD-STE100 Simplified Technical English, Issue 9"
_RFC8174 = "RFC 8174 (BCP 14), ambiguity of uppercase and lowercase keywords"
_RFC2119 = "RFC 2119 (BCP 14), key words for use in RFCs"

PACK_REASONS = {
    "ux-length": (
        "A long button, label or error sentence takes longer to scan, can be cut off "
        "on a small screen, and hides the action the reader came to take.",
        "Material Design 3, button guidelines; Microsoft, Windows button controls; "
        + _GOVUK),
    "ux-case": (
        "Mixed capitalization across one interface makes the reader wonder whether "
        "the capitals mark a name or a term.",
        "Microsoft Style Guide, capitalization; Material Design 3"),
    "ux-vague-error": (
        "An error message that names no cause and no next step leaves the reader "
        "unable to recover.",
        "Nielsen Norman Group, error-message guidelines"),
    "ux-link-text": (
        "Link text such as 'click here' tells a reader who scans the links, or hears "
        "them read aloud, nothing about where the link goes.",
        "W3C QA tip, Don't use 'click here' as link text; W3C Web Content "
        "Accessibility Guidelines 2.1, success criterion 2.4.9"),
    "review-condescension": (
        "Words such as 'just', 'obviously' or 'why didn't you' tell the author the "
        "change should have been easy, which reads as blame and makes the comment "
        "harder to act on.",
        _REVIEW + ", courtesy"),
    "review-no-reason": (
        "A request with no reason leaves the author unable to weigh it or to apply "
        "the same lesson to the next change.",
        _REVIEW + ", explain why"),
    "review-absolute": (
        "A statement about the person, such as 'you always' or 'your code is wrong', "
        "turns a comment on the change into a judgment of its author.",
        _REVIEW + ", comment on the code and never on the developer"),
    "plain-readability": (
        "Above the reading grade its audience reads at, a document is skimmed or "
        "misread; the grade here is an estimate from sentence and word length.",
        "Microsoft Word, readability statistics; AHRQ Health Literacy Universal "
        "Precautions Toolkit, Tool 11"),
    "plain-long-sentence": (
        "A sentence over 25 words asks the reader to hold more in mind before its "
        "point arrives.",
        _GOVUK + "; " + _PLAIN + ", write short sentences"),
    "plain-wordy": (
        "A padded phrase such as 'in order to' makes the reader process words that "
        "add no meaning where a plainer form says the same.",
        _STRUNK + ", omit needless words; " + _PLAIN + ", omit unnecessary words"),
    "bcp14-mixed-case": (
        "A keyword in mixed case, such as 'MUST not', leaves the reader unsure whether "
        "the requirement carries its BCP 14 force.",
        _RFC8174),
    "bcp14-no-boilerplate": (
        "Capital keywords with no citation of BCP 14 leave the reader unsure whether "
        "they carry the RFC 2119 meaning.",
        _RFC8174 + ", the boilerplate"),
    "bcp14-may-not": (
        "'MAY NOT' is no BCP 14 keyword, so the reader cannot tell whether the text "
        "forbids the step or only declines to require it.",
        _RFC2119 + "; " + _RFC8174),
    "bcp14-lowercase": (
        "In a document that declares BCP 14, a lowercase 'must' has only its plain "
        "sense, and the reader cannot tell whether a requirement was meant.",
        _RFC8174),
    "bcp14-shall-must": (
        "RFC 2119 makes SHALL and MUST synonyms, so a document that uses both sends "
        "the reader looking for a difference in strength that is not there.",
        _RFC2119 + ", MUST and SHALL"),
    "bcp14-old-boilerplate": (
        "Without the RFC 8174 clause on capitals, the reader cannot tell whether a "
        "lowercase keyword carries BCP 14 force.",
        _RFC8174 + ", the boilerplate"),
    "controlled-sentence-length": (
        "A long sentence is harder for a second-language reader, and for a "
        "translation engine, to parse into its parts.",
        _STE + ", sentence length (20 words in a procedure, 25 in a description)"),
    "controlled-multi-instruction": (
        "Two instructions in one sentence make a reader, or a translation, more "
        "likely to merge or miss a step.",
        _STE + ", one instruction in each sentence"),
    "controlled-idiom": (
        "An idiom asks the reader to know a meaning its words do not state, and a "
        "second-language reader or a translation engine may read it word by word.",
        _MS_GLOBAL + ", avoid idioms"),
    "controlled-phrasal-verb": (
        "A phrasal verb such as 'find out' carries several meanings a second-language "
        "reader must choose among; one verb such as 'learn' carries fewer.",
        _STE + ", approved words with one meaning each"),
    "controlled-vague-pronoun": (
        "A sentence that opens with 'This' or 'It' and no noun makes the reader look "
        "back to find what the pronoun stands for.",
        "Google developer documentation style guide, ambiguous pronoun references"),
}
