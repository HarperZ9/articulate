#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.advisories -- document-level and multi-line signals: contrast
pairs, anaphora runs, fragment openers and the structure and repetition
advisories. Standard library only.
"""
import re
from statistics import mean, pstdev

from .lexicon import (BOLD_SPAN, BULLET, FIRSTWORD, HEADING, HEDGE_WORDS, NEG,
                      NGRAM_STOP, OPENER_STOP, WORD)
from .logical import sentence_spans
from .markup import FENCE, _line_offsets, _mk, is_md_hr, strip_markup

PRONOUN_SUBJ = {"you", "we", "i", "they", "he", "she", "it"}
# 4+ letter function words that do not count as a shared predicate.
STOP4 = {"that", "this", "what", "with", "from", "have", "were", "been", "will",
         "would", "could", "should", "there", "their", "them", "then", "than",
         "when", "which", "your", "some", "more", "most", "into", "over", "only",
         "also", "such", "each", "does", "here", "must", "very", "much", "many",
         "both", "even", "just", "like", "well", "back", "down", "upon", "onto",
         "whom", "cannot", "about", "because", "while"}


def find_contrast_pairs(lines):
    """Adjacent short sentences that repeat a pronoun subject and a predicate
    word, where one affirms and the other negates ("You can watch ... You cannot
    watch ..."). The pronoun-subject and shared-word requirements keep it off
    parallel list items and off deliberate does-not-prove lines."""
    offsets, acc = [], 0
    for raw in lines:
        offsets.append(acc)
        acc += len(raw)
    sents = sentence_spans(lines)
    findings = []
    for (l1, s1), (l2, s2) in zip(sents, sents[1:]):
        m1, m2 = FIRSTWORD.match(s1), FIRSTWORD.match(s2)
        if not (m1 and m2):
            continue
        fw = m1.group(1).lower()
        if fw != m2.group(1).lower() or fw not in PRONOUN_SUBJ:
            continue
        if bool(NEG.search(s1)) == bool(NEG.search(s2)):
            continue                      # need one affirmative, one negated
        w1, w2 = len(WORD.findall(s1)), len(WORD.findall(s2))
        if max(w1, w2) > 16 or abs(w1 - w2) > 6:
            continue                      # short and similar in length
        shared = ({w.lower() for w in WORD.findall(s1) if len(w) >= 4 and w.lower() not in STOP4}
                  & {w.lower() for w in WORD.findall(s2) if len(w) >= 4 and w.lower() not in STOP4})
        if not shared:
            continue                      # a repeated predicate, not just a subject
        raw = lines[l2 - 1] if l2 - 1 < len(lines) else ""
        first = (s2.split() or [""])[0]
        pos = raw.find(first) if first else -1
        if pos < 0:
            pos = len(raw) - len(raw.lstrip())
        end = min(len(raw.rstrip("\n")), pos + len(s2))
        findings.append(_mk(l2, offsets[l2 - 1], "contrast-pair",
                            "contrast pair (parallel negation)", pos, end, raw, s2[:100]))
    return findings




def find_anaphora_runs(lines):
    """A local run of >=3 consecutive prose sentences opening with the same
    CONTENT word (case-insensitive), a report-only advisory (LOW). Function-word
    openers (The/This/It/You) are excluded and left to the document-wide opener
    ratio; list items and headings are skipped, and only real sentences (>=4
    words) count, so a bulleted list or a run of short labels does not trip it.
    Reported once, at the run's first sentence."""
    offsets = _line_offsets(lines)
    # Only real prose sentences: drop those whose source line is a heading or a
    # list item, and require at least four words so labels and fragments are out.
    sents = [(ln, s) for (ln, s) in sentence_spans(lines)
             if not (0 < ln <= len(lines)
                     and (HEADING.match(lines[ln - 1]) or BULLET.match(lines[ln - 1])))
             and len(WORD.findall(s)) >= 4]
    findings, i, n = [], 0, len(sents)
    while i < n:
        m0 = FIRSTWORD.match(sents[i][1])
        if not m0:
            i += 1
            continue
        w0 = m0.group(1).lower()
        j = i + 1
        while j < n:
            mj = FIRSTWORD.match(sents[j][1])
            if not mj or mj.group(1).lower() != w0:
                break
            j += 1
        run = j - i
        if run >= 3 and len(w0) >= 3 and w0 not in OPENER_STOP:
            l2 = sents[i][0]
            raw = lines[l2 - 1] if l2 - 1 < len(lines) else ""
            lead = len(raw) - len(raw.lstrip())
            findings.append(_mk(l2, offsets[l2 - 1], "anaphora",
                                f"{run} consecutive sentences open with '{w0}'",
                                lead, min(len(raw.rstrip("\n")), lead + len(w0)),
                                raw, sents[i][1][:100]))
        i = j
    return findings


# A curated evaluative-adjective + abstract-noun fragment ("Strong foundation.",
# "Solid architecture."), the two-or-three-word declarative beat a model drops at
# the start of a paragraph. Both the adjective and the noun come from curated
# sets, so an ordinary short line ("Good morning.", "Nice work.") does not fire:
# "morning" and "work" are not summary nouns. The noun must be followed by
# sentence punctuation, so a full sentence ("Strong foundations hold the system
# together.") is not a fragment and does not match.
FRAGMENT_OPENER = re.compile(
    r"(?i)^\s*"
    r"(?:(?:very|really|remarkably|genuinely|impressively|surprisingly)\s+)?"
    r"(?:strong|solid|clean|elegant|powerful|robust|simple|clear|sound|smart|"
    r"impressive|remarkable|compelling|decent|great|excellent|fine|good|tight|"
    r"slick|neat|thoughtful|careful|rigorous|brilliant|nice|classic|textbook)\s+"
    r"(?:foundations?|architecture|design|reasoning|logic|structure|framing|"
    r"insight|distinction|approach|execution|progress|groundwork|footing|"
    r"fundamentals?|engineering|craftsmanship|integration|abstraction|premise|"
    r"thesis|argument|analysis|coverage|separation|encapsulation|typing)"
    r"[.!?](?=\s|$)")


def find_fragment_openers(lines):
    """A curated evaluative-adjective + abstract-noun fragment used as a punchy
    beat at the START of a paragraph ("Strong foundation.", "Solid architecture.").
    Report-only (LOW): the fragment shape is legitimate human prose too, so it
    never gates. Paragraph-initial only, because a fragment mid-paragraph is a
    stylistic choice; the machine tell is opening a paragraph with it. Fenced code
    and frontmatter are skipped, and a heading, list item, table row, block quote,
    or horizontal rule is not a prose paragraph, so it is passed over."""
    offsets = _line_offsets(lines)
    findings = []
    in_fence = False
    in_fm = bool(lines) and lines[0].strip() == "---"
    prev_blank = True
    for i, raw in enumerate(lines, 1):
        if FENCE.match(raw):
            in_fence = not in_fence
            prev_blank = False
            continue
        if in_fence:
            prev_blank = False
            continue
        if in_fm:
            if i > 1 and raw.strip() == "---":
                in_fm = False
            prev_blank = False
            continue
        stripped = raw.strip()
        if not stripped:
            prev_blank = True
            continue
        is_structure = bool(HEADING.match(raw) or BULLET.match(raw)
                            or is_md_hr(raw) or stripped[0] in "|>")
        if prev_blank and not is_structure:
            text = strip_markup(raw)
            m = FRAGMENT_OPENER.match(text)
            if m:
                lead = len(text) - len(text.lstrip())
                findings.append(_mk(i, offsets[i - 1], "fragment-opener",
                                    "evaluative fragment opener (Strong foundation.)",
                                    lead, m.end(), raw, stripped[:100]))
        prev_blank = False
    return findings


def find_repeated_ngrams(text, n=3, min_repeat=3):
    """A content n-gram repeated >= min_repeat times (a mode-collapse repetition
    signal). Grams that are entirely stopwords, or carry fewer than two content
    tokens, are skipped so ordinary function-word runs and a repeated two-word term
    do not fire. Returns (gram_text, count) or None. Report-only (LOW)."""
    words = [w.lower() for w in re.findall(r"[a-zA-Z']+", text)]
    if len(words) < n * min_repeat:
        return None
    from collections import Counter
    grams = Counter()
    for k in range(len(words) - n + 1):
        g = tuple(words[k:k + n])
        if sum(1 for w in g if w not in NGRAM_STOP) < 2:
            continue
        grams[g] += 1
    if not grams:
        return None
    gram, cnt = grams.most_common(1)[0]
    return (" ".join(gram), cnt) if cnt >= min_repeat else None


def paragraph_word_counts(lines):
    """Word counts of blank-line-separated paragraphs, skipping fenced code and
    frontmatter. Used for the uniform-paragraph-length advisory."""
    counts, cur, in_fence = [], 0, False
    in_fm = bool(lines) and lines[0].strip() == "---"
    for idx, raw in enumerate(lines):
        if FENCE.match(raw):
            in_fence = not in_fence
            continue
        if in_fm:
            if idx > 0 and raw.strip() == "---":
                in_fm = False
            continue
        if in_fence:
            continue
        if raw.strip() == "":
            if cur:
                counts.append(cur)
                cur = 0
        elif not raw.lstrip().startswith(("#", "|", ">")):
            cur += len(WORD.findall(strip_markup(raw)))
    if cur:
        counts.append(cur)
    return [c for c in counts if c > 0]


def document_advisories(lines, word_total):
    """Document-level LOW advisories over structure and repetition: header,
    list, and bold density on short/expository text; a repeated content n-gram;
    a hedge cluster in one sentence; and near-uniform paragraph lengths. Each has
    a minimum-size guard so a short human snippet cannot trip it. Report-only:
    none of these gate, and none change the clean/flagged verdict."""
    offsets = _line_offsets(lines)
    out = []

    def add(line_no, cat, label):
        raw = lines[line_no - 1] if 0 < line_no <= len(lines) else "\n"
        out.append(_mk(line_no, offsets[line_no - 1] if line_no <= len(offsets) else 0,
                       cat, label, 0, 0, raw, raw.strip()[:100]))

    # Markdown structure density. Fenced code is masked out of the counts.
    nonblank = headers = list_lines = bold_spans = 0
    in_fence = False
    for raw in lines:
        if FENCE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence or not raw.strip():
            continue
        nonblank += 1
        if HEADING.match(raw):
            headers += 1
        if BULLET.match(raw):
            list_lines += 1
        bold_spans += len(BOLD_SPAN.findall(raw))

    if headers >= 3 and word_total and word_total < 300:
        add(1, "header-reflex", f"{headers} headers in {word_total} words (structure on short text)")
    if nonblank >= 6 and list_lines / nonblank > 0.6:
        add(1, "list-reflex", f"{list_lines}/{nonblank} lines are list items (lists replacing prose)")
    if word_total >= 60 and bold_spans / word_total * 100 > 2.5:
        add(1, "bold-density", f"{bold_spans} bold spans / {word_total} words (boldface overuse)")

    rep = find_repeated_ngrams("\n".join(lines))
    if rep:
        add(1, "ngram-repetition", f"'{rep[0]}' repeats {rep[1]}x (n-gram repetition)")

    para = paragraph_word_counts(lines)
    if len(para) >= 4:
        mu = mean(para)
        if mu and pstdev(para) / mu < 0.25:
            add(1, "paragraph-uniformity",
                f"{len(para)} paragraphs, near-uniform length (cv<0.25)")

    for line_no, s in sentence_spans(lines):
        if len(HEDGE_WORDS.findall(s)) >= 3:
            raw = lines[line_no - 1] if line_no <= len(lines) else "\n"
            out.append(_mk(line_no, offsets[line_no - 1], "hedge-cluster",
                           "3+ hedges in one sentence", 0,
                           min(len(raw.rstrip("\n")), 1), raw, s[:100]))
    return out
