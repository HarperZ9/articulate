#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
articulate.guard -- refuse a rewrite that breaks what the original says.

Every model rewrite in the editor layer runs through a RewriteGuard. The guard
compares the candidate against the text it was asked to rewrite with the meaning
guard (articulate.meaning). When any invariant is dropped, added, or changed, the
candidate is refused: the guard raises RewriteRefused, the caller keeps the
previous text, and the refusal names each invariant that blocked it.

A caller can let named kinds change with `allow` ("number", "entity", ...), or
every kind with "all". That is an explicit opt-out, recorded in the log, never a
default. The log keeps one entry per attempt so a change report can show what was
accepted and what was refused.

The guard checks surface invariants only; see the meaning module for what a
`preserved` verdict does not prove. Standard library only.
"""
from __future__ import annotations

from . import invariants, meaning


class RewriteRefused(RuntimeError):
    """A rewrite was refused. `stage` names the check that refused it, and
    `blocking` lists the invariants or placeholders that blocked it."""

    def __init__(self, message, *, stage="meaning", blocking=(), report=None):
        super().__init__(message)
        self.stage = stage
        self.blocking = list(blocking)
        self.report = report


def parse_allow(allow):
    """Normalize the allowed kinds: a comma string or an iterable; "all" means
    every kind. An unknown kind raises ValueError, so a typo never allows nothing
    in silence."""
    if isinstance(allow, str):
        allow = [a for a in allow.split(",")]
    kinds = {a.strip().lower() for a in (allow or ()) if a and a.strip()}
    if "all" in kinds:
        return set(invariants.KINDS)
    unknown = kinds - set(invariants.KINDS)
    if unknown:
        raise ValueError(f"unknown invariant kind(s) {sorted(unknown)}; "
                         f"known: {', '.join(invariants.KINDS)}, all")
    return kinds


class RewriteGuard:
    """Wraps a rewrite function with the meaning guard."""

    def __init__(self, *, freeze=(), allow=()):
        self.freeze = tuple(freeze or ())
        self.allow = parse_allow(allow)
        self.log = []

    def check(self, before, after):
        """Return `after` if it keeps every invariant of `before` that is not
        allowed to change; otherwise raise RewriteRefused."""
        report = meaning.compare(before, after, freeze=self.freeze)
        block = meaning.blocking(report, self.allow)
        self.log.append({"accepted": not block, "stage": "meaning",
                         "blocking": block, "report": report,
                         "before": before, "after": after})
        if block:
            raise RewriteRefused(
                "meaning guard refused the rewrite: " + meaning.describe(block),
                stage="meaning", blocking=block, report=report)
        return after

    def run(self, rewrite_fn, text):
        """Call rewrite_fn(text) and check the candidate against `text`."""
        return self.check(text, rewrite_fn(text))

    def wrap(self, fn):
        """Adapt a polish-style rewrite(text, mech, worst) to run guarded."""
        def rewrite(text, mech, worst):
            return self.run(lambda t: fn(t, mech, worst), text)
        return rewrite

    def refusals(self):
        return [e for e in self.log if not e["accepted"]]


def add_arguments(ap):
    """The editor CLI flags that configure the guard."""
    ap.add_argument("--allow-change", default="", metavar="KINDS",
                    help="let these invariant kinds change (comma list, or 'all'); "
                         "by default a rewrite that changes any invariant is refused")
    ap.add_argument("--freeze", action="append", default=[], metavar="TERM",
                    help="a term every rewrite must keep verbatim (repeatable)")


def from_args(args):
    return RewriteGuard(freeze=getattr(args, "freeze", ()),
                        allow=getattr(args, "allow_change", ""))
