#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.polish -- the quality loop.

Each pass rewrites the best text so far, scores it on five qualities for its
intended reader, and keeps it only when editor.accept() says so: no score falls,
the gate under the chosen profile does not go from ok to blocked, and no
required advisory opens. The loop stops when every quality clears the bar, the
gate is ok and the required advisories are closed, or when the passes run out.
No density, cadence statistic or outside score enters any decision.

rewrite_fn(text, summary, notes) and judge_fn(text) are injectable for testing.
"""
import os

from . import editor as ed


class _Loop:
    """The text, its check result, its scores and the files it writes."""

    def __init__(self, path, out_path, bar, prof, ecfg):
        self.path, self.out_path, self.bar = path, out_path, bar
        self.prof, self.required = prof, set(ecfg.get("require_fix", ()))
        self.best = open(path, encoding="utf-8", errors="replace").read()
        self.accepted = 0

    def evaluate(self, text):
        r = ed.assess(text, self.prof)
        return r, {f["category"] for f in r["low"]} & self.required

    def write(self, text):
        with open(self.out_path, "w", encoding="utf-8") as fh:
            fh.write(text + ("" if text.endswith("\n") else "\n"))


def _row(attempt, sc, gate, note):
    print(f"{attempt:<5}" + "".join(f"{sc.get(k, 0):<5}" for k in ed.QUALITIES)
          + f"{gate:<9}{note}")


def _scores(q):
    return {k: int(q.get(k, 0) or 0) for k in ed.QUALITIES}


def _callables(path, loop, ecfg, rewrite_fn, judge_fn):
    """(judge, rewrite) for this file. On a math file no model call sees a
    formula: the judge scores masked text, and the rewrite gets masked text, a
    findings summary built from it and notes with any math scrubbed."""
    is_html = os.path.splitext(path)[1].lower() in (".html", ".htm")
    delta = ecfg.get("standard_delta", "")
    base_judge = judge_fn or ed.quality_judge
    base_rewrite = rewrite_fn or (lambda t, mech, worst: ed.rewrite_once(
        t, mech, worst, is_html, delta, profile=loop.prof))
    if not ed.is_math_file(path):
        return base_judge, base_rewrite

    def judge(t):
        return base_judge(ed.mask_math(t)[0])

    def rewrite(t, mech, worst):
        notes = ed.scrub_math_notes(worst)
        return ed.masked_rewrite(t, lambda m, mm: base_rewrite(m, mm, notes), loop.prof)
    return judge, rewrite


def _run(loop, passes, judge, rewrite):
    r, open_req = loop.evaluate(loop.best)
    q = judge(loop.best)
    sc = _scores(q)
    for attempt in range(passes + 1):
        met = r["gate"] == "ok" and not open_req and min(sc.values() or [0]) >= loop.bar
        _row(attempt, sc, r["gate"], "met" if met else
             ("required advisory open" if open_req else ""))
        if met or attempt == passes:
            return
        worst = list(q.get("worst", []))
        if open_req:
            worst.append("clear required advisories: " + ", ".join(sorted(open_req)))
        try:
            cand = rewrite(loop.best, ed.mechanical_text(loop.best, loop.prof)[1], worst)
        except ed._UNAVAILABLE as e:
            print(f"[polish] rewrite failed: {e}")
            return
        if not cand or not cand.strip():
            print("[polish] empty rewrite; stopping")
            return
        try:
            cq = judge(cand)
        except ed._UNAVAILABLE as e:
            # The backend can drop halfway through, for example on a rate limit.
            print(f"[polish] judge failed: {e}; kept the best version so far")
            return
        cr, c_open = loop.evaluate(cand)
        ok, why = ed.accept(sc, _scores(cq), r["gate"], cr["gate"], c_open - open_req, None)
        if not ok:
            _row(attempt + 1, _scores(cq), cr["gate"], f"REJECTED ({why}); kept best")
            return
        loop.best, r, open_req, q, sc = cand, cr, c_open, cq, _scores(cq)
        loop.write(loop.best)
        loop.accepted += 1


def polish(path, out_path, passes, bar, mode=None, rewrite_fn=None, judge_fn=None,
           profile=None):
    ext = os.path.splitext(path)[1]
    out_path = out_path or os.path.splitext(path)[0] + ".polished" + ext
    prof, ecfg = ed._resolve(mode, profile)
    loop = _Loop(path, out_path, bar, prof, ecfg)
    warn = ed.injection_warning(loop.best)
    if warn:
        print(warn + "\n")
    loop.write(loop.best)
    if ecfg and not ecfg.get("run_fix_by_default", True):
        print(f"[polish] mode {mode} does not rewrite by default (authorial voice "
              f"governs); use --judge. No change written.")
        return 0
    judge, rewrite = _callables(path, loop, ecfg, rewrite_fn, judge_fn)
    print(f"[polish] {os.path.basename(path)}" + (f" [{mode}]" if mode else "")
          + f" -> {os.path.basename(out_path)} (bar: every quality >= {bar}/5, "
            f"gate ok, required fixes cleared)\n")
    print(f"{'pass':<5}{'conc':<5}{'comm':<5}{'econ':<5}{'rhyt':<5}{'rest':<5}{'gate':<9}note")
    try:
        _run(loop, passes, judge, rewrite)
    except ed._UNAVAILABLE as e:
        print(f"\n[polish] model layer unavailable: {e}")
        print("[polish] the local checks still work; rerun when the backend is restored.")
        return 1
    if loop.accepted:
        from .fix import _log_pass
        _log_pass(path, "polish")
    print(f"\n[polish] final -> {out_path}")
    print("[polish] accepted on the reader's qualities and the gate, never on an outside score.")
    return 0
