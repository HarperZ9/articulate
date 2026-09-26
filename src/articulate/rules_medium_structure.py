#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.rules_medium_structure -- MEDIUM rules over sentence shape.

Summary beats, reply templates, reveals, framing pivots and puffery frames.
Standard library only.
"""
import re

MEDIUM_STRUCTURE = [
    # --- cadence beats (house pack) --------------------------------------- #
    # Sentence shapes that restate or label a point in place of adding one. They
    # are one writer's house style, so only a house profile gates them. Anything
    # that would fire on ordinary prose (bare "the first", ordinary "that is") is
    # excluded or moved to LOW.
    #
    # A summary-beat is a structural device, not a vocabulary choice, so the
    # "cadence" category is exempt from the terms-of-art allowlist (see
    # ALLOW_EXEMPT_CATEGORIES): "That is the load-bearing part" is a summary-beat
    # whether or not "load-bearing" is a kept term of art elsewhere.
    #
    # 1. Demonstrative summary-beat: a sentence that labels the prior point
    #    ("That is the load-bearing part", "This is the whole point", "That is what
    #    makes it work"). Anchored to a sentence boundary (line start or after
    #    .!?) so ordinary mid-clause "that is" does not fire, and the object is a
    #    curated set of summary labels so "This is the file I need" does not fire.
    #    A fourth branch adds the "That is the <X> half" shape: a curated noun set
    #    (half, side, piece, layer, angle, story, trick) after an optional single
    #    modifier word, closed by end-of-clause or "of" so "That is the side
    #    effect" (a compound noun, another noun follows) does not fire. "whole
    #    game" is already covered by the second branch.
    ("cadence", "demonstrative summary-beat (That is the ...)",
     re.compile(r"(?i)(?:^|[.!?]\s+)(?:that|this)(?:'s|’s|\s+(?:is|was))\s+"
                r"(?:what\s+(?:makes|matters|counts|does|gives|keeps|separates|"
                r"drives|holds|lets|allows|breaks)\b"
                r"|the\s+(?:crux|kicker|takeaway|whole\s+point|whole\s+game|"
                r"hard\s+part|easy\s+part)\b"
                r"|the\s+(?:whole|entire|actual|central|core|crucial|essential|"
                r"load[- ]bearing)\s+(?:point|problem|part|piece|question|issue|"
                r"reason|insight|tension|idea|thing|layer|catch|danger|risk|"
                r"trick|move|bit)\b"
                r"|the\s+(?:\w+\s+)?(?:half|side|piece|layer|angle|story|trick)\b"
                r"(?=\s*(?:[.,;:!?]|of\b|$)))")),
    # 2. Meta-acknowledgment of the interlocutor (reply sycophancy): restating or
    #    praising the other person's framing ("the whole picture you drew", "the
    #    point you're making", "what you're describing", "you're onto something",
    #    "you nailed it", "you're absolutely right").
    ("cadence", "meta-acknowledgment of interlocutor (reply sycophancy)",
     re.compile(r"(?i)"
                r"\bthe\s+(?:whole\s+|entire\s+|exact\s+|very\s+)?"
                r"(?:picture|point|framing|frame|world|model|story|argument|thread|"
                r"distinction|vision|map|case|diagnosis|analogy|metaphor|setup)\s+"
                r"(?:that\s+)?you(?:'re|’re|\s+are|'ve|’ve|\s+have|\s+just)?"
                r"\s+(?:drew|draw|drawing|described|describing|laid\s+out|"
                r"laying\s+out|painting|painted|paint|making|made|make|outlined|"
                r"outlining|sketched|sketching|set\s+out|raised|raising|"
                r"getting\s+at|pointing\s+(?:to|at))\b"
                r"|\bwhat\s+you(?:'re|’re|\s+are|'ve|’ve|\s+have)\s+"
                r"(?:describing|getting\s+at|pointing\s+(?:to|at)|driving\s+at|"
                r"after|onto|really\s+saying|circling)\b"
                r"|\byou(?:'re|’re|\s+are)\s+(?:really\s+|absolutely\s+|"
                r"totally\s+|clearly\s+)?onto\s+something\b"
                r"|\byou(?:'ve|’ve|\s+have)\s+(?:really\s+)?nailed\s+"
                r"(?:it|this|that)\b"
                r"|\byou\s+nailed\s+(?:it|this|that)\b"
                r"|\byou(?:'re|’re|\s+are)\s+(?:absolutely|exactly|completely|"
                r"totally|so)\s+right\b")),
    # 3. Balanced ordinal/antithetical closer: two abstract ordinals used as a neat
    #    closing generalization ("does the first ... ignores the second", "the
    #    former ... the latter", "one does X, the other Y"). The "second" must
    #    close a clause (bare, punctuation next), so an enumeration like "the first
    #    day ... the second day" (a noun follows) does not fire.
    ("cadence", "balanced ordinal antithesis (the first ... the second)",
     re.compile(r"(?i)\bthe\s+first\b[^.\n]{1,70}?\bthe\s+second\b"
                r"(?=\s*[.,;:!?)\]”’\"']|\s*$)")),
    ("cadence", "former/latter antithesis",
     re.compile(r"(?i)\bthe\s+former\b[^.\n]{1,70}?\bthe\s+latter\b")),
    ("cadence", "one/the-other antithesis (one does X, the other Y)",
     re.compile(r"(?i)\bone\s+(?:does|did|says|said|is|was|handles|solves|takes|"
                r"gets|goes|makes|gives|checks|verifies|understands|wins|leads|"
                r"works|covers|answers)\b[^.\n]{0,55}?,\s+(?:while\s+|whereas\s+|"
                r"and\s+|but\s+)?the\s+other\b")),
    # 4. Aphoristic label: naming a thing with a stock generalization ("X is a
    #    separate problem", "X is the hard part", "that is the whole point",
    #    "which is the point"). The noun set is curated so "This is a hard problem"
    #    (a-branch excludes "hard") does not fire.
    ("cadence", "aphoristic label (a separate problem / the hard part)",
     re.compile(r"(?i)\b(?:is|are|was|were|remains?|becomes?)\s+"
                r"(?:a\s+(?:separate|different|distinct|whole\s+other|"
                r"whole\s+different)\s+(?:problem|question|issue|matter|beast|"
                r"story|animal|game)"
                r"|the\s+(?:hard|easy|tricky|fun|whole|entire)\s+"
                r"(?:part|bit|point|game))\b"
                r"|\bwhich\s+is\s+(?:rather\s+|exactly\s+|precisely\s+|"
                r"kind of\s+)?the\s+point\b")),
    # 5. Dead-metaphor connector that names a link without saying what it is. "load-bearing" (as summary
    #    metaphor) is caught by the summary-beat above; "at its core" is a HIGH
    #    throat-clearing opener already. These two are the remaining connectors.
    ("cadence", "dead-metaphor connector (throughline / connective tissue)",
     re.compile(r"(?i)\b(?:the\s+)?through[- ]?line\b|\bconnective\s+tissue\b")),

    # ===================================================================== #
    # Reply templates, scaffolding, reveals, framing pivots and puffery frames.
    # Deduped against every entry above. Single dual-use words are not here (they
    # live in the inflated-word lists); formatting and density signals that fire
    # on ordinary prose are LOW advisories. Which of these gate outside the house
    # pack is set in rule_reasons.
    # ===================================================================== #

    # --- reply and closer phrases ----------------------------------------- #
    ("sycophancy", "sycophantic flattery of the interlocutor",
     re.compile(r"(?i)\b(?:that|this)(?:'s| is)\s+(?:a|an)\s+(?:great|excellent|"
                r"fantastic|really\s+good|very\s+good|insightful|thoughtful|"
                r"brilliant|smart|wonderful)\s+(?:point|question|idea|observation|"
                r"catch|example|call)\b")),
    ("closing-boilerplate", "boilerplate helpful closer",
     re.compile(r"(?i)\bi\s+hope\s+(?:this|that|these|the\s+above)\s+(?:helps?|"
                r"is\s+helpful|clarifies|answers?\s+your\s+question|makes\s+sense)\b"
                r"|\bhope\s+(?:this|that)\s+helps\b"
                r"|\bis\s+there\s+anything\s+else\s+(?:i\s+can\s+(?:help|assist|do)|"
                r"you'?d\s+like)\b")),
    ("delivery", "reassurance cadence",
     re.compile(r"(?i)\b(?:don'?t\s+worry|not\s+to\s+worry|worry\s+not|rest\s+assured|"
                r"the\s+good\s+news\s+is|no\s+need\s+to\s+(?:worry|panic|stress))\b")),
    ("over-apology", "reflexive over-apology template",
     re.compile(r"(?i)\bi\s+apologi[sz]e\s+for\s+(?:the|any)\s+(?:confusion|"
                r"misunderstanding|inconvenience|error|mistake|oversight)\b"
                r"|\bsorry\s+for\s+the\s+confusion\b")),
    ("disclaimer", "unsolicited not-a-professional disclaimer",
     re.compile(r"(?i)\bi'?m\s+not\s+(?:a|your)\s+(?:doctor|lawyer|attorney|"
                r"financial\s+advisor|accountant|therapist|medical\s+professional)\b"
                r"|\bthis\s+(?:is\s+not|isn'?t|should\s+not\s+be\s+considered)\s+"
                r"(?:legal|medical|financial|professional|tax|investment)\s+advice\b")),
    ("evasive", "evasive non-answer template",
     re.compile(r"(?i)\bthere(?:'s| is)\s+no\s+(?:one[- ]size[- ]fits[- ]all|"
                r"single\s+(?:right\s+|correct\s+)?answer|silver\s+bullet|"
                r"magic\s+bullet|universal\s+(?:answer|solution))\b")),

    # --- meta / scaffolding / reveal ------------------------------------- #
    ("meta", "section-framing imperative (let's break it down)",
     re.compile(r"(?i)\blet(?:'?s| us)\s+(?:break\s+(?:it|this)\s+down|take\s+a\s+"
                r"(?:closer\s+)?look|get\s+started|jump\s+(?:in|right\s+in)|"
                r"walk\s+through|dig\s+(?:in|into))\b"
                r"|\bwithout\s+further\s+ado\b|\bbuckle\s+up\b")),
    ("meta", "back-reference (as we've seen / as mentioned earlier)",
     re.compile(r"(?i)\bas\s+(?:we'?ve|we\s+have)\s+(?:seen|discussed|explored|"
                r"noted|established)\b"
                r"|\bas\s+(?:mentioned|discussed|noted|stated|shown)\s+"
                r"(?:earlier|above|previously|before)\b")),
    ("meta", "reader mind-reading (you might be wondering)",
     re.compile(r"(?i)\byou\s+(?:might|may|probably|likely)\s+(?:be\s+)?"
                r"(?:wondering|asking|thinking|expecting)\b"
                r"|\bif\s+you'?re\s+like\s+(?:most|many)\s+(?:people|of\s+us|"
                r"developers|readers)\b|\bchances\s+are\b")),
    ("scaffold", "roadmap-preview sentence (by the end of this guide)",
     re.compile(r"(?i)\bby\s+the\s+end\s+of\s+this\s+(?:article|post|guide|piece|"
                r"section|tutorial|chapter)\b")),
    ("reveal", "colon reveal (The kicker: X)",
     re.compile(r"(?im)^\s*(?:and\s+)?(?:the\s+)?(?:kicker|catch|twist|upshot|"
                r"best\s+part|plot\s+twist)\s*:\s*\S")),
    ("reveal", "here's-the-kicker declarative reveal",
     re.compile(r"(?i)\bhere(?:'?s| is)\s+(?:the\s+)?(?:kicker|catch|deal|rub|"
                r"best\s+part|twist|secret|hard\s+part|beauty\s+of\s+it)\b")),
    ("reveal", "here's-where-it-gets-interesting escalation",
     re.compile(r"(?i)\b(?:but|and|now)?\s*(?:here(?:'?s| is)|this\s+is)\s+where\s+"
                r"(?:it|things|the\s+\w+)\s+get(?:s)?\s+(?:interesting|tricky|"
                r"complicated|good|weird|fun|hairy|real)\b")),
    ("throat-clearing", "worth-noting preamble",
     re.compile(r"(?i)\bit(?:'?s| is)\s+worth\s+(?:noting|mentioning|remembering|"
                r"pointing\s+out|highlighting|considering)\s+that\b"
                r"|\bit\s+(?:is|should\s+be)\s+(?:important|worth|essential)\s+"
                r"to\s+note\s+that\b")),

    # --- structural framing pivots --------------------------------------- #
    ("antithesis", "this isn't about X, it's about Y",
     re.compile(r"(?i)\b(?:this|it|that)\s+(?:isn'?t|is\s+not|wasn'?t|was\s+not)\s+"
                r"(?:just\s+)?about\b[^.!?\n]{1,60}?[.,;]\s*"
                r"(?:it(?:'?s| is)|this\s+is|they'?re)\s+about\b")),
    ("setup", "more-than-just setup",
     re.compile(r"(?i)\b(?:more\s+than|much\s+more\s+than|far\s+more\s+than)\s+"
                r"(?:just|simply|merely)\b")),
    ("both-sides", "reflexive both-sides balancing",
     re.compile(r"(?i)\bon\s+(?:the\s+)?one\s+hand\b[^.\n]{0,160}?"
                r"\bon\s+the\s+other\s+hand\b"
                r"|\bthere\s+are\s+(?:both\s+)?(?:pros\s+and\s+cons|"
                r"advantages\s+and\s+disadvantages|benefits\s+and\s+drawbacks|"
                r"trade[- ]?offs)\b")),
    ("closer", "restatement opener (Simply put / In a nutshell)",
     re.compile(r"(?im)^\s*(?:simply\s+put|put\s+simply|in\s+a\s+nutshell|"
                r"to\s+put\s+it\s+(?:simply|briefly))\s*,")),
    ("closer", "and-that's-why closing beat",
     re.compile(r"(?im)^\s*(?:and|so)\s+that(?:'?s| is)\s+(?:why|how|what|the\s+"
                r"(?:whole\s+)?(?:point|reason|idea))\b")),
    ("enumeration", "-ly ordinal enumeration (Firstly / Secondly)",
     re.compile(r"(?im)^\s*(?:firstly|secondly|thirdly|fourthly|lastly)\s*,")),
    ("rhetorical-we", "inclusive we've-all-been-there",
     re.compile(r"(?i)\bwe(?:'ve| have)\s+all\s+been\s+there\b|\bwe\s+all\s+know\b"
                r"|\bwe\s+live\s+in\s+a\s+(?:world|time|age|era)\b")),

    # --- marketing / puffery phrase frames (not single dual-use words) ---- #
    ("cta", "marketing hook (look no further / picture this / imagine a world)",
     re.compile(r"(?i)\b(?:look\s+no\s+further|embark\s+on\s+(?:a|your|this)\s+"
                r"(?:journey|adventure)|imagine\s+a\s+world\s+where|buckle\s+up|"
                r"picture\s+this|now\s+imagine)\b")),
    ("continuation-cliche", "continues to (captivate / inspire / redefine)",
     re.compile(r"(?i)\bcontinues?\s+to\s+(?:captivate|inspire|thrive|resonate|"
                r"redefine|push\s+the\s+boundaries|shape\s+the\s+future)\b")),
    ("significance", "inflated-significance / legacy framing",
     re.compile(r"(?i)\bwatershed\s+moment\b"
                r"|\b(?:marks?|marking|represents?|signals?)\s+an?\s+(?:pivotal|"
                r"significant|defining|major|key)\s+(?:moment|shift|milestone|"
                r"turning\s+point)\b"
                r"|\bsetting\s+the\s+stage\s+for\b"
                r"|\b(?:leaves?|left|leaving)\s+(?:an?\s+)?(?:indelible|lasting|"
                r"profound|enduring)\s+(?:mark|legacy|impact|impression)\b"
                r"|\blasting\s+legacy\b")),
]
