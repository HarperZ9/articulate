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


def _log_pass(path, name, backend=None, model=None):
    from .process_events import record_editor_pass
    from .process_ledger import LogBroken
    try:
        if record_editor_pass(path, name, backend=backend, model=model):
            print(f"[{name}] recorded an assistance entry in this document's process log")
    except LogBroken as e:
        print(f"[{name}] the process log is broken, so no entry was added: {e}")


def fix(path, out_path, passes, mode=None, profile=None, backend=None):
    return ed._execute_file(path, "fix", out_path, passes, mode=mode, profile=profile, backend=backend)


def review(path, mode=None, profile=None, backend=None):
    prof, _ = ed._resolve(mode, profile, path)
    _clean, mech = ed.mechanical(path, prof)
    print(f"[review] {os.path.basename(path)}")
    print(f"  checks: {mech}\n")
    ed.judge(path, mode, profile, backend=backend)
