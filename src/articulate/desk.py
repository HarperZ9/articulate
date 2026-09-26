#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.desk -- the questions a reviewer should ask, inside the document
and across the field.

Two halves, always together. "Inside the document" turns the document's own
statements into questions (desk_inside). "Across the field" asks what the work
adds to its field and quotes only what the authors themselves claim
(desk_field). The desk never reads a process record, never compares one with a
disclosure and never ranks. It prepares questions; the reviewer judges.

`author=True` runs the author side before submission: presence checks for a
stated contribution, named prior work and what the work enables, plus the same
across-the-field questions. It grades none of the answers.

Standard library only.
"""
from __future__ import annotations

from . import desk_field, desk_inside

HEADER = ("Prepares the questions a reviewer should ask, inside the document and across "
          "the field. It checks the document's own statements and cannot judge "
          "contribution, novelty or significance.")
ITEM_LIMIT = ("This question points at the document's own statement. It says nothing about "
              "who or what wrote the text, or about the merit of the work.")
SCHEMA = "articulate/desk/v1"


def review(text, venue=None, disclosure=None, author=False):
    """The desk report as a dict. Deterministic; reads nothing from disk."""
    field, found = desk_field.across_field(text)
    if author:
        items = desk_inside.author_items(found)
    else:
        items = (desk_inside.venue_items(text, venue, disclosure)
                 + desk_inside.claim_items(text) + desk_inside.hidden_items(text))
    items.sort(key=lambda i: i["line"])
    for i in items:
        i["does_not_prove"] = ITEM_LIMIT
    return {"schema": SCHEMA, "header": HEADER, "venue": venue or "none",
            "side": "author" if author else "reviewer",
            "inside": {"title": "Inside the document", "items": items},
            "across_field": {"title": "Across the field", **field}}
