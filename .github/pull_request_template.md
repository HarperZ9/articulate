## What changed

## Checks

- [ ] `python -m pytest -q` and `ruff check .` pass.
- [ ] If a rule, profile, mode or scanner constant changed: the golden pin is
      regenerated on purpose, and a fairness receipt for the new fingerprint is
      committed under `fairness/receipts/` (`python -m articulate.fairness`).
- [ ] Any new rule that can block outside the house pack has a reader-cost
      reason and a source in `rule_reasons.py`, and a person other than the
      author has read that reason.

## Read every new output string

The origin-claim test catches a fixed word list and misses paraphrase. Read each
new or changed string a user sees (CLI help and output, JSON keys, SARIF text,
MCP descriptions, editor prompts, desk and disclosure templates) against
`docs/boundaries.md`. No output may read as a claim about who or what wrote a
text, as a score or a ranking of a person, or as a way past a detector.
