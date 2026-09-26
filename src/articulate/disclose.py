#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.disclose -- a statement of tool use and contributor credit, from the log.

The statement has two parts. Assistance lists each tool the writer declared, its
version, the task verb as recorded (generated, drafted, edited, translated) and
where. Contributor credit lists CRediT roles, and only people hold them. The
lines it holds to:

  - it never lists a model or a tool as an author;
  - it refuses any claim or template that says no tool was used while the log
    holds an assistance entry;
  - it takes its verb from the recorded task, so generation never reads as
    help with editing;
  - it refuses to leave out an assistance entry the log holds;
  - input-method entries (dictation and the like) stay out unless the writer
    includes them by name.

A statement records what the writer declared. It cannot settle who composed
any words or the copyright status of model output.
Standard library only.
"""
from __future__ import annotations

from .provenance import (CREDIT_HEADING, CREDIT_ROLES, NO_TOOL_CLAIMS, NOT_A_PERSON,
                         NOT_A_PERSON_REASON, STATEMENT_TITLE)

TEMPLATES = ("general", "pip")


class DisclosureRefused(ValueError):
    """The requested statement would misstate the recorded process."""


def _norm_role(role):
    return role.replace("–", "-").replace("—", "-").replace("&", "and").strip()


def validate_contributions(contrib):
    """Raise DisclosureRefused unless every author is a person with known CRediT
    roles and every declared tool task names a person who checked it."""
    authors = (contrib or {}).get("authors", [])
    names = set()
    for a in authors:
        name = str(a.get("name", "")).strip()
        low = f" {name.lower()} "
        if not name or any(w in low for w in NOT_A_PERSON):
            raise DisclosureRefused(f"{name!r} {NOT_A_PERSON_REASON}")
        bad = {r for r in a.get("roles", []) if _norm_role(r) not in CREDIT_ROLES}
        if bad:
            raise DisclosureRefused(f"unknown CRediT roles for {name}: {sorted(bad)}")
        names.add(name)
    for task in (contrib or {}).get("tool_tasks", []):
        if task.get("checked_by") not in names:
            raise DisclosureRefused(f"tool task {task.get('task')!r} names no author who "
                                    f"checked its output")
    return authors


def _assist_line(e, pip=False):
    verb = e["verb"].capitalize()
    where = ", ".join(e.get("sections", [])) or "whole document"
    tool = e["tool"] + (f" {e['version']}" if e.get("version") else "")
    if pip:
        return [f"Assisted-by: {tool}", f"{verb}: {where}"]
    model = f" (model as declared: {e['model']})" if e.get("model") else ""
    lang = (f", from {e['source_language']} to {e['target_language']}"
            if e["verb"] == "translated" else "")
    return [f"- {verb} with {tool}{model}{lang}: {where}."]


def _check_request(assists, omit, claim, template):
    if template not in TEMPLATES:
        raise DisclosureRefused(f"unknown template {template!r}; known: {TEMPLATES}")
    left_out = [e for e in assists if e["seq"] in set(omit or ())]
    if left_out:
        raise DisclosureRefused("the log records assistance the statement would leave "
                                f"out (entries {[e['seq'] for e in left_out]})")
    if assists and claim and any(p in claim.lower() for p in NO_TOOL_CLAIMS):
        raise DisclosureRefused("the log records tool assistance, so the statement cannot "
                                "say that no tool was used")


def build(entries, contributions=None, template="general", include=(), omit=(), claim=None):
    """The statement text. Raises DisclosureRefused on any line above."""
    assists = [e for e in entries if e.get("kind") == "assist"]
    _check_request(assists, omit, claim, template)
    authors = validate_contributions(contributions)
    if template == "pip":
        lines = [ln for e in assists for ln in _assist_line(e, pip=True)]
        return "\n".join(lines) + ("\n" if lines else "")
    out = [STATEMENT_TITLE, "", "Assistance"]
    out += [ln for e in assists for ln in _assist_line(e)] or [
        "- The process log records no assistance entry."]
    if "input_method" in include:
        methods = [e for e in entries if e.get("kind") == "input_method"]
        if methods:
            out += ["", "Input method (included by the writer)"]
            out += [f"- {e['method']}: {', '.join(e['sections'])}." for e in methods]
    if authors:
        out += ["", CREDIT_HEADING]
        out += [f"- {a['name']}: {'; '.join(_norm_role(r) for r in a.get('roles', []))}."
                for a in authors]
    out += ["", "Responsibility",
            "The authors named above take responsibility for every line of this text."]
    if claim:
        out += ["", claim]
    return "\n".join(out) + "\n"
