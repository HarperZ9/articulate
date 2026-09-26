#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.fairness_corpora -- the corpus manifest the fairness harness reads.

A manifest names each corpus with its licence, upstream location and retrieval
date, and lists every document by path and SHA-256 with its set, an optional
prompt id, an optional human score and a key that pairs a document with its
rewrite. A set carries group labels as dimension=value pairs (first_language,
disability, input_method, register, age_band) and an optional window rule that
cuts a longer text to a sentence-aligned sample of about the protected set's
length. The harness refuses any file whose hash differs from the manifest, and
it never stores or prints text.

The texts stay where the licence allows them to be. Most research corpora carry
noncommercial or no-derivatives terms, so no text ships in the repository or the
package; the manifest and the content-free receipt do.

Standard library only.
"""
from __future__ import annotations

import hashlib
import json
import os
import re

SCHEMA = "articulate/fairness-manifest/v1"
DIMENSIONS = ("first_language", "disability", "input_method", "register", "age_band")
WORD = re.compile(r"\b\w+\b")          # the token rule Articulate counts words with
SENT = re.compile(r"(?<=[.!?])\s+")


class CorpusError(ValueError):
    """A manifest that is malformed, or a file that does not match its hash."""


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def load_manifest(path):
    """(manifest, manifest_hash). The hash covers the manifest's bytes, so a
    receipt names exactly which document list it measured."""
    with open(path, "rb") as fh:
        data = fh.read()
    try:
        man = json.loads(data.decode("utf-8"))
    except ValueError as e:
        raise CorpusError(f"manifest is not JSON: {e}") from e
    _validate(man)
    return man, sha256_bytes(data)


def _validate(man):
    if not isinstance(man, dict) or man.get("schema") != SCHEMA:
        raise CorpusError(f"manifest schema must be {SCHEMA!r}")
    sets = man.get("sets")
    if not isinstance(sets, dict) or not sets:
        raise CorpusError("manifest names no sets")
    corpora = man.get("corpora") or {}
    for name, s in sets.items():
        if s.get("corpus") not in corpora:
            raise CorpusError(f"set {name!r} names an unknown corpus")
        bad = set(s.get("groups", {})) - set(DIMENSIONS)
        if bad:
            raise CorpusError(f"set {name!r} uses unknown group dimensions {sorted(bad)}")
    for c in corpora.values():
        for k in ("licence", "upstream", "retrieved"):
            if not c.get(k):
                raise CorpusError(f"every corpus needs {k!r}")
    for d in man.get("documents", []):
        if d.get("set") not in sets or not d.get("path") or not d.get("sha256"):
            raise CorpusError(f"document row needs a known set, a path and a sha256: {d}")
    for c in man.get("comparisons", []):
        if c.get("protected") not in sets or c.get("reference") not in sets:
            raise CorpusError(f"comparison {c.get('name')!r} names an unknown set")
        if c.get("design") not in ("matched", "proxy"):
            raise CorpusError(f"comparison {c.get('name')!r} needs design matched or proxy")


def windows(text, target, minimum):
    """Sentence-aligned windows of at least `target` words, joined on one line.
    A remainder shorter than `minimum` words is dropped."""
    sents = [s.strip() for s in SENT.split(text.replace("\n", " ")) if s.strip()]
    out, cur, n = [], [], 0
    for s in sents:
        cur.append(s)
        n += len(WORD.findall(s))
        if n >= target:
            out.append(" ".join(cur))
            cur, n = [], 0
    if cur and n >= minimum:
        out.append(" ".join(cur))
    return out


def _normalized(text):
    return hashlib.sha256(" ".join(text.lower().split()).encode("utf-8")).hexdigest()


def load_documents(man, base):
    """Yield (doc_row, text) for every document, windowed as its set asks, after a
    hash check on the raw bytes. A document whose normalized text appears in two
    corpora is dropped from both, since the harness cannot tell which one it
    belongs to. Raises CorpusError on a missing file or a hash mismatch."""
    rows = []
    for d in man.get("documents", []):
        path = os.path.join(base, d["path"])
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError as e:
            raise CorpusError(f"cannot read {d['path']}: {e}") from e
        if sha256_bytes(data) != d["sha256"]:
            raise CorpusError(f"{d['path']} does not match its manifest hash")
        try:
            text = data.decode("utf-8").replace("\r\n", "\n")
        except UnicodeDecodeError as e:
            raise CorpusError(f"{d['path']} is not UTF-8 text: {e}") from e
        rows.append((d, text))
    seen = {}
    for d, text in rows:
        corpus = man["sets"][d["set"]]["corpus"]
        seen.setdefault(_normalized(text), set()).add(corpus)
    shared = {h for h, cs in seen.items() if len(cs) > 1}
    for d, text in rows:
        if _normalized(text) in shared:
            continue
        rule = man["sets"][d["set"]].get("window")
        if rule:
            parts = windows(text, rule["target"], rule["min"])
            if rule.get("first_only", True):
                parts = parts[:1]
            for k, w in enumerate(parts):
                yield {**d, "window": k}, w
        else:
            yield d, text


def overlap_count(man, base):
    """How many documents the cross-corpus overlap rule drops."""
    listed = len(man.get("documents", []))
    kept = {(d["path"]) for d, _t in load_documents(man, base)}
    return listed - len(kept)
