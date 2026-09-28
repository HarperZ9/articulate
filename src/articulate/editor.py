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

The shared editor selects a configured backend or uses guarded deterministic
editing. A calling model can use the host edit protocol. The explicit
claude_call helper remains available and retains its local-only restriction.
"""
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
from .origin_guard import clean_notes, strip_origin_guesses
from .origin_guard import note as origin_note
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
            "to a model reading it. The editor tells the model to treat them as content "
            "to edit and not to follow them; a prompt cannot guarantee that:\n"
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
    if r.returncode != 0:
        claude_cli.raise_for_failed_call(out, err)
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


def _resolve(mode=None, profile=None, path=None):
    """(profile_dict_or_None, editor_cfg) for a mode id or a profile name. With
    neither, a file path resolves the way `check` resolves it: an in-file
    `writing-profile:` tag, then the path rules, then the default."""
    from . import profiles
    if mode:
        from . import modes
        prof = modes.load(mode)
        return prof, prof.get("editor", {})
    if profile:
        return profiles.load(profile), {}
    if path:
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                head = "".join(fh.readline() for _ in range(10))
        except OSError:
            head = None
        return profiles.resolve(path=path, text=head), {}
    return None, {}


def _execute_file(path, goal, out_path=None, passes=3, bar=4, mode=None, profile=None, backend=None):
    from .editing import run_edit
    text = open(path, encoding="utf-8", errors="replace").read()
    ext = os.path.splitext(path)[1].lower()
    warning = injection_warning(text)
    if warning:
        print(warning + "\n")
    prof, _ = _resolve(mode, profile, path)
    result = run_edit(text, goal=goal, backend=backend, mode=mode, profile=None if mode else prof,
                      is_html=ext in (".html", ".htm"), is_tex=ext == ".tex",
                      passes=passes, bar=bar)
    if "plan_id" in result and "next_step" in result:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    print(f"[{goal}] {os.path.basename(path)} (backend: {result['backend']}, "
          f"model: {result.get('model') or 'none'})")
    for attempt in result.get("attempts", []):
        print(f"[{goal}] model layer unavailable: {attempt.get('backend')}: "
              f"{attempt.get('reason', 'unavailable')}")
    if goal == "judge":
        print(result.get("assessment") or mechanical_text(text, prof)[1])
        if result.get("origin_claims_removed"):
            print(origin_note(result["origin_claims_removed"]))
    else:
        out_path = out_path or os.path.splitext(path)[0] + (".fixed" if goal == "fix" else ".polished") + ext
        accepted = result["text"]
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(accepted + ("\n" if accepted and not accepted.endswith("\n") else ""))
        if accepted != text:
            from .fix import _log_pass
            _log_pass(path, goal, backend=result["backend"], model=result.get("model"))
        print(f"[{goal}] final -> {out_path}; gate: {result.get('gate_after')}")
        if result.get("refused"):
            print(f"[{goal}] kept protected content in {len(result['refused'])} refused span(s)")
    if result.get("note"):
        print(result["note"])
    return 0

def judge(path, mode=None, profile=None, backend=None):
    return _execute_file(path, "judge", mode=mode, profile=profile, backend=backend)



def rewrite_once(text, mech, quality_notes, is_html, standard_delta="", profile=None):
    instr = rewrite_instructions(mech, profile, standard_delta, quality_notes or (), is_html)
    from .meaning_guard import guard_rewrite
    return guard_rewrite(text, strip_preamble(claude_call(instr, text)), is_html=is_html)["text"]


def quality_judge(text):
    """Score the five qualities the loop reads. Returns a dict or {}."""
    from .prompts import QUALITY_INSTRUCTIONS
    out = claude_call(QUALITY_INSTRUCTIONS, text)
    m = re.search(r"\{.*\}", out, re.S)
    if not m:
        return {}
    try:
        q = json.loads(m.group(0))
    except ValueError:
        return {}
    if isinstance(q, dict) and isinstance(q.get("worst"), list):
        q["worst"] = clean_notes(q["worst"])
    return q


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


if __name__ == "__main__":
    # `python -m articulate.editor` runs this file as __main__, and polish and fix
    # import articulate.editor. Run the package module, so both bind to one
    # editor and the circular import never sees a half-built module.
    import importlib
    sys.exit(importlib.import_module("articulate.editor").main())

from .polish import polish  # noqa: E402,F401  (polish reads the names above)
from .fix import fix, review  # noqa: E402,F401


def main(argv=None):
    """The editor command line (articulate.editor_cli)."""
    from .editor_cli import main as _main
    return _main(argv)
