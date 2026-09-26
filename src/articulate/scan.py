#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.scan -- the core scanner over a document's lines.
Standard library only.
"""
from .advisories import (document_advisories, find_anaphora_runs,
                         find_contrast_pairs, find_fragment_openers)
from .binary import binary_reason
from .cadence import cadence_stats, texture_score
from .lexicon import (ADVERB, BULLET, DIGIT, EMOJI, EXPLETIVE, HEADING, NOMINAL,
                      PASSIVE, SOFT, VAGUE_QUANT, WORD)
from .markup import (ALLOW_EXEMPT_CATEGORIES, FENCE, _mk, allowed,
                     classify_fountain, is_md_hr, is_md_table_sep, mask_quotes,
                     read_allowlist, strip_markup)
from .rules_high import HIGH
from .rules_low import FICTION_SLOP, LOW, REGISTER_JARGON
from .rules_medium_register import MEDIUM_REGISTER
from .rules_medium_structure import MEDIUM_STRUCTURE

MEDIUM = MEDIUM_REGISTER + MEDIUM_STRUCTURE

# Bump SCAN_ALGO on any change to the scanner's control flow (what a line is,
# which pass runs on it, how many hits a rule may return). The fingerprint folds
# it in, so a receipt issued under the old flow reads Unverifiable, not Match.
SCAN_ALGO = 1
# A Markdown table delimiter row is structure, never an em-dash.
SKIP_TABLE_SEP = True


def scan(path: str):
    """Read a file and scan it. Findings: (line, cat, label, snippet)."""
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError:
        return [], [], [], {}
    if binary_reason(data, name=path):
        return [], [], [], {}
    return scan_lines(data.decode("utf-8", errors="replace").splitlines(keepends=True))


def scan_lines(lines, extra_allow=(), *, genre=None):
    """Core scanner over a list of raw lines. Shared by scan(path) and
    check_text(text), so the engine never needs the filesystem.

    `genre` is an optional dict of genre-layer options (from a genre profile or
    mode): `unit` ("sentence" default, or "line" for verse), `structural_classify`
    ("fountain" for screenplay), `dialogue_exempt`/`quote_exempt_all` for masking
    quoted speech, `fiction_slop` to run the report-only fiction lexicon, and
    `suppress_categories` to drop craft-device categories that are miscategorized
    as flaws in a genre. With genre=None the scanner behaves exactly as before."""
    genre = genre or {}
    unit = genre.get("unit", "sentence")
    fountain = genre.get("structural_classify") == "fountain"
    dialogue_exempt = bool(genre.get("dialogue_exempt"))
    quote_exempt_all = bool(genre.get("quote_exempt_all"))
    fiction_slop = bool(genre.get("fiction_slop"))
    suppress = set(genre.get("suppress_categories", ()))
    mask_q = dialogue_exempt or quote_exempt_all
    roles = classify_fountain(lines) if fountain else None

    high, medium, low = [], [], []
    prose_words = []          # for cadence stats
    soft_count = 0            # dual-use signal density, for the texture score
    adv_count = 0             # -ly adverbs, for adverb-density
    passive_count = 0         # agentless passive, for passive-density
    word_total = 0
    in_fence = False
    in_frontmatter = False
    allow = read_allowlist(lines) | {a.lower() for a in extra_allow}

    # YAML frontmatter: a leading '---' opens it, the next '---' closes it.
    if lines and lines[0].strip() == "---":
        in_frontmatter = True

    # Absolute character offset of the start of each line, for span records.
    offsets, acc = [], 0
    for raw in lines:
        offsets.append(acc)
        acc += len(raw)

    for i, raw in enumerate(lines, 1):
        off = offsets[i - 1]
        stripped = raw.strip()

        # Skip fenced code blocks entirely (prose tells do not apply to code).
        if FENCE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        # Skip YAML frontmatter body.
        if in_frontmatter:
            if i > 1 and stripped == "---":
                in_frontmatter = False
            continue

        # Screenplay: a line's role decides which passes run. Structural lines
        # (slug, cue, parenthetical, transition, blank) are not prose; dialogue
        # keeps the character's voice; only action faces device scrutiny.
        role = roles[i - 1] if fountain else "prose"
        run_devices = role in ("prose", "action")
        run_slop = fiction_slop and (role in ("prose", "dialogue"))
        if fountain and role not in ("action", "dialogue"):
            continue

        snippet = stripped[:100]
        slop_text = strip_markup(raw)   # fiction-slop reads the actual words

        if run_slop:
            for cat, label, rx in FICTION_SLOP:
                m = rx.search(slop_text)
                if m and not allowed(m.group(0), allow):
                    low.append(_mk(i, off, cat, label, m.start(), m.end(), raw, snippet))
        if not run_devices:
            continue

        # Formatting advisories look at the RAW line (markup matters). Under a
        # quote-exempt genre, quoted speech is masked out of the raw line too.
        raw_low = mask_quotes(raw) if quote_exempt_all else raw
        me = EMOJI.search(raw_low)
        if me:
            low.append(_mk(i, off, "emoji", "emoji in text", me.start(), me.end(), raw, snippet))
            # Emoji used as STRUCTURE (in a heading, as/beside a bullet, or at the
            # very start of a line as a status marker) is a strong tell, not just
            # decoration. Markdown-oriented; a MEDIUM rather than an advisory.
            if HEADING.match(raw_low) or BULLET.match(raw_low) or not raw_low[:me.start()].strip():
                medium.append(_mk(i, off, "emoji-structure",
                                  "emoji as heading / bullet / status marker",
                                  me.start(), me.end(), raw, snippet))
        for cat, label, rx in LOW:
            m = rx.search(raw_low)
            if m and not allowed(m.group(0), allow):
                low.append(_mk(i, off, cat, label, m.start(), m.end(), raw, snippet))

        if is_md_hr(raw) or (SKIP_TABLE_SEP and is_md_table_sep(raw)):
            continue

        text = mask_quotes(slop_text) if mask_q else slop_text

        # inline "---" (three hyphens mid-line) reads as an em-dash.
        pos = text.find("---")
        if pos != -1:
            high.append(_mk(i, off, "em-dash", "em-dash (---)", pos, pos + 3, raw, snippet))

        for cat, label, rx in HIGH:
            m = rx.search(text)
            if m and (cat in ALLOW_EXEMPT_CATEGORIES or not allowed(m.group(0), allow)):
                high.append(_mk(i, off, cat, label, m.start(), m.end(), raw, snippet))
        for cat, label, rx in MEDIUM:
            m = rx.search(text)
            if m and (cat in ALLOW_EXEMPT_CATEGORIES or not allowed(m.group(0), allow)):
                medium.append(_mk(i, off, cat, label, m.start(), m.end(), raw, snippet))
        for cat, label, rx in REGISTER_JARGON:   # a hit to fix; allowlist to keep
            m = rx.search(text)
            if m and not allowed(m.group(0), allow):
                medium.append(_mk(i, off, cat, label, m.start(), m.end(), raw, snippet))
        # vague quantifier, advisory, only when no number is given on the line
        mq = VAGUE_QUANT.search(text)
        if mq and not DIGIT.search(text) and not allowed(mq.group(0), allow):
            low.append(_mk(i, off, "vague-quantifier", "vague quantifier, no number given",
                           mq.start(), mq.end(), raw, snippet))
        # Williams: expletive opener (advisory), on the line start
        lead = len(text) - len(text.lstrip())
        mex = EXPLETIVE.match(text.lstrip())
        if mex:
            low.append(_mk(i, off, "expletive-opener",
                           "empty opener (there is / it is important)",
                           lead + mex.start(), lead + mex.end(), raw, snippet))
        # Williams: stacked nominalizations (advisory), only when 4+ pile up
        noms = list(NOMINAL.finditer(text))
        if len(noms) >= 4:
            m0 = noms[0]
            low.append(_mk(i, off, "nominalization",
                           f"{len(noms)} nominalizations in one line",
                           m0.start(), m0.end(), raw, snippet))

        # texture-score inputs: soft-signal density over real prose words. A kept
        # term of art does not count toward texture either, so a register's normal
        # vocabulary cannot push a clean document to "elevated".
        word_total += len(WORD.findall(text))
        soft_count += sum(1 for w in SOFT.findall(text) if not allowed(w, allow))
        adv_count += len(ADVERB.findall(text))
        passive_count += len(PASSIVE.findall(text))

        # collect prose words for cadence (skip headings, list bullets, tables)
        if stripped and not stripped.startswith(("#", "|", ">", "-", "*", "+")):
            prose_words.append(text)

    # Contrast-pair detection stays on (report-only under slop=off), but where a
    # genre exempts quoted speech, the pass runs over quote-masked lines so a
    # dialogue or cited-testimony pair drops out. Verse suppresses it outright.
    if "contrast-pair" not in suppress:
        cp_lines = [mask_quotes(ln) for ln in lines] if mask_q else lines
        medium.extend(find_contrast_pairs(cp_lines))

    # Local anaphora and the document-level structure / repetition signals are
    # report-only advisories (LOW): they fire on ordinary human prose too, so they
    # never gate or change the clean verdict. Verse suppresses anaphora, which
    # poets use by craft. Each carries a minimum-size guard, so a short snippet
    # cannot trip it.
    if "anaphora" not in suppress:
        low.extend(find_anaphora_runs(lines))
    if "fragment-opener" not in suppress:
        low.extend(find_fragment_openers(lines))
    low.extend(document_advisories(lines, word_total))

    doc = cadence_stats(" ".join(prose_words))
    doc["words"] = word_total
    doc["soft"] = soft_count
    doc["adverb_rate"] = round(adv_count / word_total * 100, 1) if word_total else 0
    doc["passive_rate"] = round(passive_count / word_total * 100, 1) if word_total else 0
    # Verse is measured by the line, not the sentence, so a punctuation-free
    # stanza is not read as one long uniform "sentence". Drop the cadence signal.
    if unit == "line":
        doc["uniform"] = False
        doc["repetitive_openers"] = False
    doc["score"], doc["elevated"] = texture_score(
        len(high) + len(medium), soft_count, doc, word_total)

    if suppress:
        high = [f for f in high if f["category"] not in suppress]
        medium = [f for f in medium if f["category"] not in suppress]
        low = [f for f in low if f["category"] not in suppress]
    return high, medium, low, doc
