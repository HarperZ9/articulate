"""Shared helper for the control-line tests.

A control line is an invented sentence that stands for one convention a rule
must leave alone, or one pattern it must keep reporting. Each comes from the
rule-proposals file of the six-lane domain review, where every line was run
through the documented CLI before the change. These helpers run a line the way
`articulate check FILE --json [--profile P | --mode M]` does: house notes off.
"""
from articulate import check_text, modes, profiles


def run(text, run_id, name="doc.md"):
    """Check `text` under a run id: a mode when the id holds a slash, else a
    profile. `name` stands in for the file path; the run id always wins."""
    prof = modes.load(run_id) if "/" in run_id else profiles.resolve(
        path=name, text=text, override=run_id)
    return check_text(text, profile=prof, house_notes=False)


def cats(r, tier):
    return [f["category"] for f in r[tier.lower()]]


def blocking(r):
    return sorted((f["tier"], f["category"]) for t in ("high", "medium", "low")
                  for f in r[t] if f["gates"])


def assert_passes(text, runs, name="doc.md"):
    """No run blocks the line."""
    for run_id in runs:
        r = run(text, run_id, name)
        assert r["gate"] == "ok", (run_id, blocking(r))


def high_medium(r):
    return sorted((f["tier"], f["category"]) for t in ("high", "medium") for f in r[t])
