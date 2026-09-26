# Fairness gates: pre-registration

This file fixes the gates the fairness harness applies before a ruleset release.
The harness is `python -m articulate.fairness`. Its code lives in
`src/articulate/fairness.py`, `fairness_gates.py`, `fairness_stats.py` and
`fairness_corpora.py`.

## Status and honest limits

- Written 26 September 2026. A git commit date can be set by whoever makes the
  commit, so the repository alone does not prove when this file was written.
  The file as it stands with the confirmatory amendment below carries an RFC
  3161 timestamp from a public time-stamping authority (FreeTSA) over its
  SHA-256. `fairness/anchor/README.md` holds the token and the command that
  verifies it. The pull request's creation time on GitHub is a second, weaker
  anchor.
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
for that exact ruleset with a reason (see the amendment below). (Amended 26
September 2026: the block covers only a release that changes the ruleset, and an
override must show that no gate row regressed; see the last amendment below.) A
failure never blocks a user's run. House profiles are measured and published and never block a
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

### Amendment of 26 September 2026: the harness review

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

### Amendment of 26 September 2026: the release block and two tier changes

Dated 26 September 2026, after the commits that carry out the decisions on
pull request 9 and after the rerun on the Liang et al. corpus. Unlike the
amendments above, the first item loosens something: it narrows the release
block to ruleset changes. Every gate definition and threshold stays as the
table and the machine-readable blocks state them.

- The release block covers ruleset changes only. `fairness/published-ruleset.json`
  names the fingerprint of the last published ruleset and its receipts; the
  release commit updates it. A package release whose fingerprint equals it is
  not gated, and the check prints "ruleset unchanged since X; gates not re-run".
  Why: nothing the gates measure has changed, and blocking such a release would
  hold back a security fix while the same rules stay live.
- A changed ruleset must pass every gate on every required receipt: one from
  each manifest in the release-requirements block. Today that is the Liang et
  al. receipt, which is exploratory because the gates were tuned on it.
- An override for one exact ruleset excuses failing gates only when no gate row
  that passes under the published ruleset's receipt fails under the new one. A
  gate row is one gate under one bound profile, and for G1, G2 and G5 one
  comparison. The check prints the comparison next to the reason. It refuses an
  override with no published receipt to compare with, and an override never
  excuses a malformed receipt. This part is stricter than the override it
  replaces, which excused any failure.
- Two phrases leave the blocking tier in every profile, on reader-cost grounds.
  "in order to" moves from `wordiness` (MEDIUM) to a LOW note, `padded-purpose`:
  usually "to" does the same work, and usage guides keep it where it separates a
  purpose from a complement. "state of the art" moves from `marketing` (MEDIUM)
  to a LOW note, `unanchored-claim`, that fires only when its sentence carries no
  number, year or citation marker: in research writing the phrase names the best
  published result on a named benchmark, so "claims a comparison the text never
  makes" does not hold there.
- Two report-only notes move to the house pack, which a writer sees only on
  request. Curly quotation marks are typographically correct and inserted by word
  processors and phone keyboards, so the note carries no reader cost. Bare "there
  is / are / was / were" is grammatical and often the clearest phrasing. "It is
  important / worth / crucial / essential / necessary" at a sentence start stays
  a default LOW note: it is metadiscourse that delays the subject. Neither half
  ever blocks.
- On the Liang et al. corpus these tier changes are exploratory. They were made
  after reading it: under `essay`, 16 of the 19 blocked abstract windows were
  blocked by the two phrases alone or together. A pass there does not confirm
  them. Confirmation needs a corpus the rules were not tuned on.
- A receipt keys the n-gram repetition and anaphora rules by category, because
  their labels quote the text. This changes no gate.

### Amendment of 26 September 2026: the confirmatory corpus

Dated 26 September 2026, before any run on the corpus it names. It adds a
corpus the rules were not tuned on, a stricter reading of G1 for documents that
name a prompt, and a second required receipt. No threshold changes.

- Corpus. PERSUADE 2.0 (Crossley et al., 2024, Assessing Writing 61):
  argumentative essays by US students in grades 6 to 12 on 15 prompts, under
  CC BY-NC-SA 4.0. The run uses the training file,
  `persuade_corpus_2.0_train.csv`, 616,894,963 bytes, SHA-256
  `f61319edd8bf16a982711ea0399fad59c05afaec05cdf0767f16a2c05c467e23`, downloaded
  on 26 September 2026 from the link in the corpus repository's README. The
  test split is distributed as an encrypted archive and is not used.
- What was read before this amendment: the file's header and the value counts
  of its non-text columns, and nothing else. The file holds 15,594 essays. The
  school-recorded English-learner field (`ell_status`) reads Yes for 1,330, No
  for 13,467 and blank for 797; every essay on one prompt ("Phones and driving",
  701 essays) is blank. Blank essays are left out. The prompt field
  (`prompt_name`) and the holistic score (`holistic_essay_score`, 1 to 6) are
  present on every essay.
- Manifest. `fairness/manifests/persuade-2.0.json`, SHA-256
  `8de8a1e6414e18f03730156ef6c4e8c87dc2f68fe73f0549d42cf4ea0788b4c3`. It lists no
  document rows. It pins the file's hash and names the id, text, prompt and
  score columns and the values that select each set. The file stays outside the
  repository; the harness reads it with `--root`.
- Comparison. `persuade-ell-vs-non-ell`, design matched: essays whose writer the
  school records as an English learner (protected) against essays whose writer
  it records as not one (reference). The unit is the whole essay, with no
  window. Every bound profile is measured, and the house profiles are reported.
- G1 on this comparison: the raw gap, the gap within holistic-score bands and
  the gap within prompt-and-score cells (Cochran-Mantel-Haenszel weights over
  cells that hold both arms) each lie within plus or minus 5.0 points. Both arms
  hold more than 500 essays, so both 95% limits of the raw gap must also lie
  within plus or minus 10.0 points. The prompt-and-score reading applies to any
  comparison whose documents name a prompt; the Liang et al. documents name
  none, so it changes nothing there.
- G2 is read both ways, as for every matched pair. G4, G5 and G7 apply as the
  table states. G8 is reported for the default and house profiles.
- Release requirement. A changed ruleset needs a passing receipt from both
  manifests in the block below. The Liang et al. receipt stays exploratory.
- When the result counts. The receipt counts as confirmatory only if the commit
  that holds this amendment and the RFC 3161 token over this file both predate
  the run. The run's own time rests on the commit that adds its receipt, which
  its author can set. The order therefore rests on the token for this file and
  on the public history of the pull request.
- The decision it serves: whether a changed ruleset ships. A failing gate blocks a
  release that changes the ruleset. Decision 2 on pull request 9 names one more
  outcome: if G8 shows the two new LOW notes skewed toward learner essays, they
  move to the house pack.
- Limits. The learner field is a school record and does not name a writer's
  first language. The writers are school students in grades 6 to 12, and no
  adult academic writer is in this corpus. Learner status can track writing
  proficiency, so the raw gap can mix the two; the banded and matched readings
  address that and cannot remove it.

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

A test checks that this block equals `fairness_release.REQUIREMENTS`. The first
manifest is the Liang et al. (2023) v1.0.0 build; the second is
`fairness/manifests/persuade-2.0.json` (amended 26 September 2026, see the
confirmatory corpus above).

```json
{
  "manifests": [
    "sha256:71ab34e241bd4315f81d4f0fefcd47eb4538c918b9584cebbca1ca848b73404a",
    "sha256:8de8a1e6414e18f03730156ef6c4e8c87dc2f68fe73f0549d42cf4ea0788b4c3"
  ],
  "comparisons": {
    "sha256:71ab34e241bd4315f81d4f0fefcd47eb4538c918b9584cebbca1ca848b73404a":
      ["toefl-vs-abstracts", "toefl-vs-college"],
    "sha256:8de8a1e6414e18f03730156ef6c4e8c87dc2f68fe73f0549d42cf4ea0788b4c3":
      ["persuade-ell-vs-non-ell"]
  }
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
