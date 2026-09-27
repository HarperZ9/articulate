#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.aliases -- names retired in ruleset 0.7.0, still read for one minor
version.

Seven category ids and one profile field carried words that read as a claim
about who wrote a text. They were renamed. A user's mode, genre, profile dict or
allowlist that still spells an old name keeps working until the next minor
release, when this table goes. Nothing here is ever emitted.

Standard library only.
"""
from __future__ import annotations

CATEGORY_ALIASES = {
    "assistant-residue": "chat-interface-text",
    "assistant-closer": "closing-boilerplate",
    "email-tell": "email-stock-phrase",
    "blog-tell": "blog-stock-phrase",
    "fiction-slop-lexicon": "fiction-stock-phrase",
    "register-word": "inflated-word",
    "filler-intensifier": "intensifier",
}

# The profile field that sets which tiers block.
PROFILE_KEY_ALIASES = {"slop": "gate_level"}


def resolve_category(name):
    """The current id for a category name, reading an old id as its new one."""
    return CATEGORY_ALIASES.get(name, name)


def resolve_all(names):
    return tuple(resolve_category(n) for n in (names or ()))


def profile_field(profile, key, default=None):
    """Read a profile field by its current name, or by its retired name."""
    p = profile or {}
    if key in p:
        return p[key]
    for old, new in PROFILE_KEY_ALIASES.items():
        if new == key and old in p:
            return p[old]
    return default
