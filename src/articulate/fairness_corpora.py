#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.fairness_corpora -- the corpus manifest the fairness harness reads.

A manifest names each corpus with its licence, upstream location and retrieval
date, and lists every document by path and SHA-256 with its set, an optional
prompt id, an optional human score and a key that pairs a document with its
rewrite. A corpus released as one CSV table is named by a `tables` entry: the
file's SHA-256, the id, text, prompt and score columns, and for each set the
column values that select its rows. Rows that share an id are one document, and
their texts must agree. Such a manifest lists no document rows.

A set carries group labels as dimension=value pairs (first_language,
disability, input_method, register, age_band, proficiency) and an optional
window rule that cuts a longer text to a sentence-aligned sample of about the
protected set's length. A table set selects rows by one column value or by a
list of values, so one set can hold a band of scores. The harness refuses any file whose hash differs from the manifest, and
it never stores or prints text.

The texts stay where the licence allows them to be. Most research corpora carry
noncommercial or no-derivatives terms, so no text ships in the repository or the
package; the manifest and the content-free receipt do.

Standard library only.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re

SCHEMA = "articulate/fairness-manifest/v1"
DIMENSIONS = ("first_language", "disability", "input_method", "register", "age_band",
              "proficiency")
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
    for t in man.get("tables", []):
        _validate_table(t, sets)
    for c in man.get("comparisons", []):
        if c.get("protected") not in sets or c.get("reference") not in sets:
            raise CorpusError(f"comparison {c.get('name')!r} names an unknown set")
        if c.get("design") not in ("matched", "proxy"):
            raise CorpusError(f"comparison {c.get('name')!r} needs design matched or proxy")


TABLE_KEYS = ("corpus", "path", "sha256", "id", "text", "sets")


def _validate_table(t, sets):
    missing = [k for k in TABLE_KEYS if not t.get(k)]
    if missing or t.get("format", "csv") != "csv":
        raise CorpusError(f"a table needs {list(TABLE_KEYS)} and format csv; missing {missing}")
    for name, where in t["sets"].items():
        if name not in sets or sets[name]["corpus"] != t["corpus"]:
            raise CorpusError(f"table {t['path']!r} names an unknown set {name!r}")
        if any(isinstance(v, list) and not v for v in where.values()):
            raise CorpusError(f"table {t['path']!r}: set {name!r} has an empty value list")


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


def _file_bytes(base, path, digest):
    try:
        with open(os.path.join(base, path), "rb") as fh:
            data = fh.read()
    except OSError as e:
        raise CorpusError(f"cannot read {path}: {e}") from e
    if sha256_bytes(data) != digest:
        raise CorpusError(f"{path} does not match its manifest hash")
    return data


def _listed_rows(man, base):
    for d in man.get("documents", []):
        data = _file_bytes(base, d["path"], d["sha256"])
        try:
            text = data.decode("utf-8").replace("\r\n", "\n")
        except UnicodeDecodeError as e:
            raise CorpusError(f"{d['path']} is not UTF-8 text: {e}") from e
        yield d, text


def _matches(cell, want):
    """A set names one value, or a list of values any of which selects the row."""
    return cell in want if isinstance(want, list) else cell == want


def _table_set(t, row):
    for name, where in t["sets"].items():
        if all(_matches(row.get(k, "").strip(), v) for k, v in where.items()):
            return name
    return None


def _check_file_hash(base, path, digest):
    """Hash a large file in chunks and refuse it when the hash differs."""
    h = hashlib.sha256()
    try:
        with open(os.path.join(base, path), "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
    except OSError as e:
        raise CorpusError(f"cannot read {path}: {e}") from e
    if "sha256:" + h.hexdigest() != digest:
        raise CorpusError(f"{path} does not match its manifest hash")


def _table_rows(t, base):
    """One (doc_row, text) per id in a CSV table, after a hash check on the
    file. A row that matches no set's values is left out."""
    _check_file_hash(base, t["path"], t["sha256"])
    csv.field_size_limit(2 ** 31 - 1)
    with open(os.path.join(base, t["path"]), newline="", encoding="utf-8") as fh:
        yield from _read_table(t, csv.DictReader(fh))


def _read_table(t, reader):
    cols = [t[k] for k in ("id", "text", "prompt", "score") if t.get(k)]
    absent = [c for c in cols + [k for w in t["sets"].values() for k in w]
              if c not in (reader.fieldnames or ())]
    if absent:
        raise CorpusError(f"table {t['path']!r} has no column {absent}")
    docs = {}
    for row in reader:
        name = _table_set(t, row)
        if name is None:
            continue
        key, text = row[t["id"]], row[t["text"]].replace("\r\n", "\n")
        if key in docs:
            if docs[key][1] != text:
                raise CorpusError(f"table {t['path']!r}: id {key} has more than one text")
            continue
        score = row.get(t.get("score") or "", "").strip()
        docs[key] = ({"set": name, "path": f"{t['path']}#{key}", "key": key,
                      "prompt": row.get(t.get("prompt") or "") or None,
                      "score": int(score) if score.isdigit() else None}, text)
    yield from docs.values()


def load_documents(man, base):
    """Yield (doc_row, text) for every document, windowed as its set asks, after a
    hash check on the raw bytes. A document whose normalized text appears in two
    corpora is dropped from both, since the harness cannot tell which one it
    belongs to. Raises CorpusError on a missing file or a hash mismatch."""
    rows = list(_listed_rows(man, base))
    for t in man.get("tables", []):
        rows.extend(_table_rows(t, base))
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
    listed = len(man.get("documents", [])) + sum(
        1 for t in man.get("tables", []) for _ in _table_rows(t, base))
    kept = {(d["path"]) for d, _t in load_documents(man, base)}
    return listed - len(kept)
