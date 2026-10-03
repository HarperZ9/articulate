"""Rules that run after the v0.5.2 detector, outside its pinned ruleset.

The detector reads every document with one frozen ruleset. Domain rule packs
add deterministic rules for one kind of writing, switched on by a domain
profile's `rule_packs` field (articulate.domains). They run in this layer, so
the detector source and its ruleset fingerprint never change.

`scan(text, lines, profile)` returns the extra findings by tier as detector
span records; articulate.checkext adds them to a check result and recomputes
the gate. `fingerprint()` hashes the packs, their defaults and the domain
profile definitions, so a receipt that used them reads Unverifiable when they
change. Standard library only.
"""
import hashlib
import json
import re

from . import detector, invariants

SEMVER = "1.0.0"
# name -> module. A pack module exposes NAME, CATEGORIES, OPTIONS (defaults),
# scan(text, prose, options, make) -> {"HIGH": [...], "MEDIUM": [...],
# "LOW": [...]}, and fingerprint() -> list of strings.
PACKS = {}

_TAG = re.compile(r"<[^<>\n]{1,400}>")


def mask_line(line):
    """Mask code, URLs and emails, tags, and TeX with equal-length spaces. The
    URL and tag patterns are bounded, so a long line of dotted tokens or of
    unclosed angle brackets stays linear."""
    for rx in (detector.INLINE_CODE, invariants.URL, _TAG, detector.TEX):
        line = rx.sub(detector._blank, line)
    return line


def prose_lines(lines):
    """(line_no, offset, raw, masked) for each prose line: fenced code and YAML
    frontmatter are skipped, and code, URLs, tags, and TeX are masked with
    equal-length spaces so offsets stay valid in the raw line."""
    in_fence = False
    in_fm = bool(lines) and lines[0].strip() == "---"
    off = 0
    for i, raw in enumerate(lines, 1):
        start, off = off, off + len(raw)
        if detector.FENCE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if in_fm:
            if i > 1 and raw.strip() == "---":
                in_fm = False
            continue
        yield i, start, raw, mask_line(raw)


def active(profile):
    """True when the profile switches on any rule in this layer."""
    return bool(profile and profile.get("rule_packs"))


def scan(text, lines, profile):
    """Extra findings (high, medium, low) from the profile's rule packs."""
    found = {"HIGH": [], "MEDIUM": [], "LOW": []}
    options = profile.get("options") or {}
    for name in profile.get("rule_packs", ()):
        pack = PACKS[name]
        opts = dict(pack.OPTIONS, **options.get(name, {}))
        for tier, items in pack.scan(text, list(prose_lines(lines)), opts,
                                     detector._mk).items():
            found[tier].extend(items)
    return found["HIGH"], found["MEDIUM"], found["LOW"]


def categories():
    cats = set()
    for pack in PACKS.values():
        cats |= set(pack.CATEGORIES)
    return cats


def option_defaults():
    return {name: dict(pack.OPTIONS) for name, pack in PACKS.items() if pack.OPTIONS}


def option_choices():
    """{pack: {option: allowed values}} for options that take a fixed set."""
    return {name: dict(getattr(pack, "CHOICES", {})) for name, pack in PACKS.items()}


def _register():
    from . import pack_bcp14, pack_controlled, pack_plain, pack_review, pack_ux
    for pack in (pack_ux, pack_review, pack_plain, pack_bcp14, pack_controlled):
        PACKS[pack.NAME] = pack


_register()


def fingerprint_parts():
    """The strings that pin this layer: packs, their defaults, domain profiles."""
    from . import domains
    parts = ["RULES_EXT=" + SEMVER]
    for name in sorted(PACKS):
        parts.append("PACK|%s|%s" % (name, sorted(PACKS[name].OPTIONS.items())))
        parts.extend("PACK|%s|%s" % (name, p) for p in PACKS[name].fingerprint())
    parts.append("DOMAINS=" + json.dumps(domains.DOMAINS, sort_keys=True))
    return parts


def fingerprint():
    """sha256 over fingerprint_parts, in the form a receipt records."""
    digest = hashlib.sha256("\n".join(fingerprint_parts()).encode("utf-8")).hexdigest()
    return "sha256:" + digest[:16]
