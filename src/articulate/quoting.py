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
from .masking import mask_code as mask_code_spans

# ``...'' with apostrophes inside ("``it's here''"), up to the first '' (SCAN_ALGO 7).
TEX_QUOTE = re.compile(r"``(?:(?!'')[^`\n])*''")
TEX_ENV = re.compile(r"\\(begin|end)\{(quote|quotation|displayquote|verbatim)\}")
# csquotes: \enquote{..}, \textquote[..][..]{..}, \foreignquote{lang}{..} and
# their block forms. The value is how many brace groups the command takes.
CSQUOTES = re.compile(r"\\(enquote|textquote|blockquote|foreignquote|hyphenquote|"
                      r"foreignblockquote|hyphenblockquote)\*?")
CSQUOTES_ARGS = {"enquote": 1, "textquote": 1, "blockquote": 1, "foreignquote": 2,
                 "hyphenquote": 2, "foreignblockquote": 2, "hyphenblockquote": 2}
TEXTTT = re.compile(r"\\texttt\{[^{}\n]*\}")
VERB_OPEN = re.compile(r"\\verb\*?([^\sA-Za-z*])")
SPEAKER = re.compile(r"^\s*(?:>\s*)?(?:\*\*)?(?:ChatGPT|Assistant|Model|User|AI|Claude|"
                     r"Gemini|Copilot)(?:\*\*)?\s*:")


def mask_direct(text, raw=None):
    """Blank direct quotations: the marks articulate.quotemarks pairs, LaTeX
    ``...'' and the csquotes commands. The LaTeX forms are found in `raw`, the
    same text before markup was blanked (the code-span mask reads a backtick
    pair as code, and the TeX mask blanks a command name)."""
    src = text if raw is None else raw
    spans = set(quote_spans(text)) | {m.span() for m in TEX_QUOTE.finditer(src)}
    spans |= set(_csquote_spans(src))
    return blank_spans(text, _merge(spans))


_BRACE = re.compile(r"[{}\n]")
_SKIP = re.compile(r"[ \t]*")
_OPTIONAL = re.compile(r"\[[^\]\n]*\]")


def _brace_pairs(text):
    """{index of an opening brace: index of its closing brace}, within a line,
    in one pass. An unclosed brace has no entry."""
    pairs, stack = {}, []
    for m in _BRACE.finditer(text):
        c = m.group()
        if c == "{":
            stack.append(m.start())
        elif c == "}" and stack:
            pairs[stack.pop()] = m.start()
        elif c == "\n":
            stack.clear()
    return pairs


def _groups_end(text, pos, want, pairs):
    """The index after `want` brace groups starting at `pos`, with at most two
    optional [..] arguments first; None when a group does not close on its line."""
    i = _SKIP.match(text, pos).end()
    for _ in range(2):
        opt = _OPTIONAL.match(text, i)
        if not opt:
            break
        i = _SKIP.match(text, opt.end()).end()
    for k in range(want):
        if k:
            i = _SKIP.match(text, i).end()
        close = pairs.get(i) if text.startswith("{", i) else None
        if close is None:
            return None
        i = close + 1
    return i


def _csquote_spans(text):
    """(start, end) of each csquotes command with all its arguments. A command
    whose arguments do not close on its line blanks nothing. Linear time."""
    found = list(CSQUOTES.finditer(text))
    if not found:
        return []
    pairs, spans, pos = _brace_pairs(text), [], 0
    for m in found:
        if m.start() < pos:
            continue
        end = _groups_end(text, m.end(), CSQUOTES_ARGS[m.group(1)], pairs)
        if end is not None:
            spans.append((m.start(), end))
            pos = end
    return spans


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


_TEX_COMMENT = re.compile(r"(?<!\\)%")
_HTML_OPEN, _HTML_CLOSE = "<!--", "-->"


def _live(raw, in_comment):
    """(the part of a line where LaTeX environments are read, in_comment after
    the line): HTML comments, inline code and a TeX comment are blanked."""
    out, pos = [], 0
    while pos < len(raw):
        if in_comment:
            end = raw.find(_HTML_CLOSE, pos)
            if end < 0:
                return "".join(out), True
            pos, in_comment = end + len(_HTML_CLOSE), False
            continue
        start = raw.find(_HTML_OPEN, pos)
        if start < 0:
            out.append(raw[pos:])
            break
        out.append(raw[pos:start])
        pos, in_comment = start + len(_HTML_OPEN), True
    text = mask_code_spans("".join(out))
    cut = _TEX_COMMENT.search(text)
    return (text[:cut.start()] if cut else text), in_comment


def _env_lines(lines, kinds=None):
    """(quoted, verbatim): 1-based numbers of the lines inside, and on the
    delimiters of, a LaTeX quote, quotation or displayquote environment and a
    verbatim one (SCAN_ALGO 7). An environment counts only where LaTeX would
    read it: on a prose or quote line, outside an HTML comment, inline code
    and a TeX comment. Environments nest. One that never closes blanks nothing,
    as an unpaired quotation mark does. Inside verbatim nothing else is read."""
    events, in_comment = [], False
    for i, raw in enumerate(lines, 1):
        if kinds is not None and kinds[i - 1] not in ("prose", "quote"):
            continue
        live, in_comment = _live(raw, in_comment)
        events.extend((i, m.group(1), m.group(2)) for m in TEX_ENV.finditer(live))
    quoted, verbatim, stack = set(), set(), []
    for line_no, kind, env in events:
        if stack and stack[-1][1] == "verbatim":
            if kind == "end" and env == "verbatim":
                verbatim.update(range(stack.pop()[0], line_no + 1))
            continue
        if kind == "begin":
            stack.append((line_no, env))
        elif stack and stack[-1][1] == env:
            quoted.update(range(stack.pop()[0], line_no + 1))
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
    tex_quoted, verbatim = _env_lines(lines, kinds)
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
