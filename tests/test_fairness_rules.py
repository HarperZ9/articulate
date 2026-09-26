"""Rule fixtures for the fair-signals change (PLAN sections 0.3 and 2.2).

Each test pins one decision: a pattern that blocked ordinary writing now reports
without blocking outside the house pack, or a narrow pattern keeps blocking. The
house pack is a style a writer or project chooses (profiles `house` and
`house-essay`); it keeps the full ban.

These tests guard the fixes against regression. They measure nothing about
fairness. The measured effect on labeled corpora lives in the fairness receipts.
"""
import pytest

import articulate
from articulate import profiles

NON_HOUSE = ("flavored", "essay", "research", "readme", "procedure", "commit")
HOUSE = ("house", "house-essay")


def _r(text, name):
    return articulate.check_text(text if text.endswith("\n") else text + "\n",
                                 profile=profiles.load(name))


def _gating(r):
    return [(f["tier"], f["category"], f["match"]) for t in ("high", "medium", "low")
            for f in r[t] if f["gates"]]


def _cats(r, tiers=("high", "medium", "low")):
    return {f["category"] for t in tiers for f in r[t]}


# --- F1: intensifiers ------------------------------------------------------- #

@pytest.mark.parametrize("word", ["really", "actually", "truly", "genuinely"])
def test_intensifiers_report_without_blocking_outside_the_house_pack(word):
    text = f"The results were {word} clear to everyone in the room."
    for name in NON_HOUSE:
        r = _r(text, name)
        assert r["gate"] == "ok", (name, _gating(r))
        assert "intensifier" in _cats(r, ("low",)), name
    for name in HOUSE:
        assert _r(text, name)["gate"] == "blocked", name


@pytest.mark.parametrize("closing", ["Yours truly,", "Very truly yours,", "yours truly"])
def test_a_valediction_is_never_an_intensifier(closing):
    for name in NON_HOUSE + HOUSE:
        r = _r(f"Thanks for the notes.\n\n{closing}\nMaria", name)
        assert "intensifier" not in _cats(r), (name, closing)


# --- F2: the house pack ------------------------------------------------------ #

HOUSE_ONLY = {
    "em-dash": "The survey ran twice — once in May.",
    "spaced en dash": "The survey ran twice – once in May.",
    "rather than": "We used paper forms rather than tablets.",
    "instead": "We used paper forms instead of tablets.",
    "not X but Y": "The delay was not a bug but a choice.",
    "corrective negation": "The team met on Friday, not the Monday before.",
    "never always": "He never calls and always texts.",
    "corporate verb": "We leverage the new data to plan the route.",
}


@pytest.mark.parametrize("label", sorted(HOUSE_ONLY))
def test_house_patterns_block_only_under_a_house_profile(label):
    text = HOUSE_ONLY[label]
    for name in NON_HOUSE:
        r = _r(text, name)
        assert r["gate"] == "ok", (label, name, _gating(r))
    for name in HOUSE:
        assert _r(text, name)["gate"] == "blocked", (label, name)


def test_house_findings_are_marked_as_house():
    r = _r("We used paper forms rather than tablets.", "flavored")
    (f,) = [f for f in r["low"] if f["category"] == "substitution"]
    assert f["house"] is True and f["gates"] is False


def test_wordiness_is_medium_with_a_reason():
    r = _r("We met early in order to plan the route.", "flavored")
    assert r["gate"] == "ok"
    assert "wordiness" in _cats(r, ("medium",))
    assert _r("We met early in order to plan the route.", "essay")["gate"] == "blocked"


def test_no_path_rule_resolves_to_a_house_profile():
    for _rx, name in profiles.PATH_RULES:
        assert name not in profiles.HOUSE_PROFILES, name


def test_essay_paths_resolve_to_the_non_house_essay():
    for path in ("essays/a.md", "blog/b.md", "writing/c.md", "thesis.tex"):
        prof = profiles.load(profiles.profile_for(path))
        assert not prof.get("house"), path


# --- F3: affirmation openers and self-identification ------------------------ #

@pytest.mark.parametrize("text", ["Of course, the survey ran twice in May.",
                                  "Absolutely. We can meet on Friday.",
                                  "Good question! The build caches responses."])
def test_a_spoken_affirmation_reports_without_blocking(text):
    for name in NON_HOUSE:
        r = _r(text, name)
        assert r["gate"] == "ok", (name, _gating(r))
    assert "affirmation-opener" in _cats(_r(text, "flavored"), ("low",))


def test_an_affirmation_that_hands_over_a_deliverable_blocks_in_a_document():
    r = _r("Certainly! Here is your essay:\n\nThe rain fell.", "essay")
    assert r["gate"] == "blocked"
    assert "reply-opener" in _cats(r, ("low",))


ARTICLE_2_12 = ("Open-source systems are exempt unless they are placed on the market or "
                "put into service as high-risk AI systems or as an AI system that falls "
                "under Article 5 or 50.")


def test_quoting_the_ai_act_raises_nothing():
    for name in NON_HOUSE + HOUSE:
        r = _r(ARTICLE_2_12, name)
        assert "chat-interface-text" not in _cats(r), name


def test_first_person_self_identification_still_blocks():
    for text in ("As an AI language model, I cannot give medical advice.",
                 "I'm an AI, so I cannot see the file.",
                 "As a large language model, I cannot browse."):
        r = _r(text, "flavored")
        assert r["gate"] == "blocked", text


# Human lines that the old self-identification and reply-opener rules blocked
# under the default profile. None may block there; the reply openers block only
# under a document profile that promotes them.
HUMAN_CONTROLS = (
    "As an assistant, I managed the calendars for four partners.",
    "We held out ten percent of my training data for the test split.",
    "I don't have real-time access to the production logs from home.",
    "Sure thing! Here's the spreadsheet you asked for.",
    "Of course! Here is the report you wanted by Friday.",
    "Absolutely. I've drafted the letter to the landlord.",
    "Good question! Here's how I fixed it.",
)


@pytest.mark.parametrize("text", HUMAN_CONTROLS)
def test_ordinary_human_lines_never_block_under_the_default(text):
    r = _r(text, "flavored")
    assert r["gate"] == "ok", _gating(r)
    assert "chat-interface-text" not in _cats(r)


def test_a_reply_opener_blocks_only_under_a_document_profile():
    text = "Certainly! Here is your essay:\n\nThe rain fell."
    assert _r(text, "flavored")["gate"] == "ok"
    assert "reply-opener" in _cats(_r(text, "flavored"), ("low",))
    for name in ("essay", "house", "house-essay"):
        assert _r(text, name)["gate"] == "blocked", name


# --- F4: zero-width characters ---------------------------------------------- #

SCRIPTS = {
    "thai": "ภาษา​ไทย",
    "khmer": "ភាសា​ខ្មែរ",
    "lao": "ພາສາ​ລາວ",
    "myanmar": "မြန်​မာ",
}


@pytest.mark.parametrize("script", sorted(SCRIPTS))
def test_zero_width_space_in_a_non_latin_script_does_not_block(script):
    r = _r(f"The phrase {SCRIPTS[script]} appears in the survey.", "flavored")
    assert r["gate"] == "ok", _gating(r)
    assert "invisible-unicode" in _cats(r, ("low",))


def test_zwnj_in_persian_raises_nothing():
    r = _r("The word می‌خواهم means I want.", "flavored")
    assert "invisible-unicode" not in _cats(r)


def test_zero_width_space_between_latin_letters_blocks():
    r = _r("This line hides a​zero-width space between two words.", "flavored")
    assert r["gate"] == "blocked"
    assert "invisible-unicode" in _cats(r, ("high",))


# --- typography and input method -------------------------------------------- #

def test_typography_never_blocks_outside_the_house_pack():
    texts = ["我们开会，然后回家。",
             "“Quoted,” she said. ‘Yes.’",
             "Pages 10–12 and 1990–2000 cover it.",
             "It rained—a lot—that week."]
    for text in texts:
        for name in NON_HOUSE:
            assert _r(text, name)["gate"] == "ok", (text, name)


# --- F5: structural regularity ---------------------------------------------- #

def test_ordinal_enumeration_and_stock_transitions_report_only():
    text = ("Firstly, the survey is short. Secondly, it is cheap. Moreover, it "
            "runs offline. Furthermore, it is free.")
    for name in NON_HOUSE:
        r = _r(text, name)
        assert r["gate"] == "ok", (name, _gating(r))


def test_nine_short_even_sentences_are_not_uniform_cadence():
    text = " ".join(f"The team met on day {i} to plan the next round of work." for i in range(9))
    r = articulate.check_text(text, profile=profiles.load("flavored"), cadence_detail=True)
    assert r["cadence"]["uniform"] is False


# --- F6: inflated words ------------------------------------------------------ #

def test_inflated_words_report_without_blocking_under_the_strict_essay():
    text = "We delve into a comprehensive and robust analysis of the landscape."
    r = _r(text, "essay")
    assert r["gate"] == "ok", _gating(r)
    assert _r(text, "house-essay")["gate"] == "blocked"


# --- other scanner fixes ----------------------------------------------------- #

def test_adverb_rate_does_not_count_intensifiers():
    r = _r("It was really good and actually fine and truly nice and genuinely calm.",
           "flavored")
    assert r["cadence"]["adverb_rate"] == 0


def test_corporate_verb_label_names_only_what_it_matches():
    from articulate import detector
    labels = [lbl for cat, lbl, _rx in detector.HIGH if cat == "corporate-verb"]
    assert labels and all("reflect" not in lbl for lbl in labels)


C2PA_TEX = ("% -----BEGIN C2PA MANIFEST----- aGVsbG8gd29ybGQ= -----END C2PA MANIFEST-----\n"
            "The rain fell for three days on the low field.\n")
C2PA_MD_COMMENT = ("<!-- -----BEGIN C2PA MANIFEST----- aGVsbG8= -----END C2PA MANIFEST----- -->\n"
                   "The rain fell for three days on the low field.\n")


@pytest.mark.parametrize("text", [C2PA_TEX, C2PA_MD_COMMENT])
def test_a_c2pa_text_manifest_raises_nothing(text):
    for name in NON_HOUSE + HOUSE:
        r = _r(text, name)
        assert not (r["high"] + r["medium"] + r["low"]), (name, _cats(r))


def test_a_variation_selector_wrapper_raises_nothing():
    payload = "".join(chr(0xFE00 + (i % 16)) for i in range(64))
    r = _r(f"The rain fell for three days.{payload} It stopped on Friday.", "house")
    assert not (r["high"] + r["medium"] + r["low"]), _cats(r)
