#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
articulate.editor -- the editor layer for Articulate.

The checker names prose patterns with their spans. This layer adds what a
pattern check cannot do on its own, the two things a skilled editor does:

  --judge FILE   Read the prose for JUDGMENT-level quality: confident emptiness,
                 vague abstraction, hedging with no committed position, a
                 metaphor standing in for a literal term, a buried point,
                 verbosity out of proportion to the task, weak verbs. Reports,
                 does not edit.
  --fix FILE     Rewrite the prose so its intended reader can follow it on one
                 read, preserving every fact, number, claim, citation, term of
                 art and structural element, then re-check the rewrite under the
                 same profile. Writes the rewrite (to --out, or <name>.fixed.<ext>).
  --polish FILE  The quality loop, with a no-regression acceptance rule (accept).
  --review FILE  Checks plus a judge read in one report. No rewrite.

The target is the reader and the job the mode names. The house writing standard
reaches the model only under a house profile. No instruction names an outside
score, a sentence-length target or a vocabulary level (prompts.py holds every
template).

The model runs through the `claude` CLI (headless `claude -p`), which sends the
text to a hosted Anthropic model. There is no local-model backend. The CLI is
found through ARTICULATE_CLAUDE_CLI when that is set, and on the PATH otherwise
(see claude_cli.py).
"""
import argparse
import json
import os
import re
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

from . import claude_cli
from .claude_cli import ClaudeUnavailable  # noqa: F401  (re-exported for callers)
from .mathmask import (MATH_EXTS, MathSpliceError, _MATH_PLACEHOLDER,  # noqa: F401
                       _MATH_PLACEHOLDER_RX, _MATH_RX, is_math_file, mask_math,
                       scrub_math_notes, splice_math)
from .prompts import (CONTENT_BOUNDARY, STANDARD, findings_block, hardened,  # noqa: F401
                      judge_instructions, neutralize, rewrite_instructions)
from .rule_reasons import reason_for

HERE = os.path.dirname(os.path.abspath(__file__))
QUALITIES = ("concreteness", "commitment", "economy", "rhythm", "restatable")
_UNAVAILABLE = (RuntimeError, subprocess.TimeoutExpired)


def injection_warning(text):
    """A one-block warning listing document lines that read as a model-addressed
    directive, or "" if none. The editor prints this before a rewrite; it does not
    block, because a document may quote such patterns in good faith."""
    from . import detector
    hits = detector.detect_injection(text)
    if not hits:
        return ""
    lines = [f"  L{h['line']} [{h['category']}] {h['label']}: {h['snippet']}" for h in hits]
    return ("[editor] WARNING: the document contains lines that read as instructions "
            "to a model reading it. They are treated as content to edit, never obeyed:\n"
            + "\n".join(lines))


def assess(text, profile=None):
    """The full check result under a profile or mode."""
    from . import detector
    return detector.check_text(text, profile=profile)


def _why(f):
    reason = reason_for(f["category"])
    if reason:
        return f" (reader cost: {reason[0]})"
    return " (house style)" if f.get("house") else ""


def mechanical_text(text, profile=None):
    """(clean, summary) for text: the HIGH and MEDIUM findings under the profile,
    each with its span and its reader-cost reason. Outside a house profile no
    house-style pattern is listed, so none becomes an editing target."""
    r = assess(text, profile)
    hits = r["high"] + r["medium"]
    lines = [f"  L{h['line']} [{h['tier']} {h['category']}] {h['label']}: "
             f"{h['snippet']}{_why(h)}" for h in hits]
    summary = (f"{len(hits)} finding(s)\n" + "\n".join(lines)) if hits \
        else "no HIGH or MEDIUM findings"
    return len(hits) == 0, summary


def mechanical(path, profile=None):
    """(clean, summary) for a file."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return True, "no HIGH or MEDIUM findings"
    return mechanical_text(text, profile)


def masked_rewrite(text, rewrite_fn, profile=None):
    """Run rewrite_fn(masked_text, findings_summary) with every math span hidden,
    then splice the spans back byte for byte. The summary is built from the masked
    text as well, because it quotes document lines and would otherwise carry the
    math into the prompt. Raises MathSpliceError when the rewrite lost or doubled
    a placeholder."""
    masked, spans = mask_math(text)
    _, mech = mechanical_text(masked, profile)
    return splice_math(rewrite_fn(masked, mech), spans)


def claude_call(instructions, text, timeout=600):
    # The trust boundary is appended to every call so the document on stdin can
    # never be read as instructions, whatever it contains.
    r = claude_cli.run(hardened(instructions), text, timeout=timeout)
    out = (r.stdout or "").strip()
    err = (r.stderr or "").strip()
    blob = (out + " " + err).lower()
    for sentinel, msg in (
        ("credit balance is too low", "credit balance too low; add credits or set ANTHROPIC_API_KEY"),
        ("rate limit", "rate limited; wait for the weekly reset"),
        ("not authenticated", "claude CLI not authenticated; run `claude login`"),
        ("invalid api key", "claude CLI auth invalid"),
    ):
        if sentinel in blob:
            raise ClaudeUnavailable(f"claude CLI: {msg}")
    if r.returncode != 0 and not out:
        raise RuntimeError(f"claude CLI failed: {err[:300] or 'unknown error'}")
    if not out:
        raise RuntimeError("claude CLI returned empty output")
    return out


def strip_preamble(out):
    """Drop a leading 'Here is the rewrite:' style line if the model adds one."""
    out = re.sub(r"^\s*```[a-z]*\n", "", out)
    out = re.sub(r"\n```\s*$", "", out)
    lines = out.splitlines()
    if lines and re.match(r"(?i)^(here('?s| is)|sure|below|the rewrite|rewritten)\b.*:$",
                          lines[0].strip()):
        lines = lines[1:]
        while lines and not lines[0].strip():
            lines = lines[1:]
    return "\n".join(lines)


def _resolve(mode=None, profile=None):
    """(profile_dict_or_None, editor_cfg) for a mode id or a profile name."""
    if mode:
        from . import modes
        prof = modes.load(mode)
        return prof, prof.get("editor", {})
    if profile:
        from . import profiles
        return profiles.load(profile), {}
    return None, {}


def judge(path, mode=None, profile=None):
    text = open(path, encoding="utf-8", errors="replace").read()
    prof, ecfg = _resolve(mode, profile)
    _, mech = mechanical(path, prof)
    instr = judge_instructions(mech, ecfg.get("standard_delta", ""))
    print(f"[judge] {os.path.basename(path)} (via claude CLI)\n")
    warn = injection_warning(text)
    if warn:
        print(warn + "\n")
    try:
        print(claude_call(instr, text))
    except _UNAVAILABLE as e:
        print(f"[judge] model layer unavailable: {e}")


def rewrite_once(text, mech, quality_notes, is_html, standard_delta="", profile=None):
    instr = rewrite_instructions(mech, profile, standard_delta, quality_notes or (), is_html)
    return strip_preamble(claude_call(instr, text))


def quality_judge(text):
    """Score the five qualities the loop reads. Returns a dict or {}."""
    from .prompts import QUALITY_INSTRUCTIONS
    out = claude_call(QUALITY_INSTRUCTIONS, text)
    m = re.search(r"\{.*\}", out, re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except ValueError:
        return {}


def accept(before_scores, after_scores, before_gate, after_gate, required_open, guard):
    """(accepted, reason) for one rewrite pass. The rule, in full: no quality
    score may fall, the gate under the chosen profile may not go from ok to
    blocked, the rewrite may not open a required advisory that was closed, and a
    meaning-guard result, when one exists, must be ok. Nothing else counts; no
    pattern density, cadence statistic or outside score enters the decision."""
    if any(after_scores.get(k, 0) < before_scores.get(k, 0) for k in QUALITIES):
        return False, "a quality score fell"
    if before_gate == "ok" and after_gate == "blocked":
        return False, "the gate went from ok to blocked"
    if required_open:
        return False, "opened a required advisory: " + ", ".join(sorted(required_open))
    if guard is not None and not guard.get("ok", False):
        return False, "the meaning guard did not pass"
    return True, "accepted"


from .polish import polish  # noqa: E402  (polish reads the names above)
from .fix import fix, review  # noqa: E402,F401


def main():
    ap = argparse.ArgumentParser(description="Articulate editor layer (judge / fix).")
    g = ap.add_mutually_exclusive_group(required=True)
    for flag in ("--judge", "--fix", "--polish", "--review"):
        g.add_argument(flag, metavar="FILE")
    ap.add_argument("--out", metavar="FILE", default=None)
    ap.add_argument("--passes", type=int, default=3)
    ap.add_argument("--bar", type=int, default=4, help="quality bar 1-5 for --polish")
    ap.add_argument("--mode", default=None,
                    help="a writing mode (domain/articulation, e.g. memo/argue)")
    ap.add_argument("--profile", default=None,
                    help="a profile; `house` sends the house writing standard")
    args = ap.parse_args()
    target = args.judge or args.fix or args.polish or args.review
    reason = _unreadable(target)
    if reason:
        print(f"[articulate] {reason}")
        return 2
    if args.judge:
        judge(args.judge, args.mode, args.profile)
        return 0
    if args.review:
        review(args.review, args.mode, args.profile)
        return 0
    if args.polish:
        return polish(args.polish, args.out, max(1, args.passes),
                      max(1, min(5, args.bar)), mode=args.mode, profile=args.profile)
    return fix(args.fix, args.out, max(1, args.passes), mode=args.mode, profile=args.profile)


def _unreadable(target):
    if not os.path.isfile(target):
        return f"no such file: {target}"
    from . import detector
    try:
        with open(target, "rb") as fh:
            head = fh.read(8192)
    except OSError as e:
        return f"cannot read {target}: {e}"
    reason = detector.binary_reason(head, name=target)
    return f"cannot edit {target}: {reason}" if reason else None


if __name__ == "__main__":
    sys.exit(main())
