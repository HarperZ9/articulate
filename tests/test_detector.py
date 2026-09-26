import articulate
from articulate import profiles

SLOP = "In today's landscape, AI is not just a tool, but a force. We leverage synergy.\n"
HUMAN = ("Four score and seven years ago our fathers brought forth on this "
         "continent a new nation, conceived in Liberty.\n")


def test_spans_slice_the_matched_text():
    r = articulate.check_text(SLOP, profile=profiles.load("flavored"))
    hits = r["high"] + r["medium"] + r["low"]
    assert hits, "this text must produce findings"
    for f in hits:
        assert SLOP[f["start"]:f["end"]] == f["match"]
        assert f["rule_id"] and "/" in f["rule_id"] or f["rule_id"]


def test_profile_gating_off_flavored_strict():
    off = articulate.check_text(SLOP, profile=profiles.load("narrative"))
    flavored = articulate.check_text(SLOP, profile=profiles.load("flavored"))
    house = articulate.check_text(SLOP, profile=profiles.load("house"))
    assert off["gate"] == "ok"            # narrative gates nothing
    assert flavored["gate"] == "ok"       # the devices here are house style: reported
    assert house["gate"] == "blocked"     # the house profile gates them


def test_human_prose_is_clean():
    r = articulate.check_text(HUMAN, profile=profiles.load("flavored"))
    assert r["clean"] is True
    assert r["findings"] == "no_findings" and r["gate"] == "ok"


def test_british_english_not_flagged():
    text = ("The team organised the release whilst reviewing the colour palette "
            "amongst users.\n")
    r = articulate.check_text(text, profile=profiles.load("flavored"))
    assert r["clean"] is True, [f["match"] for f in r["high"] + r["medium"]]


def test_could_not_help_but_is_not_antithesis():
    # "could not help but" is a stock catenative, not "not X but Y". It must not
    # trip the antithesis rule in any register, while a real antithesis still does.
    idiom = articulate.check_text("She could not help but smile at the news.\n",
                                  profile=profiles.load("house-essay"))
    real = articulate.check_text("It is not a bug but a feature.\n",
                                 profile=profiles.load("house-essay"))
    assert "antithesis" not in {f["category"] for f in idiom["high"]}
    assert "antithesis" in {f["category"] for f in real["high"]}


def _register_hits(r):
    return {f["match"].lower() for t in ("high", "medium", "low") for f in r[t]
            if f["category"] == "inflated-word"}


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
    r = articulate.check_text(txt, profile=profiles.load("house"), allow=("utiliz",))
    assert "antithesis" in {f["category"] for f in r["high"]}
    assert r["gate"] == "blocked"                       # HIGH device gates
    assert "inflated-word" not in {f["category"] for f in r["medium"]}  # word still kept


def test_genuine_help_but_antithesis_is_flagged():
    caught = articulate.check_text("This tool does not exist to help but to hinder.\n",
                                   profile=profiles.load("house-essay"))
    idiom = articulate.check_text("She could not help but smile at the news.\n",
                                  profile=profiles.load("house-essay"))
    assert "antithesis" in {f["category"] for f in caught["high"]}
    assert "antithesis" not in {f["category"] for f in idiom["high"]}


def test_kept_word_raises_nothing_under_research():
    # 'comprehensive' is kept for research, so a paper is not flagged for its own
    # normal vocabulary, at any tier.
    txt = ("comprehensive " * 20) + "analysis of the corpus and the broader field of study.\n"
    research = articulate.check_text(txt, profile=profiles.load("research"))
    flavored = articulate.check_text(txt, profile=profiles.load("flavored"))
    assert _register_hits(flavored) and not _register_hits(research)


# --------------------------------------------------------------------------- #
# AI cadence tells: prose free of banned constructions that still reads as
# machine-written by its shape (demonstrative summary-beats, reply sycophancy,
# balanced ordinals, aphoristic labels, dead-metaphor connectors). Each tell has
# a positive (must fire) and a near-miss negative (must stay clean). These are
# MEDIUM, so under the flavored profile they do not gate; the assertions are on
# the finding, not the gate.
# --------------------------------------------------------------------------- #

def _cadence(text):
    r = articulate.check_text(text if text.endswith("\n") else text + "\n",
                              profile=profiles.load("house"))
    return {f["label"] for f in r["medium"] if f["category"] == "cadence"}


def _fires(text, needle):
    return any(needle in label for label in _cadence(text))


def test_cadence_demonstrative_summary_beat_fires():
    assert _fires("The check re-runs offline. That is the whole point of the design.",
                  "demonstrative summary-beat")
    assert _fires("A stranger re-runs it. That is the load-bearing part of the claim.",
                  "demonstrative summary-beat")
    assert _fires("You can automate the search. That is what makes it scale.",
                  "demonstrative summary-beat")


def test_cadence_demonstrative_near_miss_stays_clean():
    # sentence-initial "That/This is the <concrete noun>" is ordinary reference,
    # and a mid-clause "that is" is never a summary-beat.
    for s in ("That is the wrench I borrowed from Dave.",
              "This is the part where the engine stalls.",
              "That is the file you asked for.",
              "I know that is the reason he left."):
        assert not _fires(s, "demonstrative summary-beat"), s


def test_cadence_meta_acknowledgment_fires():
    assert _fires("Right, and that supports the whole picture you drew earlier.",
                  "meta-acknowledgment")
    assert _fires("I like the point you're making about receipts.", "meta-acknowledgment")
    assert _fires("What you're describing is the reproducibility gap.",
                  "meta-acknowledgment")
    assert _fires("You're onto something with the offline replay.", "meta-acknowledgment")
    assert _fires("You nailed it with the trust boundary.", "meta-acknowledgment")


def test_cadence_meta_acknowledgment_near_miss_stays_clean():
    for s in ("You're right that the deadline is tight.",   # bare 'right that'
              "I drew the map you asked for.",              # not framing praise
              "Let me know what works for you."):
        assert not _fires(s, "meta-acknowledgment"), s


def test_cadence_balanced_ordinal_fires():
    assert _fires("Most of the tooling that does the first ignores the second.",
                  "balanced ordinal")
    assert _fires("The former checks the work; the latter explains it.", "former/latter")
    assert _fires("One verifies the run, and the other reads the result.", "one/the-other")


def test_cadence_ordinal_near_miss_stays_clean():
    # an enumeration where a noun follows the ordinal is not a closing antithesis.
    ordinal_labels = {
        "balanced ordinal antithesis (the first ... the second)",
        "former/latter antithesis",
        "one/the-other antithesis (one does X, the other Y)",
    }
    for s in ("On the first day we hiked; on the second day we rested.",
              "The first bus was full, so I took the next one.",
              "One of the cats knocked it over."):
        assert not (_cadence(s) & ordinal_labels), s


def test_cadence_aphoristic_label_fires():
    assert _fires("Verification is one thing. Understanding is a separate problem.",
                  "aphoristic label")
    assert _fires("Getting it to run is the easy part.", "aphoristic label")
    assert _fires("Shipping the receipt, which is the point, comes last.", "aphoristic label")


def test_cadence_aphoristic_near_miss_stays_clean():
    for s in ("This is a hard problem to reason about.",   # 'a hard' is excluded
              "The output is a separate file on disk.",     # 'file' is not a label noun
              "I watched the whole thing twice."):          # no copula label
        assert not _fires(s, "aphoristic label"), s


def test_cadence_dead_metaphor_connector_fires():
    assert _fires("The throughline of the argument is trust.", "dead-metaphor connector")
    assert _fires("Provenance is the connective tissue between the tools.",
                  "dead-metaphor connector")


def test_cadence_dead_metaphor_near_miss_stays_clean():
    assert not _fires("The connective rod links the two gears.", "dead-metaphor connector")


def test_cadence_tell_is_allowlist_exempt():
    # 'load-bearing' is a kept term of art (profiles._TERMS), but a summary-beat
    # built on it is a structural pattern and must still fire despite the allowlist.
    r = articulate.check_text(
        "A stranger re-runs the checks. That is the load-bearing part of the claim.\n",
        profile=profiles.load("house"))
    assert "cadence" in {f["category"] for f in r["medium"]}


def test_cadence_human_controls_stay_clean():
    # plain, concrete, offhand human sentences with none of the tells.
    controls = [
        "I fixed the leaky faucet yesterday and it still drips a little.",
        "The bus was late again so I walked the last mile home.",
        "She said the meeting moved to three, so I rescheduled the call.",
        "On the first day we drove to the coast; on the second day we hiked.",
        "That is the wrench I borrowed from Dave last weekend.",
        "This is the part where the engine usually stalls out.",
        "You're right that the deadline is tight, but we can split it.",
        "One of the dogs barked all night. The other one slept through it.",
    ]
    for c in controls:
        r = articulate.check_text(c + "\n", profile=profiles.load("flavored"))
        assert r["clean"], (c, [f["match"] for f in r["high"] + r["medium"]])


def test_cadence_canonical_example_is_not_clean():
    # the shipped draft that motivated the tells: no banned construction, yet it
    # reads as machine-written. It must now report a MEDIUM cadence tell.
    panos = ("The third tribe only works if the reproducibility package is real: a "
             "stranger re-runs the checks and gets the same verdict without trusting "
             "the authors or the reviewer. That is the load-bearing part of the whole "
             "picture you drew.\n")
    r = articulate.check_text(panos, profile=profiles.load("house"))
    assert r["clean"] is False
    assert any(f["category"] == "cadence" for f in r["medium"])
