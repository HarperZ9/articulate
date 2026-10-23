"""Built-in intent specs and the words that steer a new one.

A spec says what a draft must do and what it must leave out, in terms the
checker can measure: device limits, wanted moves and a few ranges. The
`zain` spec turns the author's standing prose rules into those terms and adds
his stated stance for posts: contrarian, polemical, asking what if and trying
the other person's shoes before judging.
"""
SCHEMA = "articulate/voice-intent/v1"

TELL_WHY = {
    "one-line-paragraphs": "a post built from one-sentence paragraphs reads as a template",
    "anaphora-run": "parallel openers hammer instead of explain",
    "epistrophe-run": "parallel endings hammer instead of explain",
    "fragment-run": "a run of fragments is rhythm with no claim in it",
    "tricolon": "a rule of three is rhythm, and the reader hears it",
    "split-antithesis": "a contrasting pair spends a sentence on what the thing is not",
    "aphorism-line": "a maxim on its own line is a landing sentence",
    "closing-maxim": "ending on a maxim tells the reader what to think",
    "numbered-escalation": "First:, Second:, Third: is a setup that delays the claim",
    "colon-drumroll": "a colon reveal is setup and payoff",
    "reveal-setup": "a stock reveal phrase is throat-clearing",
    "house-devices": "the line checker's devices: antithesis, em-dash, filler, corporate verbs",
    "hedge": "a hedge asks the reader to do the deciding",
}

WORK_HOW = {
    "anchor": "Open on something a reader can check: a date, a number, a quote with its source.",
    "counter-view": "Name the view you are pushing against, in words its holder would sign.",
    "other-shoes": "Spend a sentence on their side: how the thing looks from where they stand.",
    "what-if": "Ask what if: change one fact and see whether the conclusion survives.",
    "stance": "Say what you think, in the first person, with no hedge.",
    "turn": "Turn once, at the place the evidence stops agreeing with the easy reading.",
    "reader-question": "End on a question the reader has to answer, in place of a maxim.",
    "tool": "Name the tool and the command once, plainly, where it helps the reader do the check.",
}

DEFAULT_LIMITS = {k: 0 for k in TELL_WHY}
DEFAULT_LIMITS["hedge"] = 2
DEFAULT_RANGES = {"sentence_len_cv": {"min": 0.35}}

# Words in --goal or --stance that add a wanted move. Matching is by substring.
GOAL_WANTS = (
    (("persuade", "argue", "post", "opinion", "op-ed", "thread", "essay"),
     ("anchor", "turn", "reader-question")),
    (("explain", "teach", "guide", "document", "docs", "tutorial", "how-to"), ("anchor",)),
    (("market", "launch", "announce", "promote", "sell", "release", "readme"), ("anchor", "tool")),
)
STANCE_WANTS = (
    (("contrarian", "counter", "skeptic", "sceptic"), ("counter-view", "turn")),
    (("what if", "what-if", "hypothetical"), ("what-if",)),
    (("shoes", "other side", "empath", "their side", "steelman"), ("other-shoes",)),
    (("polemic", "direct", "blunt", "first person", "first-person", "opinion"), ("stance",)),
)

ZAIN = {
    "schema": SCHEMA,
    "name": "zain",
    "goal": "Posts and short essays that change how a reader checks a claim, and that point at "
            "the tools that make checking cheap.",
    "audience": "Smart, busy readers on X and the site who are not specialists.",
    "stance": "Contrarian and polemical. Asks what if. Tries the other person's shoes before "
              "judging. First person. Pragmatic and clear; it does not have to be ASD-STE.",
    "traits": [
        "Technical English that is easy to read, written for the spoken voice.",
        "Sentence length varies; no two sentences in a paragraph share a frame.",
        "No antithesis, corrective negation, contrasting pairs or negative parallels.",
        "No rule of three, no anaphora, no setup and payoff, no landing or summary sentence.",
        "No em-dashes, filler intensifiers, corporate verbs, hedges or throat-clearing.",
        "No performed enthusiasm. Every claim has something a reader can check.",
        "Picks a side and says so in the first person, after trying the other side.",
    ],
    "limits": dict(DEFAULT_LIMITS, hedge=0),
    "wants": {k: 1 for k in ("anchor", "counter-view", "other-shoes", "what-if", "stance", "turn",
                             "reader-question")},
    "ranges": {"sentence_len_cv": {"min": 0.4}},
    "sources": {"rules": "the author's standing prose-style rules (2026-08-04) and his stated "
                         "stance for posts (2026-10-23)", "samples": []},
}

BUILTIN = {"zain": ZAIN}
