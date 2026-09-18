import articulate
from articulate import profiles

SLOP = "In today's landscape, AI is not just a tool, but a force. We leverage synergy.\n"
HUMAN = ("Four score and seven years ago our fathers brought forth on this "
         "continent a new nation, conceived in Liberty.\n")


def test_spans_slice_the_matched_text():
    r = articulate.check_text(SLOP, profile=profiles.load("flavored"))
    hits = r["high"] + r["medium"]
    assert hits, "slop must produce findings"
    for f in hits:
        assert SLOP[f["start"]:f["end"]] == f["match"]
        assert f["rule_id"] and "/" in f["rule_id"] or f["rule_id"]


def test_profile_gating_off_flavored_strict():
    off = articulate.check_text(SLOP, profile=profiles.load("narrative"))
    flavored = articulate.check_text(SLOP, profile=profiles.load("flavored"))
    strict = articulate.check_text(SLOP, profile=profiles.load("essay"))
    assert off["gate"] == "ok"            # narrative gates nothing
    assert flavored["gate"] == "blocked"  # HIGH devices present
    assert strict["gate"] == "blocked"


def test_human_prose_is_clean():
    r = articulate.check_text(HUMAN, profile=profiles.load("flavored"))
    assert r["clean"] is True
    assert r["texture_score"] == 0


def test_british_english_not_flagged():
    text = ("The team organised the release whilst reviewing the colour palette "
            "amongst users.\n")
    r = articulate.check_text(text, profile=profiles.load("flavored"))
    assert r["clean"] is True, [f["match"] for f in r["high"] + r["medium"]]


def test_could_not_help_but_is_not_antithesis():
    # "could not help but" is a stock catenative, not "not X but Y". It must not
    # trip the antithesis rule in any register, while a real antithesis still does.
    idiom = articulate.check_text("She could not help but smile at the news.\n",
                                  profile=profiles.load("essay"))
    real = articulate.check_text("It is not a bug but a feature.\n",
                                 profile=profiles.load("essay"))
    assert "antithesis" not in {f["category"] for f in idiom["high"]}
    assert "antithesis" in {f["category"] for f in real["high"]}


def _register_hits(r):
    return {f["match"].lower() for f in r["medium"] if f["category"] == "register-word"}


def test_esl_formal_words_kept_in_research_register():
    # P0-b: utilize/facilitate/comprehensive are ordinary in scholarly writing.
    # They flag under a general register and are kept under the research register.
    txt = "We utilize a comprehensive method to facilitate the analysis.\n"
    research = articulate.check_text(txt, profile=profiles.load("research"))
    flavored = articulate.check_text(txt, profile=profiles.load("flavored"))
    esl = {"utilize", "comprehensive", "facilitate"}
    assert not (_register_hits(research) & esl), _register_hits(research)
    assert _register_hits(flavored) & esl
    assert research["clean"] is True


def test_esl_words_kept_under_academic_mode():
    from articulate import modes
    txt = "We utilize a comprehensive framework to facilitate reproducibility.\n"
    r = articulate.check_text(txt, profile=modes.load("academic/explain"))
    assert r["clean"] is True, [f["match"] for f in r["high"] + r["medium"]]


def test_keep_does_not_suppress_a_real_device():
    # A kept register word inside a device's wide span must not un-flag the device.
    txt = "This method does not utilize legacy protocols, but replaces them.\n"
    r = articulate.check_text(txt, profile=profiles.load("research"))
    assert "antithesis" in {f["category"] for f in r["high"]}
    assert r["gate"] == "blocked"                       # HIGH device gates
    assert "register-word" not in {f["category"] for f in r["medium"]}  # word still kept


def test_genuine_help_but_antithesis_is_flagged():
    caught = articulate.check_text("This tool does not exist to help but to hinder.\n",
                                   profile=profiles.load("essay"))
    idiom = articulate.check_text("She could not help but smile at the news.\n",
                                  profile=profiles.load("essay"))
    assert "antithesis" in {f["category"] for f in caught["high"]}
    assert "antithesis" not in {f["category"] for f in idiom["high"]}


def test_kept_word_does_not_inflate_texture_under_research():
    # 'comprehensive' is kept for research, so it must not count toward texture
    # either; a clean paper is not scored elevated on its own normal vocabulary.
    txt = ("comprehensive " * 20) + "analysis of the corpus and the broader field of study.\n"
    research = articulate.check_text(txt, profile=profiles.load("research"))
    flavored = articulate.check_text(txt, profile=profiles.load("flavored"))
    assert flavored["texture_score"] > research["texture_score"]
    assert research["elevated"] is False
