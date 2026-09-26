#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.process_export -- the Articulate process summary, and verify.

`<document>.process-summary.json`, schema articulate/process-summary/v1. The
default export holds the document hashes, the entry sequence with days, each
draft's commitment, the declared assistance, review roles and outcomes, and the
disclosure statement. Every other field (word counts, diff sizes, times,
shareable labels and citations, input methods, reviewer names) is added only
when the writer names it. `reveal` attaches the text and salt of chosen drafts
so a reader can check each against its commitment.

The actions list follows the C2PA data model so a signed manifest could be built
from it later: the first action is c2pa.created or c2pa.opened, each action
carries its own IPTC digital source type, sections are textual changes, and a
translation carries BCP 47 source and target languages. People stay out of the
actions. This file is unsigned. It is not a Content Credential and not an EU AI
Act Article 50 marking.

`verify` reports intact or broken with reasons. It reports no gaps, no intervals
between entries and no clock notes. Standard library only.
"""
from __future__ import annotations

import hashlib
import os

from . import disclose
from . import process_commit as pc
from . import process_ledger as pl
from .provenance import SOURCE_TYPE, iptc_uri
from .tool_text import DOES_NOT_PROVE

SCHEMA = "articulate/process-summary/v1"
LIMITS = (
    "This summary shows that texts with these commitments were logged in this order, "
    "which tools the writer declared, and, with an anchor, that the log existed by the "
    "anchor's time. It does not show who composed the words, when anything happened "
    "before the first anchor, or that the record is complete. A writer can build a log "
    "after the fact. An absent record shows nothing about a writer.")
_BASE = ("seq", "kind", "day", "hash")
_DEFAULT = {"init": (), "draft": ("commitment",), "note": (), "source": (),
            "assist": ("tool", "version", "verb", "sections", "model", "receipt", "guard",
                       "source_type", "source_language", "target_language"),
            "review": ("role", "outcome", "editorial_responsibility"),
            "continuation": ("continues", "reason"),
            "anchor": ("git_commit", "token_sha256")}
OPTIONAL = {"words": ("draft", ("words",)), "diff": ("draft", ("lines_added", "lines_removed")),
            "time": ("draft", ("time",)), "review_names": ("review", ("name", "reviewed")),
            "labels": ("note", ("label",)), "citations": ("source", ("citation",))}


def _export_entry(e, include):
    kind = e.get("kind")
    if kind == "input_method" and "input_method" not in include:
        return None
    keep = set(_BASE) | set(_DEFAULT.get(kind, ()))
    if kind == "input_method":
        keep |= {"method", "sections"}
    for name, (k, fields) in OPTIONAL.items():
        if name in include and k == kind:
            if kind in ("note", "source") and not e.get("shareable"):
                continue
            keep |= set(fields)
    return {k: v for k, v in e.items() if k in keep}


def _action(e, first):
    if e["kind"] == "draft":
        code = SOURCE_TYPE["written" if first else "human-edit"]
        return {"action": "c2pa.created" if first else "c2pa.edited",
                "digitalSourceType": iptc_uri(code), "entry": e["seq"]}
    verb = e["verb"]
    code = e["source_type"] if verb == "translated" else SOURCE_TYPE[verb]
    act = {"action": {"translated": "c2pa.translated"}.get(verb, "c2pa.edited"),
           "digitalSourceType": iptc_uri(code), "entry": e["seq"],
           "softwareAgent": {"name": e["tool"], **({"version": e["version"]}
                                                   if e.get("version") else {})},
           "changes": [{"type": "textual", "description": s} for s in e["sections"]]}
    if verb == "translated":
        act.update(sourceLanguage=e["source_language"], targetLanguage=e["target_language"])
    if first and verb in ("generated", "drafted"):
        act["action"] = "c2pa.created"
    return act


def actions(entries):
    out = []
    for e in (x for x in entries if x.get("kind") in ("draft", "assist")):
        out.append(_action(e, first=not out))
    if out and out[0]["action"] != "c2pa.created":
        out.insert(0, {"action": "c2pa.opened"})
    return out


def _hashes(doc):
    with open(doc, "rb") as fh:
        data = fh.read()
    text = data.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
    return ("sha256:" + hashlib.sha256(data).hexdigest(),
            "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest())


def _reveals(doc, entries, reveal):
    salts = pc.load_salts(pl.paths(doc)["salts"])
    by_seq = {e["seq"]: e for e in entries}
    out = []
    for seq, text in sorted((reveal or {}).items()):
        e = by_seq.get(seq)
        if not e or e.get("kind") != "draft":
            raise ValueError(f"entry {seq} is not a draft")
        if text is None:
            snap = os.path.join(pl.paths(doc)["objects"], f"{seq}.txt")
            if not os.path.isfile(snap):
                raise ValueError(f"no snapshot for draft {seq}; pass the draft's text")
            with open(snap, encoding="utf-8", newline="") as fh:
                text = fh.read()
        salt = salts.get(str(seq), {}).get("salt")
        if not salt or not pc.opens(e["commitment"], salt, text):
            raise ValueError(f"the text given for draft {seq} does not open its commitment")
        out.append({"seq": seq, "salt": salt, "text": text})
    return out


def summary(doc, include=(), reveal=None, contributions=None):
    entries, problems = pl.load(doc)
    problems += pl.chain_problems(entries)
    file_sha, text_sha = _hashes(doc)
    reviews = [e for e in entries if e.get("kind") == "review"]
    return {
        "schema": SCHEMA, "title": "Articulate process summary",
        "document": os.path.basename(doc), "file_sha256": file_sha, "text_sha256": text_sha,
        "chain": {"state": "broken" if problems else "intact", "problems": problems,
                  "entries": len(entries)},
        "entries": [x for x in (_export_entry(e, set(include)) for e in entries) if x],
        "actions": actions(entries),
        "editorial_responsibility": [r["role"] for r in reviews
                                     if r.get("editorial_responsibility")],
        "disclosure": disclose.build(entries, contributions, include=include),
        "reveals": _reveals(doc, entries, reveal),
        "limits": LIMITS, "does_not_prove": DOES_NOT_PROVE,
    }


def verify_log(doc):
    entries, problems = pl.load(doc)
    problems += pl.chain_problems(entries)
    return {"state": "broken" if problems else "intact", "entries": len(entries),
            "problems": problems}


def verify_summary(summ):
    """Check each revealed draft against the commitment the summary lists."""
    problems = []
    commits = {e["seq"]: e.get("commitment") for e in summ.get("entries", [])}
    for r in summ.get("reveals", []):
        if not pc.opens(commits.get(r.get("seq"), ""), r.get("salt", ""), r.get("text", "")):
            problems.append(f"revealed draft {r.get('seq')} does not open its commitment")
    if summ.get("schema") != SCHEMA:
        problems.append("unknown summary schema")
    return {"state": "broken" if problems else "intact", "problems": problems}
