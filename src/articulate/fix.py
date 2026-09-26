#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.fix -- one rewrite toward the reader, self-checked, and the review.

`fix` rewrites the text so its intended reader can follow it on one read, then
re-checks the rewrite under the same profile or mode, for up to `passes` rounds.
On a math file every span is masked before the model call and spliced back
after. The rewrite is a suggestion; the writer decides.
"""
import os

from . import editor as ed


def _call(is_html, prof, delta):
    def call(t, mech):
        instr = ed.rewrite_instructions(mech, prof, delta, (), is_html)
        return ed.strip_preamble(ed.claude_call(instr, t))
    return call


def _one_pass(attempt, text, path, out_path, prof, call):
    """Returns (status, text). 'done' and 'again' wrote a rewrite; 'stop' wrote
    nothing because the last rewrite had no findings; 'failed' wrote nothing."""
    clean_before, mech = ed.mechanical(path if attempt == 1 else out_path, prof)
    if attempt > 1 and clean_before:
        return "stop", text
    try:
        # On a math file the model sees placeholders, never a formula.
        result = (ed.masked_rewrite(text, call, prof) if ed.is_math_file(path)
                  else call(text, mech))
    except ed._UNAVAILABLE as e:
        print(f"[fix] pass {attempt} failed: {e}")
        return "failed", text
    if not result.strip():
        print(f"[fix] pass {attempt}: empty result, stopping")
        return "failed", text
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(result + ("" if result.endswith("\n") else "\n"))
    # The self-check reads the rewrite under the same profile as the first pass.
    clean_after, _ = ed.mechanical(out_path, prof)
    print(f"[fix] pass {attempt}: {'no findings' if clean_after else 'findings remain'} -> {out_path}")
    return ("done" if clean_after else "again"), result


def _log_pass(path, name):
    from .process_events import record_editor_pass
    from .process_ledger import LogBroken
    try:
        if record_editor_pass(path, name):
            print(f"[{name}] recorded an assistance entry in this document's process log")
    except LogBroken as e:
        print(f"[{name}] the process log is broken, so no entry was added: {e}")


def fix(path, out_path, passes, mode=None, profile=None):
    ext = os.path.splitext(path)[1]
    out_path = out_path or os.path.splitext(path)[0] + ".fixed" + ext
    text = open(path, encoding="utf-8", errors="replace").read()
    warn = ed.injection_warning(text)
    if warn:
        print(warn + "\n")
    prof, ecfg = ed._resolve(mode, profile, path)
    call = _call(ext.lower() in (".html", ".htm"), prof, ecfg.get("standard_delta", ""))
    wrote = False
    for attempt in range(1, passes + 1):
        status, text = _one_pass(attempt, text, path, out_path, prof, call)
        wrote = wrote or status in ("done", "again")
        if status == "failed":
            if wrote:
                # An earlier pass already wrote a rewrite; the log records it
                # even though this pass failed.
                _log_pass(path, "fix")
            return 1
        if status in ("done", "stop"):
            break
    if wrote:
        _log_pass(path, "fix")
    _, mech_final = ed.mechanical(out_path, prof)
    print(f"\n[fix] final:{os.path.basename(out_path)}")
    print(f"[fix] {mech_final.splitlines()[0]}")
    print("[fix] the rewrite is a suggestion; read it against the original before you ship it.")
    return 0


def review(path, mode=None, profile=None):
    prof, _ = ed._resolve(mode, profile, path)
    _clean, mech = ed.mechanical(path, prof)
    print(f"[review] {os.path.basename(path)}")
    print(f"  checks: {mech}\n")
    ed.judge(path, mode, profile)
