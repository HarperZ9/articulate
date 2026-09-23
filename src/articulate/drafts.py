#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
articulate.drafts -- a local, append-only, hash-chained record of drafts.

Each `record` appends one entry to `<dir>/.articulate/drafts/<name>.jsonl`: the
draft's text hash, the time, its word count and texture score, the size of the
change from the previous draft, and an optional actor label. Each entry carries
the hash of the entry before it and its own hash over its content, so an edited,
removed, or reordered entry breaks the chain. By default the draft text is also
stored, content-addressed, under `objects/`, so `verify` can re-derive every
hash, word count, and diff from the drafts themselves; `--no-snapshot` keeps
hashes only.

What it shows: that this sequence of drafts was recorded, in this order, and
that the log has not been edited since, as far as the chain can tell. What it
does not show: who typed the text (the actor label is whatever the recorder
typed), when it was typed (times come from the local clock), or that the log is
complete (a deleted tail leaves a valid shorter chain, and anyone with write
access can build a new chain from scratch). Anchor the latest entry hash
somewhere you do not control alone, such as a commit, to make a rewrite visible.
It is a record of process for a reader who asks how a document came to be. It
is not a way to pass an AI detector, and it never makes text read as human.
Standard library only; no network.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import os
from datetime import datetime, timezone

SCHEMA = "articulate/drafts/v1"
GENESIS = "sha256:" + "0" * 64


class LogBroken(ValueError):
    """The draft log fails its own chain check, so it is never extended."""


def _sha(data):
    return "sha256:" + hashlib.sha256(data.encode("utf-8")).hexdigest()


def entry_hash(entry):
    body = {k: v for k, v in entry.items() if k != "hash"}
    return _sha(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False))


def paths(target, log_dir=None):
    """(log file, objects dir) for a document."""
    base = log_dir or os.path.join(os.path.dirname(os.path.abspath(target)), ".articulate",
                                   "drafts")
    return os.path.join(base, os.path.basename(target) + ".jsonl"), os.path.join(base, "objects")


def load(log_path):
    """(entries, problems): each parsed line, and a problem for each unreadable one."""
    entries, problems = [], []
    with open(log_path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except ValueError as e:
                problems.append(f"line {n}: not JSON ({e})")
                continue
            if isinstance(entry, dict):
                entries.append(entry)
            else:
                problems.append(f"line {n}: not a JSON object")
    return entries, problems


def diff_size(before, after):
    """Lines added and removed going from `before` to `after`, and the change in
    character count."""
    sm = difflib.SequenceMatcher(None, before.splitlines(), after.splitlines(), autojunk=False)
    added = removed = 0
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op != "equal":
            removed += i2 - i1
            added += j2 - j1
    return {"lines_added": added, "lines_removed": removed,
            "chars_delta": len(after) - len(before)}


def _object(objects, sha):
    return os.path.join(objects, sha.split(":", 1)[1] + ".txt")


def _read_object(objects, sha):
    try:
        with open(_object(objects, sha), encoding="utf-8", newline="") as fh:
            return fh.read()
    except OSError:
        return None


def _measure(text):
    from . import detector
    r = detector.check_text(text)
    return r["cadence"]["words"], r["texture_score"], detector.ruleset_fingerprint()


def record(target, text, *, actor=None, log_dir=None, snapshot=True, now=None):
    """Append an entry for `text`. Returns (entry, None), or (None, reason) when
    the text is the same as the last recorded draft. Raises LogBroken, and
    appends nothing, when the existing log fails its chain check."""
    log_path, objects = paths(target, log_dir)
    entries, problems = load(log_path) if os.path.isfile(log_path) else ([], [])
    problems += _chain_problems(entries)
    if problems:
        raise LogBroken("the existing draft log is broken, so nothing was appended: "
                        + "; ".join(problems[:3]) + ". Run `articulate drafts verify`.")
    last = entries[-1] if entries else None
    sha = _sha(text)
    if last and last.get("text_sha256") == sha:
        return None, f"unchanged since draft {last.get('seq')}; nothing recorded"
    prev_text = _read_object(objects, last["text_sha256"]) if last else None
    words, texture, ruleset = _measure(text)
    entry = {
        "schema": SCHEMA, "seq": (last["seq"] + 1) if last else 1,
        "time": (now or datetime.now(timezone.utc)).isoformat(),
        "file": os.path.basename(target), "text_sha256": sha, "words": words,
        "texture_score": texture, "ruleset_version": ruleset,
        "diff": diff_size(prev_text, text) if prev_text is not None else None,
        "actor": actor or None, "snapshot": bool(snapshot),
        "prev": last["hash"] if last else GENESIS,
    }
    entry["hash"] = entry_hash(entry)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    if snapshot:
        os.makedirs(objects, exist_ok=True)
        if not os.path.isfile(_object(objects, sha)):
            with open(_object(objects, sha), "w", encoding="utf-8", newline="") as fh:
                fh.write(text)
    with open(log_path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(entry, sort_keys=True, ensure_ascii=False) + "\n")
    return entry, None


def _chain_problems(entries):
    problems, prev = [], GENESIS
    for i, e in enumerate(entries, 1):
        if e.get("schema") != SCHEMA:
            problems.append(f"draft {i}: unknown schema {e.get('schema')!r}")
        if e.get("seq") != i:
            problems.append(f"draft {i}: sequence number {e.get('seq')!r}, expected {i}")
        if e.get("prev") != prev:
            problems.append(f"draft {i}: does not link to the entry before it")
        if e.get("hash") != entry_hash(e):
            problems.append(f"draft {i}: content does not match its hash")
        prev = e.get("hash")
    return problems


def _rederive(entries, objects, current_ruleset):
    """Check each stored snapshot against its entry: text hash, words, diff, and
    (under the same ruleset) the texture score. Returns (problems, notes)."""
    problems, notes, prev_text = [], [], None
    for i, e in enumerate(entries, 1):
        sha = e.get("text_sha256")
        if not isinstance(sha, str) or not sha.startswith("sha256:"):
            problems.append(f"draft {i}: no valid text hash")
            prev_text = None
            continue
        text = _read_object(objects, sha) if e.get("snapshot") else None
        if e.get("snapshot") and text is None:
            problems.append(f"draft {i}: its stored snapshot is missing")
        elif text is not None:
            problems += _check_snapshot(i, e, text, prev_text, current_ruleset, notes)
        prev_text = text
    return problems, notes


def _check_snapshot(i, e, text, prev_text, current_ruleset, notes):
    if _sha(text) != e["text_sha256"]:
        return [f"draft {i}: its stored snapshot was altered"]
    out = []
    words, texture, ruleset = _measure(text)
    if words != e.get("words"):
        out.append(f"draft {i}: word count does not re-derive")
    if prev_text is not None and e.get("diff") != diff_size(prev_text, text):
        out.append(f"draft {i}: diff size does not re-derive")
    if e.get("ruleset_version") != current_ruleset:
        notes.append(f"draft {i}: texture score recorded under another ruleset; not re-derived")
    elif texture != e.get("texture_score"):
        out.append(f"draft {i}: texture score does not re-derive")
    return out


def _time_notes(entries):
    notes, last = [], None
    for i, e in enumerate(entries, 1):
        try:
            t = datetime.fromisoformat(e.get("time", ""))
        except (TypeError, ValueError):
            notes.append(f"draft {i}: unreadable time {e.get('time')!r}")
            continue
        if last is not None and t < last:
            notes.append(f"draft {i}: recorded time goes backwards (local clock)")
        last = t
    return notes


def verify(target, text=None, log_dir=None):
    """The verdict for a document's draft log: `intact` when the chain holds and
    every stored snapshot re-derives, `broken` otherwise, with the reasons."""
    from . import detector
    log_path, objects = paths(target, log_dir)
    if not os.path.isfile(log_path):
        return {"verdict": "missing", "log": log_path, "drafts": 0, "problems": [
            "no draft log for this file"], "notes": []}
    entries, problems = load(log_path)
    problems += _chain_problems(entries)
    snap_problems, notes = _rederive(entries, objects, detector.ruleset_fingerprint())
    problems += snap_problems
    notes += _time_notes(entries)
    if text is not None and entries:
        same = entries[-1].get("text_sha256") == _sha(text)
        notes.append(f"the current file {'matches' if same else 'differs from'} "
                     f"the last recorded draft ({entries[-1].get('seq')})")
    return {"verdict": "broken" if problems else "intact", "log": log_path,
            "drafts": len(entries), "last_hash": entries[-1].get("hash") if entries else None,
            "problems": problems, "notes": notes}
