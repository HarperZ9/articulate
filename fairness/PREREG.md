# Fairness gates: pre-registration

This file fixes the gates the fairness harness applies before a ruleset release.
The harness is `python -m articulate.fairness`. Its code lives in
`src/articulate/fairness.py`, `fairness_gates.py`, `fairness_stats.py` and
`fairness_corpora.py`.

## Status and honest limits

- Written 26 September 2026. It is not yet anchored anywhere outside this
  repository. A git commit date can be set by whoever makes the commit, so this
  file alone does not prove when it was written. An outside anchor (a pull
  request's creation time, an RFC 3161 token or a Zenodo deposit) is pending a
  maintainer decision.
- The thresholds below were chosen after an exploratory audit had already read
  the Liang et al. (2023) release. On that corpus these gates are therefore not
  pre-registered. They bind every licensed corpus added after this file lands.
- The corpora run so far are proxies: learner exam scripts against US college
  admission essays and student project abstracts. No arm groups adult academic
  writers by first language, and none covers dictated text, disabled writers or
  World Englishes yet.

## What the harness measures

For every profile and mode a writer can land on without choosing it (the
default, every path rule target, every mode that can gate), and separately for
the house profiles a project opts into:

- the share of documents the profile blocks, per group, with Wilson intervals;
- the difference between the protected and the reference group, both
  directions, with Newcombe intervals, raw and within human-score bands where the
  corpus has scores;
- per-rule counts and rates per 1,000 words, and a skew state per rule;
- the density of blocking findings per document;
- whether any document changes its blocking findings when it is rewrapped to one
  sentence per line.

## Gates

A failure blocks a release. Every package release ships the ruleset, so while a
gate fails no package release publishes unless a maintainer records an override
for that exact ruleset with a reason (see the amendment below). A failure never
blocks a user's run. House profiles are measured and published and never block a
release.

| Gate | Rule |
|:-|:-|
| G1 | For each comparison under each bound profile, the block-rate difference lies within plus or minus 5.0 points, raw and within score bands. When both groups hold 500 or more documents, both 95% limits must also lie within plus or minus 10.0 points. The median density difference is reported with a bootstrap interval. |
| G2 | For each rule that blocks under the profile, a skew state. Skewed: at least 5 documents in the higher group, a pooled per-1,000-word ratio of 2 or more and a bootstrap lower limit above 1. Not skewed: a bootstrap upper limit below 2. Bounded: neither, and the rule fires on at most 2% of documents in every arm. Inconclusive: anything else. Skewed or inconclusive fails. Proxy pairs are read in the protected direction; matched-prompt pairs both ways. |
| G3 | Paired rewrites (a text before and after a model rewrite). Reported, never a gate: it concerns origin. |
| G4 | Blocking findings and density inputs are identical after a rewrap to one sentence per line. Verse (line unit) and screenplay profiles are exempt. |
| G5 | While any cadence signal blocks or is a required fix: the protected group's uniform-cadence rate is at most twice the reference rate, or the difference's upper limit is at most 5.0 points. Report only when no cadence signal gates. |
| G6 | Editor behavior by group (rewrite rate, edit distance, guard rejections, vocabulary lift, sentence-length variance). Reported when a model run exists. Not run so far. |
| G7 | The absolute default-profile block rate on every human arm. Above 10% opens a review. (Amended 26 September 2026: every bound profile, see below.) |
| G8 | Report only. For the default and house profiles, each LOW-tier rule's skew state by the G2 rule, and whether a writer sees it by default. Added 26 September 2026. |

## Amendments

Dated 26 September 2026, after a review of the harness and before any new
corpus. Each one makes a gate stricter or adds a report; none loosens one.

- G1 and G2 fail when a comparison has an empty arm or a bound profile has no
  evaluated comparison. They passed vacuously before.
- G7 applies to every bound profile, not only the default. The code did this
  from the start and the table above said otherwise; the stricter reading
  stays.
- G4 also hard-wraps each text at 60 columns, breaking at hyphens, as well as
  rewrapping it to one sentence per line.
- G8 is added, report only.
- The release check recomputes the gates from the receipt's own rows, and it
  accepts only a receipt from a listed manifest that holds every required
  comparison (the block below). An override file for one exact ruleset, with a
  reason and who decided, lets a release publish while a gate fails; the check
  prints the reason. No override exists.
- The smallest detectable gap is found by searching the Newcombe interval with
  the reference arm held at its observed count. The earlier normal
  approximation overstated power near a zero rate.

## Statistics

Wilson intervals for a proportion; Newcombe hybrid-score intervals for a
difference; a Cochran-Mantel-Haenszel weighted difference over score bands;
percentile bootstraps with 2,000 resamples and seed 20260925, drawing each index
as `int(rng.random() * n)` because Python guarantees only `random()` across
versions; exact McNemar for paired rewrites; exact Poisson intervals for counts.

## Thresholds, machine-readable

A test checks that this block equals `fairness_gates.THRESHOLDS`.

```json
{
  "g1_point": 0.05,
  "g1_ci": 0.10,
  "g1_ci_min_n": 500,
  "g2_min_docs": 5,
  "g2_ratio": 2.0,
  "g2_bounded_share": 0.02,
  "g5_ratio": 2.0,
  "g5_diff_hi": 0.05,
  "g7_review": 0.10
}
```

## Release requirements, machine-readable

A test checks that this block equals `fairness_release.RELEASE_MANIFESTS` and
`REQUIRED_COMPARISONS`. The manifest is the Liang et al. (2023) v1.0.0 build.

```json
{
  "manifests": ["sha256:71ab34e241bd4315f81d4f0fefcd47eb4538c918b9584cebbca1ca848b73404a"],
  "comparisons": ["toefl-vs-abstracts", "toefl-vs-college"]
}
```

## What a passing receipt does not show

It shows how these rules behave on these corpora. It says nothing about who or
what wrote any text, nothing about any group trait as a cause of a difference,
and nothing about groups, genres or profiles it does not list. At the sizes run
so far a 95% interval spans from about 4 to about 14 points either side of its
estimate, so a small gap in either direction cannot be ruled out. Against the
70 college windows, the default profile could tell a gap from zero only at 6.6
points or more, above the 5-point G1 line.
