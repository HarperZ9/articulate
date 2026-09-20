# Changelog

All notable changes to `articulate-writing` are recorded here. The package uses
semantic versioning. This is the package version. The detector ruleset carries its
own `RULESET_SEMVER`, which a receipt records so a replay knows which rules ran.

## 0.3.0

Added three cadence detectors for prose that reads clean under the earlier ruleset
yet still carries a machine rhythm a reader hears.

- Demonstrative summary-beat, "That is the ... half / side / piece / layer / angle
  / story / trick". Tier MEDIUM, so it gates under a strict profile. A compound noun
  like "That is the side effect" and a plain "That is the file" do not fire.
- Two-imperative parallel slogan, "Verb the X, verb the Y." Tier LOW and advisory,
  since an everyday instruction is often an imperative pair. It anchors to a full
  line of two comma-joined bare-verb clauses, and a determiner or pronoun opener
  blocks it.
- Evaluative fragment opener, "Strong foundation." Tier LOW and advisory,
  paragraph-initial only, and fragment-shaped so a full sentence does not match.

Detector internals:

- Ruleset semver moves 0.4.0 to 0.5.0, and `FRAGMENT_OPENER` folds into the ruleset
  fingerprint, so a replay against an older receipt reports the ruleset change
  explicitly.
- A verse genre suppresses the two new LOW categories.
- Every new pattern uses bounded quantifiers and stays covered by the ReDoS safety
  test.
- The demonstrative extension fires on none of a 26-snippet human control corpus.

Tests: 151 pass.

## 0.2.0

Detector expanded to the full device catalogue. It reached 18 HIGH, 55 MEDIUM, and
12 LOW tells, plus 7 standard-library statistical advisories. The tells cover
lexical and structural devices, cadence, delivery, and formatting.
False-positive-controlled against a 22-snippet human corpus with zero false HIGH or
MEDIUM. Ruleset semver 0.4.0. Tests: 143 pass. Published to PyPI as
`articulate-writing`.

## 0.1.0

First public release. The core detector, register profiles, writing modes, the
genre axis, per-span mixed-authorship verdicts, an "unverifiable" sub-threshold
calibration, binary fail-closed input guards, the benchmark, the editor layer, the
CLI, the LSP and SARIF surfaces, receipts, the content-free audit receipt, and the
MCP server. The core runs standard-library-only with no network call.
Source-available under FSL-1.1-MIT. Published to PyPI as `articulate-writing`.
