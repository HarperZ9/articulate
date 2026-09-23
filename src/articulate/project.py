#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
articulate.project -- the project config file, `.articulate.json`.

The file is found by walking up from the target file's directory; the nearest
one wins. `--config PATH` overrides discovery, and `--config none` turns it off.
The format is JSON because the package supports Python 3.9, and TOML parsing
only joined the standard library in 3.11.

  {
    "version": 1,
    "profiles": {"docs/ui/**": "ux-microcopy", "reviews/*.md": "code-review"},
    "terminology": {
      "preferred": [{"use": "sign in", "instead_of": ["log in", "login"],
                     "reason": "house style"}],
      "banned": [{"term": "whitelist", "suggestion": "allowlist",
                  "reason": "inclusive language"}],
      "allowed": ["upstream"]
    },
    "freeze": ["Articulate"],
    "protect": {"quotes": true, "blockquotes": true},
    "options": {"plain-language": {"max_grade": 8}}
  }

`profiles` maps a glob (relative to the config file's directory, first match
wins) to a profile, genre, or mode. `terminology` adds project rules to every
check. `allowed` terms join the terms-of-art keep list, which exempts them from
the vocabulary and register rules; a structural device still fires. `freeze`
terms are protected spans and meaning-guard invariants in every rewrite.
`protect` switches the configurable protected kinds. `options` tunes a domain
rule pack by the pack's name.

A malformed file raises ConfigError with the file and the reason; it is never
ignored in silence. Standard library only.
"""
from __future__ import annotations

import hashlib
import json
import os
import re

from . import terms

CONFIG_NAME = ".articulate.json"
_TOP = {"version", "profiles", "terminology", "freeze", "protect", "options"}


class ConfigError(ValueError):
    """A malformed or inconsistent project config."""


class ProjectConfig:
    def __init__(self, path, data):
        self.path = path
        self.root = os.path.dirname(os.path.abspath(path))
        self.profiles = [(g, _glob_rx(g), n) for g, n in (data.get("profiles") or {}).items()]
        self.terminology = data.get("terminology") or {}
        self.freeze = tuple(data.get("freeze") or ())
        self.protect = dict(data.get("protect") or {})
        self.options = data.get("options") or {}

    def profile_for(self, target):
        """The profile named by the first glob that matches `target`, or None."""
        rel = os.path.relpath(os.path.abspath(target), self.root).replace("\\", "/")
        for _glob, rx, name in self.profiles:
            if rx.fullmatch(rel):
                return name
        return None


def _glob_rx(glob):
    """Translate a path glob to a regex: `**` spans directories, `*` and `?`
    stay inside one path segment."""
    out, i = [], 0
    while i < len(glob):
        if glob.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif glob.startswith("**", i):
            out.append(".*")
            i += 2
        else:
            c = glob[i]
            out.append("[^/]*" if c == "*" else "[^/]" if c == "?" else re.escape(c))
            i += 1
    return re.compile("".join(out))


def _fail(path, msg):
    raise ConfigError(f"{path}: {msg}")


def _check_profiles(path, profiles):
    from . import modes
    from . import profiles as _profiles
    if not isinstance(profiles, dict):
        _fail(path, "'profiles' must map a glob to a profile name")
    for glob, name in profiles.items():
        try:
            (modes.load if "/" in str(name) else _profiles.load)(name)
        except (ValueError, TypeError) as e:
            _fail(path, f"profiles[{glob!r}]: {e}")


def _check_types(path, data):
    unknown = set(data) - _TOP
    if unknown:
        _fail(path, f"unknown key(s) {sorted(unknown)}; known: {sorted(_TOP)}")
    if data.get("version", 1) != 1:
        _fail(path, f"unsupported version {data.get('version')!r}; this build reads 1")
    freeze = data.get("freeze", [])
    if not isinstance(freeze, list) or not all(isinstance(t, str) and t.strip() for t in freeze):
        _fail(path, "'freeze' must be a list of non-empty strings")
    protect = data.get("protect", {})
    if not isinstance(protect, dict) or set(protect) - {"quotes", "blockquotes"} \
            or not all(isinstance(v, bool) for v in protect.values()):
        _fail(path, "'protect' takes only 'quotes' and 'blockquotes', each true or false")


def _type_ok(value, default):
    if isinstance(default, bool):
        return isinstance(value, bool)
    if isinstance(default, (int, float)):
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, type(default))


def _check_options(path, options):
    from . import rules_ext
    if not isinstance(options, dict):
        _fail(path, "'options' must map a rule-pack name to an object")
    known = rules_ext.option_defaults()
    for name, opts in options.items():
        if name not in known:
            _fail(path, f"options[{name!r}]: no such rule pack; tunable: {sorted(known)}")
        if not isinstance(opts, dict):
            _fail(path, f"options[{name!r}] must be an object")
        bad = set(opts) - set(known[name])
        if bad:
            _fail(path, f"options[{name!r}]: unknown {sorted(bad)}; known: {sorted(known[name])}")
        for key, value in opts.items():
            if not _type_ok(value, known[name][key]):
                _fail(path, f"options[{name!r}][{key!r}] must be "
                            f"{type(known[name][key]).__name__}")


def validate(path, data):
    if not isinstance(data, dict):
        _fail(path, "the top level must be a JSON object")
    _check_types(path, data)
    _check_profiles(path, data.get("profiles", {}))
    try:
        terms.validate(data.get("terminology", {}))
    except ValueError as e:
        _fail(path, f"terminology: {e}")
    _check_options(path, data.get("options", {}))


def load(path):
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except OSError as e:
        raise ConfigError(f"{path}: cannot read: {e}") from e
    except ValueError as e:
        raise ConfigError(f"{path}: not valid JSON: {e}") from e
    validate(path, data)
    return ProjectConfig(path, data)


def discover(start):
    """The nearest config file at or above `start` (a file or a directory)."""
    d = os.path.abspath(start)
    if not os.path.isdir(d):
        d = os.path.dirname(d)
    while True:
        cand = os.path.join(d, CONFIG_NAME)
        if os.path.isfile(cand):
            return cand
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def for_path(target, override=None):
    """The config that applies to `target`: the override file, none when the
    override is "none", else the discovered file, else None."""
    if override:
        return None if override.lower() == "none" else load(override)
    if not target or target == "<stdin>":
        target = os.getcwd()
    found = discover(target)
    return load(found) if found else None


def rules_payload(cfg):
    """The parts of a config that change a check's findings, as plain data. A
    receipt embeds this so a replay re-derives under the same project rules."""
    if cfg is None:
        return None
    payload = {"terminology": cfg.terminology, "options": cfg.options}
    return payload if (cfg.terminology or cfg.options) else None


def check_payload(payload):
    """Validate a receipt's embedded project rules; raise ConfigError if malformed."""
    if not isinstance(payload, dict) or set(payload) - {"terminology", "options"}:
        raise ConfigError("receipt: project_rules must hold only terminology and options")
    try:
        terms.validate(payload.get("terminology") or {})
    except ValueError as e:
        raise ConfigError(f"receipt: terminology: {e}") from e
    _check_options("receipt", payload.get("options") or {})


def payload_sha256(payload):
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


def apply_payload(profile, payload):
    """A copy of `profile` carrying the project rules: terminology findings, the
    allowed terms on the keep list, and the rule-pack options."""
    out = dict(profile)
    if not payload:
        return out
    term = payload.get("terminology") or {}
    if term:
        out["terminology"] = term
        out["keep"] = tuple(out.get("keep", ())) + tuple(a.lower() for a in term.get("allowed", ()))
    if payload.get("options"):
        out["options"] = payload["options"]
    return out


def resolve(path, text, *, profile=None, mode=None, cfg=None):
    """(name, profile_dict): --mode, else --profile, else an in-file tag, else the
    config's glob, else path inference, else the default; with the project rules
    applied."""
    from . import modes, profiles
    if mode:
        return mode, apply_payload(modes.load(mode), rules_payload(cfg))
    name = profile or profiles.declared_profile(text or "")
    if not name and cfg is not None and path and path != "<stdin>":
        name = cfg.profile_for(path)
    if not name:
        name = profiles.profile_for(path) if path and path != "<stdin>" else profiles.DEFAULT
    loaded = modes.load(name) if "/" in name else profiles.load(name)
    return name, apply_payload(loaded, rules_payload(cfg))
