#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.quoting -- which text is quoted, so the rules leave it alone.

A quotation is evidence the writer cites. Its phrasing belongs to its source,
and changing it would misquote the source, so the phrasing rules read the text
with every quotation blanked:

- direct quotations in straight or curly double quotes, and LaTeX ``...'';
- Markdown block quote lines (`>`);
- the lines of a LaTeX `quote` or `quotation` environment.

The rule on a first-person line in which the speaker calls itself software also
skips text that a document shows as data: table rows, a LaTeX
`verbatim` environment, `\\texttt{}` and `\\verb` spans, and speaker-labelled
transcript turns (a speaker name and a colon at a line start, such as "User:",
with the lines that continue the turn).

Rules about the rendered document (an interface markup token, a hidden
character) read every character, quotes included. Every mask here replaces text
with the same number of spaces, so offsets stay valid. Straight single quotes
are left alone, because an apostrophe would open a false span.

Standard library only.
"""
import re

from .masking import blank_spans, quote_spans

TEX_QUOTE = re.compile(r"``[^`'\n]*''")
TEX_ENV = re.compile(r"\\begin\{(quote|quotation|verbatim)\}")
TEXTTT = re.compile(r"\\texttt\{[^{}\n]*\}")
VERB_OPEN = re.compile(r"\\verb\*?([^\sA-Za-z*])")
SPEAKER = re.compile(r"^\s*(?:>\s*)?(?:\*\*)?(?:ChatGPT|Assistant|Model|User|AI|Claude|"
                     r"Gemini|Copilot)(?:\*\*)?\s*:")


def mask_direct(text, raw=None):
    """Blank direct quotations: double quotes, curly pairs and LaTeX ``...''.
    The LaTeX pairs are found in `raw`, the same text before markup was blanked
    (the code-span mask reads a backtick pair as code)."""
    tex = TEX_QUOTE.finditer(text if raw is None else raw)
    spans = set(quote_spans(text)) | {m.span() for m in tex}
    return blank_spans(text, _merge(spans))


def mask_code(text):
    """Blank `\\texttt{}` and `\\verb` spans, in linear time: each `\\verb`
    looks for its closing delimiter once, and an unclosed one blanks nothing."""
    spans = [m.span() for m in TEXTTT.finditer(text)]
    pos, dead = 0, {}   # delimiter -> the newline before which it cannot close
    for m in VERB_OPEN.finditer(text):
        if m.start() < pos or dead.get(m.group(1), -1) > m.start():
            continue
        stop = text.find("\n", m.end())
        stop = len(text) if stop < 0 else stop
        close = text.find(m.group(1), m.end(), stop)
        if close < 0:
            dead[m.group(1)] = stop
            continue
        spans.append((m.start(), close + 1))
        pos = close + 1
    return blank_spans(text, _merge(spans))


def _merge(spans):
    merged = []
    for s, e in sorted(spans):
        if merged and s < merged[-1][1]:
            merged[-1] = (merged[-1][0], max(e, merged[-1][1]))
        else:
            merged.append((s, e))
    return merged


def _env_lines(lines):
    """(quoted, verbatim): 1-based numbers of the lines inside, and on the
    delimiters of, a LaTeX quote or quotation environment and a verbatim one."""
    quoted, verbatim, open_env = set(), set(), None
    for i, raw in enumerate(lines, 1):
        if open_env is None:
            m = TEX_ENV.search(raw)
            open_env = m.group(1) if m else None
        if open_env is not None:
            (verbatim if open_env == "verbatim" else quoted).add(i)
            if "\\end{" + open_env + "}" in raw:
                open_env = None
    return quoted, verbatim


def _transcript_lines(lines):
    """A speaker-labelled turn: the labelled line and its continuation lines
    up to the next blank line or the next label."""
    out, in_turn = set(), False
    for i, raw in enumerate(lines, 1):
        if not raw.strip():
            in_turn = False
        elif SPEAKER.match(raw):
            in_turn = True
        if in_turn:
            out.add(i)
    return out


def quoted_lines(lines, kinds):
    """(block, shown): the lines every phrasing rule skips, and the further
    lines the self-description rule skips. `kinds` comes from logical.line_kinds."""
    tex_quoted, verbatim = _env_lines(lines)
    block = {i for i, k in enumerate(kinds, 1) if k == "quote"} | tex_quoted
    tables = {i for i, k in enumerate(kinds, 1) if k == "table"}
    return block, verbatim | tables | _transcript_lines(lines)


def mask_lines(unit, text, line_numbers):
    """Blank the parts of a logical line's text that came from the given lines."""
    if not line_numbers:
        return text
    spans = []
    for log_start, _doc, line_no, length in unit.pieces:
        if line_no in line_numbers:
            spans.append((log_start, log_start + length))
    return blank_spans(text, spans)
