"""The domain packs and project terms skip quoted text, as the phrasing rules do.

A quotation is its source's words. The core phrasing rules read a document with
every direct quotation, Markdown block quote and LaTeX quote environment
blanked (SCAN_ALGO 6 and 7). The packs and the project terminology read the same
text with the same quotations blanked, from ruleset 0.9.0 (rules_ext 1.2.0), so
a spec that quotes another spec's "SHOULD not", or a style guide that quotes a
banned term, is not held to the writer's own rules.

Each case states a phrase once in the writer's own words, which must fire, and
once inside a quotation, which must not. The UI-string pack is the exception:
its quoted strings are the interface text it checks, not quotations.
"""
from collections import Counter

import pytest

import articulate
from articulate import profiles, project

DQ = chr(34)


def _found(text, prof, cat):
    r = articulate.check_text(text, profile=prof)
    return Counter((f["tier"], f["rule_id"]) for t in ("high", "medium", "low")
                   for f in r[t] if f["category"] == cat)


def _terms(term):
    return project.apply_payload(profiles.load("flavored"), {"terminology": term})


BANNED = {"banned": [{"term": "whitelist", "reason": "use allowlist", "suggestion": "allowlist"}]}

# (profile or None for the banned-term profile, category, own words, quoted form)
CASES = [
    ("normative-spec", "bcp14-mixed-case",
     "Clients SHOULD not retry after a timeout.\n",
     "The old draft said " + DQ + "clients SHOULD not retry" + DQ + " and was withdrawn.\n"),
    ("normative-spec", "bcp14-may-not",
     "Servers MAY NOT cache the reply.\n",
     "An early reviewer wrote " + DQ + "servers MAY NOT cache it" + DQ + " in error.\n"),
    ("plain-language", "plain-wordy",
     "Press the key in order to start the pump.\n",
     "The manual says " + DQ + "press the key in order to start" + DQ + " on page 4.\n"),
    ("controlled-english", "controlled-idiom",
     "The tool works out of the box on most hosts.\n",
     "The vendor claims it " + DQ + "works out of the box" + DQ + " on most hosts.\n"),
    (None, "terminology",
     "Add the host to the whitelist first.\n",
     "The old guide said " + DQ + "add the host to the whitelist" + DQ + " at this step.\n"),
]


def _profile(name):
    return _terms(BANNED) if name is None else profiles.load(name)


@pytest.mark.parametrize("name,cat,own,quoted", CASES, ids=[c[1] for c in CASES])
def test_a_quoted_phrase_gives_no_pack_or_term_finding(name, cat, own, quoted):
    prof = _profile(name)
    assert _found(own, prof, cat), (cat, "premise: the phrase fires in the writer's words")
    assert not _found(quoted, prof, cat), quoted


@pytest.mark.parametrize("name,cat,own,quoted", CASES, ids=[c[1] for c in CASES])
def test_a_block_quote_gives_no_pack_or_term_finding(name, cat, own, quoted):
    prof = _profile(name)
    text = "The reviewer quoted the old text.\n\n> " + own
    assert not _found(text, prof, cat), text
    # Control: the same line outside the block quote fires.
    assert _found("The reviewer quoted the old text.\n\n" + own, prof, cat)


@pytest.mark.parametrize("name,cat,own,quoted", CASES, ids=[c[1] for c in CASES])
def test_a_latex_quote_environment_gives_no_pack_or_term_finding(name, cat, own, quoted):
    prof = _profile(name)
    text = "As the source puts it:\n\\begin{quote}\n" + own + "\\end{quote}\n"
    assert not _found(text, prof, cat), text


def test_a_quotation_that_wraps_inside_its_paragraph_is_still_skipped():
    # The packs read a paragraph as one line, so a quotation the writer wrapped
    # across a line break is one quotation, as it is for the core rules.
    prof = profiles.load("normative-spec")
    text = ("The old draft said " + DQ + "clients\nSHOULD not retry" + DQ
            + " and was withdrawn.\n")
    assert not _found(text, prof, "bcp14-mixed-case")
    # Control: the same wrapped words with no quotation marks fire.
    assert _found(text.replace(DQ, ""), prof, "bcp14-mixed-case")


def test_an_inch_mark_opens_no_quotation_for_the_packs():
    # The packs pair marks as the core rules do (articulate.quotemarks): a mark
    # after a digit closes nothing it did not open, so the writer's own text
    # after it is still read.
    prof = profiles.load("normative-spec")
    text = "The panel is 6" + DQ + " wide. Clients SHOULD not retry. See " + DQ + "Notes" + DQ + ".\n"
    assert _found(text, prof, "bcp14-mixed-case")


def test_the_boilerplate_with_quoted_keywords_still_declares_bcp_14():
    # Control, true before and after: the declaration's own quoted keywords are
    # not findings, and the declaration itself is read.
    prof = profiles.load("normative-spec")
    text = ("The key words " + DQ + "MUST" + DQ + " and " + DQ + "SHOULD" + DQ + " in this "
            "document are to be interpreted as described in BCP 14 [RFC2119] [RFC8174] "
            "when, and only when, they appear in all capitals, as shown here.\n\n"
            "Clients MUST retry.\n")
    assert not _found(text, prof, "bcp14-no-boilerplate")
    assert not _found(text, prof, "bcp14-old-boilerplate")


def test_a_declaration_the_writer_quotes_still_declares_bcp_14():
    # A document may state its conventions by quoting the boilerplate. Whether
    # it declares BCP 14 is read from all of its prose, quotations included;
    # only findings skip quoted text.
    prof = profiles.load("normative-spec")
    text = ("> The key words in this document are to be interpreted as described in "
            "BCP 14 [RFC2119] [RFC8174] when, and only when, they appear in all capitals.\n\n"
            "Clients MUST retry.\n")
    assert not _found(text, prof, "bcp14-no-boilerplate")


def test_the_ui_string_pack_still_reads_quoted_interface_text():
    # Control, true before and after: in a UI string file the quotes delimit the
    # interface text the pack checks, so they are not skipped.
    prof = profiles.load("ux-microcopy")
    text = "button: " + DQ + "Click here to save all of your changes to the server now" + DQ + "\n"
    r = articulate.check_text(text, profile=prof)
    cats = {f["category"] for t in ("high", "medium", "low") for f in r[t]}
    assert cats & {"ux-length", "ux-link-text"}, cats
