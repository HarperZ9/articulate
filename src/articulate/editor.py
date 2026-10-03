#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
articulate-judge.py  --  the editor layer for Articulate.

check-writing-devices.py is the fast, deterministic detector: it flags the
mechanical tells (devices, register, cadence) and scores machine texture. This
layer adds the two things a detector cannot do on its own, the two things a
skilled editor does:

  --judge FILE   Read the prose for JUDGMENT-level quality, the failures regex
                 cannot see: confident emptiness (a fluent paragraph with no
                 fact a reader could restate), vague abstraction, hedging with
                 no committed position, a metaphor standing in for an available
                 literal term, a buried point, verbosity out of proportion to
                 the task, weak verbs, passive overuse. Reports, does not edit.

  --fix FILE     Rewrite the prose to skilled-author quality in the plain-writing
                 standard, preserving every fact, number, claim, citation, term
                 of art and structural element, then re-run the mechanical
                 detector and iterate until the rewrite is clean. Offers the
                 fix: writes the rewrite (to --out, or <name>.fixed.<ext>).

  --review FILE  Mechanical detect + judge in one report. No rewrite.

The rewrite target is WRITING QUALITY, gated by the mechanical tell-checker.
It is not gated by, or tuned toward, any AI-detector score.

The shared editor selects a configured backend or uses local deterministic
editing. A calling model can also use the host edit protocol. The legacy
claude_call helper remains available for explicit callers. Usage:
    python articulate-judge.py --judge FILE
    python articulate-judge.py --fix FILE [--out OUT] [--passes N]
    python articulate-judge.py --review FILE
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

from .claude_cli import ClaudeUnavailable  # noqa: F401  (re-exported for callers)
from . import claude_cli
from .process_events import log_pass

HERE = os.path.dirname(os.path.abspath(__file__))

# Kept importable here for existing callers; all execution paths use one prompt set.
from .prompts import (STANDARD, CONTENT_BOUNDARY, QUALITIES, hardened,
                      _neutralize, _detector_block)


def injection_warning(text):
    """A one-block warning listing document lines that read as an assistant
    directive, or "" if none. The editor prints this before a rewrite; it does not
    block, because a document may quote such patterns in good faith."""
    from . import detector
    hits = detector.detect_injection(text)
    if not hits:
        return ""
    lines = [f"  L{h['line']} [{h['category']}] {h['label']}: {h['snippet']}" for h in hits]
    return ("[editor] WARNING: the document contains lines that read as instructions "
            "to an assistant. They are treated as content to edit, never obeyed:\n"
            + "\n".join(lines))


# Math spans a rewrite must never touch: a changed symbol, quantifier order, or
# inequality direction changes a theorem. Longest and display forms first so an
# inline pass does not split a display span.
_MATH_PATTERNS = [
    re.compile(r"\$\$.*?\$\$", re.S),
    re.compile(r"\\\[.*?\\\]", re.S),
    re.compile(r"\\\(.*?\\\)", re.S),
    re.compile(r"\$(?:\\.|[^$\\])*\$", re.S),
    re.compile(r"\\begin\{(equation|align|gather|multline|eqnarray|split|theorem"
               r"|lemma|proof|definition|proposition|corollary|claim)\*?\}"
               r".*?\\end\{\1\*?\}", re.S),
]
_MATH_PLACEHOLDER = "\u2983MATH{}\u2984"   # a distinctive bracket unlikely to be edited


def mask_math(text):
    """Replace every LaTeX math span with a numbered placeholder and return
    (masked_text, spans). The model never sees the math, so it cannot alter a
    formula. This is a structural guarantee that holds whatever the model returns."""
    spans = []

    def repl(m):
        spans.append(m.group(0))
        return _MATH_PLACEHOLDER.format(len(spans) - 1)

    for rx in _MATH_PATTERNS:
        text = rx.sub(repl, text)
    return text, spans


def splice_math(text, spans):
    """Restore masked math spans by placeholder, byte for byte."""
    for i, original in enumerate(spans):
        text = text.replace(_MATH_PLACEHOLDER.format(i), original)
    return text


def mechanical(path, profile=None):
    """Return (clean, summary_text) from the deterministic detector, for a file."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return True, "no mechanical findings"
    return mechanical_text(text, profile)


def assess(text, profile=None):
    """The full detector result under a profile/mode (findings + gate + low
    advisories). The editor threads the mode here, so it is no longer profile-blind."""
    from . import detector
    return detector.check_text(text, profile=profile)


def mechanical_text(text, profile=None):
    """Return (clean, summary_text) from the deterministic detector, for text."""
    r = assess(text, profile)
    hits = r["high"] + r["medium"]
    lines = [f"  L{h['line']} [{h['tier']} {h['category']}] {h['label']}: {h['snippet']}"
             for h in hits]
    tex = f"texture score {r['texture_score']}/100"
    summary = (f"{len(hits)} mechanical tell(s); {tex}\n" + "\n".join(lines)) if hits \
        else f"clean of mechanical tells; {tex}"
    return len(hits) == 0, summary


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


def _execute_file(path, goal, out_path=None, passes=3, bar=4, mode=None, backend=None):
    from .editing import run_edit
    text = open(path, encoding="utf-8", errors="replace").read()
    ext = os.path.splitext(path)[1].lower()
    warning = injection_warning(text)
    if warning:
        print(warning + "\n")
    result = run_edit(text, goal=goal, backend=backend, mode=mode,
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
        print(result.get("assessment") or mechanical_text(text, _resolve_mode(mode)[0])[1])
    else:
        out_path = out_path or os.path.splitext(path)[0] + (".fixed" if goal == "fix" else ".polished") + ext
        accepted = result["text"]
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(accepted + ("\n" if accepted and not accepted.endswith("\n") else ""))
        if accepted != text:
            log_pass(path, goal, backend=result["backend"], model=result.get("model"))
        print(f"[{goal}] final -> {out_path}; gate: {result.get('gate_after')}")
        if result.get("refused"):
            print(f"[{goal}] kept protected content in {len(result['refused'])} refused span(s)")
    if result.get("note"):
        print(result["note"])
    return 0


def judge(path, mode=None, backend=None):
    return _execute_file(path, "judge", mode=mode, backend=backend)


def rewrite_once(text, mech, quality_notes, is_html, standard_delta=""):
    """Compatibility helper for an explicitly requested Claude rewrite."""
    from .prompts import rewrite_instructions
    from .meaning_guard import guard_rewrite
    output = strip_preamble(claude_call(
        rewrite_instructions(mech, quality_notes, is_html, standard_delta), text))
    return guard_rewrite(text, output, is_html=is_html)["text"]


def quality_judge(text):
    from .prompts import quality_instructions
    from .editing import _scores
    return _scores(claude_call(quality_instructions(), text)) or {}


def _resolve_mode(mode):
    """(profile_dict_or_None, editor_cfg) for a mode_id string, or (None, {})."""
    if not mode:
        return None, {}
    from . import modes
    prof = modes.load(mode)
    return prof, prof.get("editor", {})


def _row(attempt, sc, gate, note):
    print(f"{attempt:<5}" + "".join(f"{sc.get(k, 0):<5}" for k in QUALITIES)
          + f"{gate:<9}{note}")


def polish(path, out_path, passes, bar, mode=None, rewrite_fn=None, judge_fn=None, backend=None):
    """The quality loop with a MONOTONIC NO-REGRESSION contract: a rewrite pass is
    accepted only if it keeps the detector gate ok AND lowers none of the five
    quality scores. A pass that regresses any score is discarded and the best kept.
    Mode-aware: it consumes the mode's quality weights, required-fix advisories, and
    standard delta. The stopping criterion is writing quality, never a detector score.

    rewrite_fn(text, mech, worst) and judge_fn(text) are injectable for testing."""
    if rewrite_fn is None and judge_fn is None:
        return _execute_file(path, "polish", out_path, passes, bar, mode, backend)
    ext = os.path.splitext(path)[1]
    if not out_path:
        out_path = os.path.splitext(path)[0] + ".polished" + ext
    is_html = ext.lower() in (".html", ".htm")
    is_tex = ext.lower() == ".tex"
    text = open(path, encoding="utf-8", errors="replace").read()
    warn = injection_warning(text)
    if warn:
        print(warn + "\n")

    prof, ecfg = _resolve_mode(mode)
    require_fix = set(ecfg.get("require_fix", ()))
    standard_delta = ecfg.get("standard_delta", "")
    open(out_path, "w", encoding="utf-8").write(text)
    if ecfg and not ecfg.get("run_fix_by_default", True):
        print(f"[polish] mode {mode} does not rewrite by default (authorial voice "
              f"governs); use --judge. No change written.")
        return 0

    judge = judge_fn or quality_judge
    base_rewrite = rewrite_fn or (lambda t, mech, worst:
                                  rewrite_once(t, mech, worst, is_html, standard_delta))
    if is_tex:
        # Mask every math span before the rewrite and splice it back after, so a
        # formula is preserved byte for byte whatever the model returns.
        def rewrite(t, mech, worst):
            masked, spans = mask_math(t)
            return splice_math(base_rewrite(masked, mech, worst), spans)
    else:
        rewrite = base_rewrite

    def evaluate(t):
        r = assess(t, prof)
        return r, {f["category"] for f in r["low"]}

    print(f"[polish] {os.path.basename(path)}" + (f" [{mode}]" if mode else "")
          + f" -> {os.path.basename(out_path)} (bar: every quality >= {bar}/5, "
            f"gate ok, required fixes cleared)\n")
    print(f"{'pass':<5}{'conc':<5}{'comm':<5}{'econ':<5}{'rhyt':<5}{'rest':<5}{'gate':<9}note")

    try:
        r, low_cats = evaluate(text)
        q = judge(text)
        sc = {k: int(q.get(k, 0) or 0) for k in QUALITIES}
    except (RuntimeError, subprocess.TimeoutExpired) as e:
        print(f"\n[polish] model layer unavailable: {e}")
        print("[polish] the deterministic detector still works; rerun when the backend is restored.")
        return 1

    best = text
    for attempt in range(passes + 1):
        req_ok = not (require_fix & low_cats)
        met = r["gate"] == "ok" and req_ok and (min(sc.values()) if sc else 0) >= bar
        _row(attempt, sc, r["gate"], "met" if met else ("required advisory open" if not req_ok else ""))
        if met or attempt == passes:
            break
        worst = list(q.get("worst", []))
        if require_fix & low_cats:
            worst.append("clear required advisories: " + ", ".join(sorted(require_fix & low_cats)))
        try:
            _, mech = mechanical_text(best, prof)
            cand = rewrite(best, mech, worst)
            from .meaning_guard import guard_rewrite
            cand = guard_rewrite(best, cand, is_html=is_html, is_tex=is_tex)["text"]
        except (RuntimeError, subprocess.TimeoutExpired) as e:
            print(f"[polish] rewrite failed: {e}")
            break
        if not cand or not cand.strip():
            print("[polish] empty rewrite; stopping")
            break
        try:
            cq = judge(cand)
        except (RuntimeError, subprocess.TimeoutExpired) as e:
            # The backend can drop halfway through, for example on a rate limit.
            print(f"[polish] judge failed: {e}; kept the best version so far")
            break
        cr, clow = evaluate(cand)
        csc = {k: int(cq.get(k, 0) or 0) for k in QUALITIES}
        regresses = any(csc[k] < sc[k] for k in QUALITIES)
        gate_worse = cr["gate"] == "blocked" and r["gate"] == "ok"
        if regresses or gate_worse:
            _row(attempt + 1, csc, cr["gate"], "REJECTED (regression); kept best")
            break
        best, r, low_cats, q, sc = cand, cr, clow, cq, csc
        open(out_path, "w", encoding="utf-8").write(best + ("\n" if not best.endswith("\n") else ""))

    if best != text:
        log_pass(path, "polish")
    print(f"\n[polish] final -> {out_path}")
    print("[polish] gated on quality with a no-regression contract, never on a detector score.")
    return 0


def fix(path, out_path, passes, mode=None, backend=None):
    return _execute_file(path, "fix", out_path, passes, mode=mode, backend=backend)


def review(path, mode=None, backend=None):
    prof, _ = _resolve_mode(mode)
    clean, mech = mechanical(path, prof)
    print(f"[review] {os.path.basename(path)}")
    print(f"  mechanical: {mech}\n")
    judge(path, mode, backend)


def main():
    ap = argparse.ArgumentParser(description="Articulate editor layer (judge / fix).")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--judge", metavar="FILE")
    g.add_argument("--fix", metavar="FILE")
    g.add_argument("--polish", metavar="FILE")
    g.add_argument("--review", metavar="FILE")
    ap.add_argument("--out", metavar="FILE", default=None)
    ap.add_argument("--passes", type=int, default=3)
    ap.add_argument("--bar", type=int, default=4, help="quality bar 1-5 for --polish")
    ap.add_argument("--mode", default=None,
                    help="a writing mode (domain/articulation, e.g. memo/argue)")
    ap.add_argument("--backend", default=None,
                    choices=("auto", "host", "sampling", "anthropic", "claude-cli", "openai", "ollama", "none"))
    args = ap.parse_args()

    target = args.judge or args.fix or args.polish or args.review
    if not os.path.isfile(target):
        print(f"[articulate] no such file: {target}")
        return 2
    from . import detector
    try:
        with open(target, "rb") as fh:
            head = fh.read(8192)
    except OSError as e:
        print(f"[articulate] cannot read {target}: {e}")
        return 2
    reason = detector.binary_reason(head, name=target)
    if reason:
        print(f"[articulate] cannot edit {target}: {reason}")
        return 2
    if args.judge:
        judge(args.judge, args.mode, args.backend)
    elif args.review:
        review(args.review, args.mode, args.backend)
    elif args.polish:
        return polish(args.polish, args.out, max(1, args.passes),
                      max(1, min(5, args.bar)), mode=args.mode, backend=args.backend)
    else:
        return fix(args.fix, args.out, max(1, args.passes), mode=args.mode, backend=args.backend)
    return 0


if __name__ == "__main__":
    sys.exit(main())
