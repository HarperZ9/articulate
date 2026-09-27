"""Defects in quote blanking found in review of the 0.6.0 candidate, fixed in
ruleset 0.9.0 (SCAN_ALGO 7).

Every phrasing rule reads a text with its quotations blanked. The review found
two ways that went wrong: text outside any quotation that the masks hid, so the
rules went silent on the writer's own prose, and quotations the masks missed,
so the rules scored a source's words.

Each defect test was strict xfail until the fix, because the fix moves the
ruleset and PERSUADE 2.0 had been read (fairness/PREREG.md, amendment of 27
September 2026). The fix lands with ruleset 0.9.0, which a corpus named in a
later amendment confirms or fails. The tests now guard the fix. The controls
show that the rules still fire on bare prose and still skip a quotation.
"""
import pytest

from articulate import check_text, profiles

ESSAY = profiles.load("essay")
DEFAULT = profiles.load("flavored")
PHRASE = "studies show that this approach is a game-changer"
BS = chr(92)   # a backslash, written this way so no editor or shell eats it


def _medium(text, prof=ESSAY):
    r = check_text(text, profile=prof, house_notes=False)
    return sorted(f["category"] for f in r["medium"])


def _words(text):
    return check_text(text, profile=ESSAY, house_notes=False)["words"]


# --- controls: the rule fires on bare prose and not inside straight quotes --- #

def test_control_the_phrase_blocks_in_the_writers_own_prose():
    assert _medium(f"We found that {PHRASE}.\n") == ["marketing", "unsupported-authority"]


def test_control_a_straight_quoted_phrase_is_blanked():
    assert _medium(f'She wrote, "{PHRASE}."\n') == []


# --- one mention of a LaTeX quote environment hides the rest of a file ------- #

PREAMBLES = {
    "inline-code": f"Use `{BS}begin{{quote}}` for a long quotation.\n\n",
    "html-comment": f"<!-- {BS}begin{{quote}} -->\n\n",
    "tex-comment": f"% {BS}begin{{quotation}} was here\n\n",
    "fenced-code": f"```latex\n{BS}begin{{quote}}\n```\n\n",
}


@pytest.mark.parametrize("where", sorted(PREAMBLES))
def test_a_named_quote_environment_does_not_hide_the_prose_after_it(where):
    text = PREAMBLES[where] + f"We found that {PHRASE}.\n"
    assert _medium(text) == ["marketing", "unsupported-authority"]


# A named begin and end that LaTeX would never read must not pair around the
# writer's prose either. An environment that never closes blanks nothing, so
# these cases close it, which the cases above cannot show.
BEGIN, END = f"{BS}begin{{quote}}", f"{BS}end{{quote}}"
MENTIONED_PAIRS = {
    "inline-code": (f"Use `{BEGIN}` to open.\n\n", f"Close it with `{END}`.\n"),
    "html-comment": (f"<!-- {BEGIN} -->\n\n", f"<!-- {END} -->\n"),
    "tex-comment": (f"% {BEGIN}\n\n", f"% {END}\n"),
    "fenced-code": (f"```latex\n{BEGIN}\n```\n\n", f"```latex\n{END}\n```\n"),
}


@pytest.mark.parametrize("where", sorted(MENTIONED_PAIRS))
def test_a_mentioned_begin_and_end_do_not_hide_the_prose_between(where):
    before, after = MENTIONED_PAIRS[where]
    text = before + f"We found that {PHRASE}.\n\n" + after
    assert _medium(text) == ["marketing", "unsupported-authority"]


def test_control_a_real_quote_environment_is_still_blanked():
    text = f"{BEGIN}\nWe found that {PHRASE}.\n{END}\n"
    assert _medium(text) == []


def test_nested_quote_environments_blank_the_outer_text_after_the_inner_end():
    inner = f"{BS}begin{{quotation}}\nsaid\n{BS}end{{quotation}}\n"
    text = f"{BEGIN}\nfirst\n{inner}We found that {PHRASE}.\n{END}\n"
    assert _medium(text) == []


# --- an unpaired mark blanks the writer's prose up to the next mark ---------- #

def test_an_inch_mark_does_not_blank_prose_up_to_the_next_quote():
    text = f'He is 6" tall, and {PHRASE}, so she called it "fine" and left.\n'
    assert "marketing" in _medium(text)


def test_a_backtick_apostrophe_does_not_blank_prose_or_drop_words():
    typed = f"I didn`t know that {PHRASE}, and it wasn`t clear.\n"
    plain = f"I didn't know that {PHRASE}, and it wasn't clear.\n"
    assert "marketing" in _medium(typed)
    assert _words(typed) == _words(plain)


def test_an_autocorrected_left_quote_on_a_year_does_not_blank_prose():
    text = f"In the ‘90s, {PHRASE}, and it’s over.\n"
    assert "marketing" in _medium(text)


# --- quotations the masks miss ----------------------------------------------- #

NON_ENGLISH = {
    "guillemets": ("« ", " »"),
    "german": ("„", "“"),
    "swedish": ("”", "”"),
    "cjk-corner": ("「", "」"),
}


@pytest.mark.parametrize("style", sorted(NON_ENGLISH))
def test_a_quotation_in_another_languages_marks_is_blanked(style):
    open_, close = NON_ENGLISH[style]
    assert _medium(f"She wrote: {open_}{PHRASE}.{close}\n") == []


def test_a_latex_quotation_with_an_apostrophe_inside_is_blanked():
    text = f"She wrote, ``{PHRASE.replace('this', 'it' + chr(39) + 's this')}.''\n"
    assert _medium(text) == []


def test_a_csquotes_enquote_is_blanked():
    assert _medium(f"She wrote, {BS}enquote{{{PHRASE}.}}\n") == []


def test_a_chatbot_line_quoted_in_guillemets_does_not_block_the_default():
    text = ("The bot replied: «As an AI language model, I cannot browse "
            "the web.»\n")
    r = check_text(text, profile=DEFAULT, house_notes=False)
    assert r["gate"] == "ok", [f["label"] for f in r["high"]]
