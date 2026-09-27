"""Known defects in quote blanking, recorded until the next pre-registered ruleset.

Every phrasing rule reads a text with its quotations blanked (SCAN_ALGO 6). A
review of the 0.6.0 candidate found two ways that goes wrong: text outside any
quotation that the masks hide, so the rules go silent on the writer's own prose,
and quotations the masks miss, so the rules score a source's words.

Each defect test is strict xfail. A fix changes what the rules read, which moves
the ruleset, and PERSUADE 2.0 has been read, so the fix waits for the next
pre-registered ruleset (fairness/PREREG.md, amendment of 27 September 2026).
Strict xfail keeps the suite green, records the defect, and fails the run when a
fix lands without removing the marker. The controls are plain tests.
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


def _known(defect):
    return pytest.mark.xfail(strict=True, reason=f"known defect ({defect}); the fix "
                                                 "changes the ruleset and waits for the "
                                                 "next pre-registration")


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


@_known("a named quote environment hides the rest of the file")
@pytest.mark.parametrize("where", sorted(PREAMBLES))
def test_a_named_quote_environment_does_not_hide_the_prose_after_it(where):
    text = PREAMBLES[where] + f"We found that {PHRASE}.\n"
    assert _medium(text) == ["marketing", "unsupported-authority"]


# --- an unpaired mark blanks the writer's prose up to the next mark ---------- #

@_known("an inch mark pairs with the next quote")
def test_an_inch_mark_does_not_blank_prose_up_to_the_next_quote():
    text = f'He is 6" tall, and {PHRASE}, so she called it "fine" and left.\n'
    assert "marketing" in _medium(text)


@_known("a backtick apostrophe opens a code span")
def test_a_backtick_apostrophe_does_not_blank_prose_or_drop_words():
    typed = f"I didn`t know that {PHRASE}, and it wasn`t clear.\n"
    plain = f"I didn't know that {PHRASE}, and it wasn't clear.\n"
    assert "marketing" in _medium(typed)
    assert _words(typed) == _words(plain)


@_known("an autocorrected left quote on a year opens a quotation")
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


@_known("quotation marks of other languages are not blanked")
@pytest.mark.parametrize("style", sorted(NON_ENGLISH))
def test_a_quotation_in_another_languages_marks_is_blanked(style):
    open_, close = NON_ENGLISH[style]
    assert _medium(f"She wrote: {open_}{PHRASE}.{close}\n") == []


@_known("a LaTeX quotation with an apostrophe inside is not blanked")
def test_a_latex_quotation_with_an_apostrophe_inside_is_blanked():
    text = f"She wrote, ``{PHRASE.replace('this', 'it' + chr(39) + 's this')}.''\n"
    assert _medium(text) == []


@_known("csquotes enquote is not blanked")
def test_a_csquotes_enquote_is_blanked():
    assert _medium(f"She wrote, {BS}enquote{{{PHRASE}.}}\n") == []


@_known("a chatbot line quoted in guillemets blocks")
def test_a_chatbot_line_quoted_in_guillemets_does_not_block_the_default():
    text = ("The bot replied: «As an AI language model, I cannot browse "
            "the web.»\n")
    r = check_text(text, profile=DEFAULT, house_notes=False)
    assert r["gate"] == "ok", [f["label"] for f in r["high"]]
