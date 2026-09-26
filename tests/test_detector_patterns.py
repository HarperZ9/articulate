"""Pattern coverage: the delivery, structural, lexical and formatting rules, with
near-miss controls. Split from test_detector.py to keep each file under 300 lines.
"""
import articulate
from articulate import profiles


def _cadence(text):
    r = articulate.check_text(text if text.endswith("\n") else text + "\n",
                              profile=profiles.load("house"))
    return {f["label"] for f in r["medium"] if f["category"] == "cadence"}


def _fires(text, needle):
    return any(needle in label for label in _cadence(text))


# Each HIGH rule and MEDIUM category has a positive; the trickier ones have a
# near-miss negative; a human-control corpus stays clean of HIGH and MEDIUM.

def _hm(text, name="house"):
    r = articulate.check_text(text if text.endswith("\n") else text + "\n",
                              profile=profiles.load(name))
    return {(f["tier"], f["category"]) for f in r["high"] + r["medium"]}


def _has_cat(text, category):
    return any(c == category for _t, c in _hm(text))


# --- new HIGH tells (mechanically unambiguous) ------------------------------ #

def test_high_ai_self_disclosure():
    assert ("HIGH", "chat-interface-text") in _hm(
        "As an AI language model, I cannot provide medical advice here.")
    assert ("HIGH", "chat-interface-text") in _hm(
        "As a language model, I do not have access to prices.")
    assert not _has_cat("As of my last knowledge update, the prices were lower.",
                        "chat-interface-text")


def test_high_leaked_markup_token():
    assert ("HIGH", "chat-interface-text") in _hm(
        "The finding held :contentReference[oaicite:0]{index=0} across every run.")


def test_high_invisible_unicode():
    assert ("HIGH", "invisible-unicode") in _hm(
        "This line hides a​zero-width space between two ordinary words.")
    assert not _has_cat("This line has only ordinary spaces between words.",
                        "invisible-unicode")


def test_high_affirmation_opener_extended():
    # A spoken affirmation alone reports at LOW, and so does a reply opener that
    # hands over a deliverable; a document profile promotes the second.
    r = articulate.check_text("Good question! Here is the answer you asked for.")
    assert "reply-opener" in {f["category"] for f in r["low"]}
    assert not _has_cat("Good question! The build caches responses.", "chat-interface-text")
    assert not _has_cat("Good tooling makes the difference on a long project.",
                        "chat-interface-text")


# --- new MEDIUM tells: one positive per new category ------------------------ #

MEDIUM_POSITIVES = {
    "sycophancy": "That is a great question, and it gets at the core tradeoff.",
    "closing-boilerplate": "The config lives in one file. I hope this helps you get unstuck.",
    "delivery": "Setup takes two commands. Don't worry, it is simpler than it sounds.",
    "over-apology": "I apologize for the confusion in my earlier note about the flags.",
    "disclaimer": "The deduction may apply. This is not financial advice, of course.",
    "evasive": "People ask which to pick. There is no one-size-fits-all answer.",
    "meta": "The pipeline has three stages. Let's break it down stage by stage.",
    "scaffold": "By the end of this guide, you will have a running verifier.",
    "reveal": "The kicker: the whole run reproduces offline with no network.",
    "throat-clearing": "It is worth noting that the benchmark shows no accuracy gain.",
    "antithesis": "This isn't about speed, it is about whether you can check it.",
    "setup": "The receipt is more than just a log line for the pipeline output.",
    "both-sides": "On the one hand it is fast; on the other hand it drops cases.",
    "closer": "Simply put, the verifier trusts arithmetic and nothing else.",
    "enumeration": "Firstly, it scales cleanly. Secondly, the cost stays flat.",
    "rhetorical-we": "We have all been there, staring at a build that only fails in CI.",
    "cta": "Looking for a verifier you can trust? Look no further than this one.",
    "continuation-cliche": "The framework continues to captivate a devoted audience.",
    "significance": "The release marks a pivotal moment for reproducible evaluation.",
    "emoji-structure": "## \U0001F680 Getting Started",
}


def test_medium_positives_fire_by_category():
    for category, text in MEDIUM_POSITIVES.items():
        cats = {c for _t, c in _hm(text)}
        assert category in cats, (category, text, cats)


def test_medium_reveal_and_meta_variants():
    # contracted and expanded copulas both fire (recall, no precision cost)
    assert _has_cat("Here is the kicker: it needs no trust at all.", "reveal")
    assert _has_cat("And here is where it gets interesting: the check runs twice.", "reveal")
    assert _has_cat("As we have seen, provenance travels with the work.", "meta")
    assert _has_cat("You might be wondering why the verifier ignores the model.", "meta")
    assert _has_cat("And that is why the receipt matters more than the verdict.", "closer")


# --- near-miss negatives for the tighter new tells -------------------------- #

def test_new_tells_near_miss_stay_clean():
    negatives = [
        "That is the file you asked for last week.",        # not a summary label
        "You are right, we should ship it today.",          # bare agreement, no flattery adj
        "It depends on the soil type and the season.",      # not the one-size template
        "Let me know if the schedule works for everyone.",  # human closer -> LOW only
        "Feel free to swing by after five.",                # human -> LOW only
        "Despite the delay, the release still went out.",   # concessive -> LOW only
        "The more we tested, the more confident we felt.",  # correlative -> LOW only
        "This is a hard problem we spent a week on.",        # 'a hard' excluded
        "That's why I always test on a clean install.",      # no and/so prefix
    ]
    for s in negatives:
        assert not _hm(s, "flavored"), (s, _hm(s, "flavored"))


# --- false-positive control corpus (>= 20 varied human snippets) ------------ #

HUMAN_CONTROLS = [
    "I fixed the leaky faucet yesterday and it still drips a little.",
    "The bus was late so I walked the last mile home. My feet are killing me.",
    "She said the meeting moved to three, so I rescheduled the call.",
    "One of the cats knocked the plant off the sill again.",
    "Honestly the whole thing took longer than I expected, but we got it done.",
    "You're right, let's grab lunch after the standup.",
    "On the first day we drove to the coast; on the second day we hiked.",
    "That is the wrench I borrowed from Dave last weekend.",
    "This is the part where the engine usually stalls out.",
    "Despite the rain, the game went ahead and we lost badly.",
    "The more I read the manual, the more confused I got.",
    "Let me know what time works and I'll book the room.",
    "Feel free to swing by after five; the door is open.",
    "We tried the new build on Linux and it segfaulted on startup.",
    "The ticket says the export fails when the file has a BOM.",
    "First, unplug the router. Wait ten seconds. Plug it back in.",
    "The paper argues that soil carbon is underestimated in current models.",
    "Both options work; I lean toward the cheaper one for now.",
    "It depends on the soil, but most tomatoes want full sun.",
    "He parked the truck, grabbed the chainsaw, and headed for the oak.",
    "My grandfather watched the rain from the porch and said nothing.",
    "Thanks for the quick turnaround. The invoice looks right to me.",
]


def test_human_control_corpus_stays_clean():
    assert len(HUMAN_CONTROLS) >= 20
    for c in HUMAN_CONTROLS:
        r = articulate.check_text(c + "\n", profile=profiles.load("flavored"))
        assert r["clean"], (c, [f["match"] for f in r["high"] + r["medium"]])


# --- statistical advisories are report-only (never gate, never flag) -------- #

def test_statistical_advisories_are_low_only():
    doc = ("Overview of the options.\n\n"
           "- item one here\n- item two here\n- item three here\n"
           "- item four here\n- item five here\n- item six here\n\n"
           "The system reads files. The system writes receipts. The system checks them.\n")
    r = articulate.check_text(doc, profile=profiles.load("flavored"))
    low_cats = {f["category"] for f in r["low"]}
    assert r["clean"] is True                       # advisories never gate or flag
    assert low_cats & {"list-reflex", "anaphora"}   # but an advisory did fire


# --------------------------------------------------------------------------- #
# Cadence residuals (ruleset 0.5.0): three tells that 0.4.0 read as clean. The
# demonstrative "That is the <X> half" shape extends an existing MEDIUM cadence
# tell; the two-imperative slogan and the evaluative fragment opener are LOW,
# because they fire on innocent prose too (an ordinary imperative pair, a human
# punchy fragment). Each has a positive and a near-miss negative, and a >= 25
# snippet human control corpus must gain no HIGH or MEDIUM.
# --------------------------------------------------------------------------- #

def _low_fires(text, category):
    r = articulate.check_text(text if text.endswith("\n") else text + "\n",
                              profile=profiles.load("flavored"))
    return any(f["category"] == category for f in r["low"])


def test_demonstrative_half_extension_fires():
    # the residual line that motivated the extension: "the run half" (a curated
    # noun after an arbitrary modifier) now reads as a MEDIUM cadence tell.
    assert _fires("A log an agent cannot rewrite. That is the run half of trust.",
                  "demonstrative summary-beat")
    for s in ("That is the other side of the coin.",
              "That is the missing piece.",
              "This is the base layer of the stack.",
              "That is the interesting angle.",
              "That is the whole story.",
              "This is the clever trick.",
              "That is the story of the whole project."):
        assert _fires(s, "demonstrative summary-beat"), s


def test_demonstrative_half_extension_near_miss_stays_clean():
    # a compound noun (another noun follows the curated word) or a concrete noun
    # is not a summary-beat, so "That is the side effect" / "the file" stay clean.
    for s in ("That is the side effect we were worried about.",
              "This is the side project I mentioned.",
              "That is the story we tell new hires.",
              "That is the file we need.",
              "This is the part where the engine stalls."):
        assert not _fires(s, "demonstrative summary-beat"), s


def test_imperative_pair_is_low_advisory_only():
    text = "Attest the run, re-derive the answer.\n"
    r = articulate.check_text(text, profile=profiles.load("flavored"))
    assert _low_fires("Attest the run, re-derive the answer.", "imperative-pair")
    assert r["clean"] is True                    # LOW never gates or flags
    assert not any(f["category"] == "imperative-pair"
                   for f in r["high"] + r["medium"])
    # an ordinary imperative pair fires the same advisory (that is why it is LOW).
    assert _low_fires("Open the door, grab the keys.", "imperative-pair")


def test_imperative_pair_near_miss_stays_clean():
    # a declarative subject (pronoun / determiner opener) or a three-clause list
    # is not a bare two-imperative slogan.
    for s in ("He parked the truck, grabbed the chainsaw, and left.",
              "The report covers the data, and the analysis follows.",
              "I opened the box, and the manual was missing.",
              "We tested the build, it crashed on startup."):
        assert not _low_fires(s, "imperative-pair"), s


def test_fragment_opener_is_low_advisory_only():
    for s in ("Strong foundation.", "Solid foundation.", "Clean architecture."):
        r = articulate.check_text(s + "\n", profile=profiles.load("flavored"))
        assert _low_fires(s, "fragment-opener"), s
        assert r["clean"] is True
        assert not any(f["category"] == "fragment-opener"
                       for f in r["high"] + r["medium"])


def test_fragment_opener_is_paragraph_initial_only():
    para_start = "Solid design.\n\nThe rest of the system builds on it cleanly.\n"
    r = articulate.check_text(para_start, profile=profiles.load("flavored"))
    assert any(f["category"] == "fragment-opener" for f in r["low"])
    # a fragment mid-paragraph (previous line is prose, not blank) is a style
    # choice, not the machine opener this catches.
    mid = "The design took three weeks to settle.\nSolid design.\n"
    r2 = articulate.check_text(mid, profile=profiles.load("flavored"))
    assert not any(f["category"] == "fragment-opener" for f in r2["low"])


def test_fragment_opener_near_miss_stays_clean():
    # a full sentence (a verb follows the noun) is not a fragment; a non-summary
    # noun ("morning", "work") never fires whatever the adjective.
    for s in ("Good morning.", "Nice work.", "Solid work today, everyone.",
              "Strong foundations take time to build properly.",
              "The foundation is strong and the tests pass."):
        assert not _low_fires(s, "fragment-opener"), s


# A dedicated control corpus for the three residual tells, including the
# deliberate near-misses named in the change request. None may gain a HIGH or a
# MEDIUM finding; a LOW advisory on an ordinary imperative pair is acceptable.
NEW_TELL_CONTROLS = [
    "That is the file we need.",
    "That is the file you asked for last week.",
    "Open the door, grab the keys.",
    "Good morning.",
    "Nice work.",
    "Solid work today, everyone.",
    "That is the side effect we were worried about.",
    "This is the side project I mentioned.",
    "That is the story we tell new hires.",
    "This is the part where the engine stalls.",
    "That is the wrench I borrowed from Dave.",
    "He parked the truck, grabbed the chainsaw, and headed for the oak.",
    "First, unplug the router. Wait ten seconds. Plug it back in.",
    "I opened the box, and the manual was missing.",
    "The report covers the data, and the analysis follows next week.",
    "We tested the build, it segfaulted on startup.",
    "Morning.",
    "Thanks again.",
    "See you tomorrow.",
    "The foundation is strong and the tests pass.",
    "Strong foundations take time to build properly.",
    "I fixed the leaky faucet yesterday and it still drips a little.",
    "On the first day we drove to the coast; on the second day we hiked.",
    "It depends on the soil, but most tomatoes want full sun.",
    "Both options work; I lean toward the cheaper one for now.",
    "Great progress on the migration this week, thanks all.",
]


def test_new_tell_control_corpus_no_high_or_medium():
    assert len(NEW_TELL_CONTROLS) >= 25
    for c in NEW_TELL_CONTROLS:
        r = articulate.check_text(c + "\n", profile=profiles.load("flavored"))
        hm = [(f["tier"], f["category"], f["match"]) for f in r["high"] + r["medium"]]
        assert not hm, (c, hm)
