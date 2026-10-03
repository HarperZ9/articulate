"""Domain profiles: a register profile plus rule packs for one kind of writing.

A domain profile starts from a register profile in articulate.profiles and
adds rule packs (articulate.rules_ext) that run after the detector. The
detector and the register profiles stay as published, so `normative-spec`
keeps its findings, and the RFC keyword rules run only under `rfc-keywords`.

  ux-microcopy        UI strings: length, case, vague errors, link text. Strict.
  code-review         review comments: condescension, absolutes, requests with
                      no reason. Flavored, so the pack reports and the banned
                      devices still gate.
  plain-language      reading grade, long sentences, wordy phrases. Strict.
  controlled-english  sentence length, one instruction per sentence, idioms,
                      phrasal verbs, vague pronouns. Strict. It claims no
                      conformance to ASD-STE100 or any other specification.
  rfc-keywords        the normative-spec register plus RFC 2119 and RFC 8174
                      keyword consistency.

`load_profile(name)` resolves a domain or register profile name, and `load`
also takes a writing mode (a name with a slash). Every place outside the
pinned detector files that resolves a profile name goes through here.
Standard library only.
"""
from . import modes, profiles

_SPEC_KEEP = ("must", "should", "may", "shall", "required", "recommended", "optional")
_REVIEW_KEEP = ("nit", "lgtm", "blocking", "non-blocking", "suggestion")

# name -> base profile, slop override, extra keep terms, register, rule packs.
DOMAINS = {
    "ux-microcopy": {"base": "flavored", "slop": "strict", "keep": (),
                     "register": ("interface", "user", "ui-string"),
                     "rule_packs": ("ux-microcopy",)},
    "code-review": {"base": "flavored", "slop": "flavored", "keep": _REVIEW_KEEP,
                    "register": ("engineering", "peer", "review-comment"),
                    "rule_packs": ("code-review",)},
    "plain-language": {"base": "flavored", "slop": "strict", "keep": (),
                       "register": ("public", "general-reader", "written"),
                       "rule_packs": ("plain-language",)},
    "controlled-english": {"base": "flavored", "slop": "strict", "keep": (),
                           "register": ("technical", "second-language", "written"),
                           "rule_packs": ("controlled-english",)},
    "rfc-keywords": {"base": "normative-spec", "slop": "flavored", "keep": (),
                     "register": None, "rule_packs": ("bcp14",)},
}


def names():
    return sorted(DOMAINS)


def _domain(name):
    spec = DOMAINS[name]
    out = profiles.load(spec["base"])
    out["slop"] = spec["slop"]
    out["keep"] = tuple(out.get("keep", ())) + tuple(spec["keep"])
    if spec["register"]:
        field, tenor, mode = spec["register"]
        out["register"] = {"field": field, "tenor": tenor, "mode": mode}
    out["rule_packs"] = tuple(spec["rule_packs"])
    out["domain"] = name
    return out


def load_profile(name):
    """A domain or register profile by name, as a fresh dict."""
    if name in DOMAINS:
        return _domain(name)
    try:
        return profiles.load(name)
    except profiles.ProfileError as exc:
        raise profiles.ProfileError("%s; domain profiles: %s" % (exc, ", ".join(names()))) from None


def load(name):
    """A writing mode (a name with a slash), domain profile or register profile."""
    return modes.load(name) if "/" in str(name) else load_profile(name)

