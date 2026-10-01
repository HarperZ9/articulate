"""The house voice spec, the brief made from it, and its fingerprint.

The spec lives in data/house_voice_v1.json and is published as
docs/house-voice.md. The brief is the short form a model reads at session
start. It is built from the spec and the active settings every time, so the
spec, the brief and the fingerprint in a receipt cannot drift apart.

This module reads one packaged file and imports no style rules, so the
SessionStart hook can load it at about the cost of starting Python.
"""
import hashlib
import json
import os

SPEC_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "house_voice_v1.json")
BRIEF_CEILING = 1500
OFF_HINT = "Turn this off with ARTICULATE_HOUSE_VOICE=off or `articulate house off`."
_CACHE = {}


def spec():
    """The parsed spec. Callers get a fresh copy, so no caller can change it."""
    if "spec" not in _CACHE:
        with open(SPEC_FILE, "r", encoding="utf-8") as fh:
            _CACHE["raw"] = fh.read()
        _CACHE["spec"] = json.loads(_CACHE["raw"])
    return json.loads(json.dumps(_CACHE["spec"]))


def canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def default_tuning():
    return {key: entry["default"] for key, entry in spec()["tuning"].items()}


def _active(settings):
    """The parts of the settings that change what the voice asks for."""
    if settings is None:
        return {"mode": "default", "tuning": default_tuning()}
    return {"mode": settings["mode"], "tuning": dict(settings["tuning"])}


def fingerprint(settings=None):
    """SHA-256 of the canonical spec plus the active mode and tuning."""
    body = canonical({"spec": spec(), "active": _active(settings)})
    return "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()


def brief(settings=None):
    """The brief text for the active tuning, one instruction per line."""
    s = spec()
    tuning = _active(settings)["tuning"]
    out = [s["brief"]["header"]]
    for line in s["brief"]["lines"]:
        if line.startswith("@"):
            key = line[1:]
            line = s["tuning"][key]["lines"][tuning.get(key, s["tuning"][key]["default"])]
        if line:
            out.append(line)
    return "\n".join(out)


def session_context(settings=None):
    """What the SessionStart hook hands the model: the brief, the spec version
    and fingerprint, and how to turn the voice off."""
    text = brief(settings)
    tail = "(%s, %s. %s)" % (spec()["version"], fingerprint(settings), OFF_HINT)
    return text + "\n" + tail
