#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
articulate.guard -- refuse a rewrite that breaks what the original says.

Every model rewrite in the editor layer runs through a RewriteGuard, in two
stages. First, the protected spans (code, math, links, citations, block quotes,
quoted material, freeze terms) are masked before the model sees the text and
spliced back byte for byte after it (articulate.protect); a placeholder that does
not come back exactly once and in order refuses the rewrite. Second, the spliced
candidate is compared against the text it was asked to rewrite with the meaning
guard (articulate.meaning). When any invariant is dropped, added, or changed, the
candidate is refused: the guard raises RewriteRefused, the caller keeps the
previous text, and the refusal names each placeholder or invariant that blocked it.

A caller can let named kinds change with `allow` ("number", "entity", ...), or
every kind with "all". That is an explicit opt-out, recorded in the log, never a
default. The log keeps one entry per attempt so a change report can show what was
accepted and what was refused.

The guard checks surface invariants only; see the meaning module for what a
`preserved` verdict does not prove. Standard library only.
"""
from __future__ import annotations

from . import invariants, meaning, protect


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


def parse_unprotect(unprotect):
    """The protect options with the named configurable kinds switched off."""
    if isinstance(unprotect, str):
        unprotect = unprotect.split(",")
    names = {u.strip().lower() for u in (unprotect or ()) if u and u.strip()}
    unknown = names - set(protect.CONFIGURABLE)
    if unknown:
        raise ValueError(f"cannot unprotect {sorted(unknown)}; configurable: "
                         f"{', '.join(protect.CONFIGURABLE)}")
    return {k: k not in names for k in protect.CONFIGURABLE}


class RewriteGuard:
    """Wraps a rewrite function with the protected-span layer and the meaning guard."""

    def __init__(self, *, freeze=(), allow=(), protect_opts=None):
        self.freeze = tuple(freeze or ())
        self.allow = parse_allow(allow)
        self.protect = {k: True for k in protect.CONFIGURABLE}
        self.protect.update(protect_opts or {})
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

    def run(self, rewrite_fn, text, *, tex=False):
        """Mask the protected spans, call rewrite_fn on the masked text, splice
        the spans back, and check the candidate against `text`. `tex` reads every
        inline $...$ as math, as a .tex file does."""
        masked, spans = protect.mask(text, freeze=self.freeze, tex=tex, **self.protect)
        raw = rewrite_fn(masked)
        try:
            candidate = protect.restore(raw, masked, spans)
        except protect.ProtectError as e:
            self.log.append({"accepted": False, "stage": "protected-span",
                             "blocking": e.problems, "report": None,
                             "before": text, "after": raw})
            raise RewriteRefused("protected spans did not survive the rewrite: " + str(e),
                                 stage="protected-span", blocking=e.problems) from e
        return self.check(text, candidate)

    def wrap(self, fn, *, tex=False):
        """Adapt a polish-style rewrite(text, mech, worst) to run guarded."""
        def rewrite(text, mech, worst):
            return self.run(lambda t: fn(t, mech, worst), text, tex=tex)
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
    ap.add_argument("--unprotect", default="", metavar="KINDS",
                    help="let the model edit these normally protected kinds: "
                         "quotes, blockquotes (comma list)")
    ap.add_argument("--config", default=None, metavar="PATH",
                    help="a project config file, or 'none'; default: the nearest "
                         ".articulate.json above the file")


def from_args(args, target=None):
    """A guard from the CLI flags plus the project config for `target`: the
    config's freeze terms and protect switches, with the flags applied on top."""
    from . import project
    cfg = project.for_path(target, getattr(args, "config", None)) if target else None
    freeze = tuple(getattr(args, "freeze", ()) or ()) + (cfg.freeze if cfg else ())
    opts = dict(cfg.protect) if cfg else {}
    for kind, on in parse_unprotect(getattr(args, "unprotect", "")).items():
        if not on:
            opts[kind] = False
    return RewriteGuard(freeze=freeze, allow=getattr(args, "allow_change", ""),
                        protect_opts=opts)
