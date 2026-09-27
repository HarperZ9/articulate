# Fairness: the confirmatory run

This page reports the pre-registered confirmatory run of the fairness gates, on
a corpus the rules were not tuned on. The gates, their thresholds, the corpus,
the comparison and the ruleset were fixed in `fairness/PREREG.md` before the
run. Two RFC 3161 timestamps from a public time-stamping authority sign two
versions of that file: the first the confirmatory amendment, the second the
same file with the ruleset fingerprint the run measured
(`fairness/anchor/README.md`). A test compares every row of every table on this
page with the receipt it cites.

Receipts:

- confirmatory = `fairness/receipts/sha256-46e1485cd2c98caa-persuade-2.0.json`
- report = `fairness/reports/ellipse-sha256-46e1485cd2c98caa.json`

Ruleset `sha256:46e1485cd2c98caa`. Manifest
`sha256:8de8a1e6414e18f03730156ef6c4e8c87dc2f68fe73f0549d42cf4ea0788b4c3`.
The confirmatory receipt's SHA-256 is pinned in `fairness/receipts/SHA256SUMS`.

## The result

Verdict: the release gate fails on the confirmatory corpus.

88 of the 152 gate rows pass. A package release that ships this ruleset is
blocked. An override is refused too: it compares with the published ruleset's
own receipt from this manifest, none exists, and the PREREG amendment of 27
September 2026 rules out one made after this result was read.

- **G1 fails under 12 strict profiles.** They block 80 of 1,330 learner essays
  (6.0%) and 1,889 of 13,467 other essays (14.0%). Learner essays are blocked
  less often. The gap is -8.0 points [-9.3, -6.5], outside the 5-point line; G1
  reads a gap in either direction. Within holistic-score bands it is -3.8
  points, and within prompt-and-score cells -4.4; both lie inside the line.
  Every other bound profile passes G1.
- **G2 fails under 17 bound profiles.** Under the strict profiles 13 blocking
  rules fired. Read both ways, nine of them fail, all in the direction of the
  other essays (eight skewed, one inconclusive), and none toward the learner
  essays. Four of
  the eight skewed rules never fired on a learner essay, so their ratio has no
  estimable interval; the other four fail on their own.
- **G4 fails under 35 of the 38 bound profiles.** Between 31 and 504 essays per
  profile change their HIGH or MEDIUM findings or their word counts when
  rewrapped to one sentence per line or hard-wrapped. The three verse and
  screenplay profiles (`poetry`, `screenplay`, `screenplay/narrate`) are exempt.
- **G5 passes.** No cadence signal gates, so it is report only.
- **G7 opens a review.** The strict profiles block 14.0% [13.5, 14.6] of the
  other essays, above the 10% line. The review is recorded in
  `fairness/reviews/2026-09-27-g7-persuade.md`.
- **The default profile** (`flavored`) blocks none of the 14,797 essays, and
  neither do 20 other bound profiles.
- **G8, report only.** Under `flavored` 18 notes a writer sees by default fired
  here. One is skewed toward learner essays: the repeated-opener note
  (`anaphora`), on 49 learner and 244 other essays, ratio 2.29 [1.61, 3.08]. One
  is inconclusive: three hedges in one sentence, ratio 1.86 [1.64, 2.09]. That
  is one skewed reading among 61 notes read, with no correction for the number
  read. The two notes that left the blocking tier under
  [decision 2](../fairness/DECISIONS-PR9.md) of pull request 9 are not skewed toward learner essays: `padded-purpose` ("in order
  to") fires on 32 learner and 854 other essays, ratio 0.42, and
  `unanchored-claim` fired on 0 and 2 essays, too rare to test. The
  pre-registered condition for moving them to the house pack is not met.

## What was run

PERSUADE 2.0 (Crossley et al., 2024, Assessing Writing 61): argumentative essays
by US students in grades 6 to 12 on 15 prompts, released under CC BY-NC-SA 4.0.
The run reads the training file, pinned by its SHA-256 in the manifest. The
school-recorded English-learner field sorts the essays: 1,330 learner essays
(protected) and 13,467 other essays (reference). Essays with a blank field are
left out, as the PREREG says. The unit is the whole essay. Each essay carries
its prompt and its holistic score (1 to 6), so the gap is also read within score
bands and within prompt-and-score cells, with Cochran-Mantel-Haenszel weights.
Every bound profile is measured, and the house profiles are reported.

The harness scanned the essays in 20 processes (`--jobs 20`) and computed every
statistic in one. Before the run, the same command on every 20th essay wrote the
same receipt bytes from one process and from several, and from the harness at
the commit the second timestamp covers.

## How the run stayed confirmatory

The timestamps sign the bytes of `fairness/PREREG.md`. Through its text the
second fixes the manifest hash, the corpus hash, the thresholds, the seed and
the 64-bit ruleset fingerprint the run measured. They do not sign the harness
code; git history and the byte-identity proof above pin it. The pull request
was opened on 26 September at 18:38 UTC, before the confirmatory amendment, so
it anchors only the original gate table.

What touched the corpus before the receipt run, in UTC (the PREREG amendment of
27 September 2026 records the same list):

| When | What | What was seen |
|:-|:-|:-|
| 26 Sep, 22:25 | Value counts of the non-text columns, with essays counted by prompt and learner status | Counts only |
| 26 Sep, 22:25 | A timing probe on 20 essays, before the confirmatory amendment was committed | Mean word count and seconds per essay |
| 26 Sep, 22:33 | First timestamp, over the confirmatory amendment | |
| 26 Sep, 22:34 | A run under the earlier ruleset `sha256:1c8f54b02d8aa211`, stopped before it wrote a receipt | Nothing: the harness prints only at the end |
| 27 Sep, 03:28 | Second timestamp, over the extended PREREG with the ruleset fingerprint | |
| 27 Sep, 03:28 to about 07:21 | A first attempt at this run, stopped before it wrote a receipt | Mean word count and seconds per essay on 20 essays |
| 27 Sep, 04:14 to 04:18 | The report-only ELLIPSE receipt was read | Block counts by proficiency band, which include 449 of these learner essays |
| 27 Sep, 08:14 to 09:45 | The receipt run | The receipt |
| 27 Sep, 11:18 | Third timestamp, over the PREREG with the amendment of 27 September, and a timestamp over the receipt's bytes | |

Two harness commits landed after the second timestamp: one lets a table set
select rows by a list of values, and one adds `--jobs`. Neither touches a rule,
a threshold, the corpus, the sampling or a seed, and the byte-identity proof
covers both. No rule changed between the second timestamp and the run. The run's
own time rests on the commit that adds the receipt, which its author can set.
The timestamp over the receipt's bytes shows the receipt existed by 11:18 UTC
on 27 September; it does not show when the run started.

## Block rates

An essay is blocked when the profile's gate says `blocked`. Counts are essays.

| Profile | Learner essays | Other essays |
|:-|:-|:-|
| essay | 80 of 1330 | 1889 of 13467 |
| academic/argue | 5 of 1330 | 186 of 13467 |
| marketing/explain | 5 of 1330 | 153 of 13467 |
| flavored | 0 of 1330 | 0 of 13467 |
| research | 0 of 1330 | 0 of 13467 |
| house | 759 of 1330 | 8591 of 13467 |
| house-essay | 965 of 1330 | 10615 of 13467 |

Profiles that block the same essays as a row above:

- `essay`: `commit`, `journalism/explain`, `legal/argue`, `marketing/persuade`,
  `memo/argue`, `memo/explain`, `memo/instruct`, `persuasive-essay/argue`,
  `persuasive-essay/persuade`, `technical-docs/instruct`, `tutorial/instruct`.
- `academic/argue`: `legal/explain`, `technical-docs/argue`.
- `marketing/explain`: `marketing/narrate`.
- `flavored` and `research`, which block nothing: `academic/explain`,
  `academic/prove`, `changelog`, `journalism/narrate`, `legal`,
  `legal/instruct`, `memoir`, `model-card`, `narrative`, `normative-spec`,
  `poetry`, `proof`, `readme`, `release-notes`, `science-writing/explain`,
  `screenplay`, `screenplay/narrate`, `technical-docs/explain`,
  `tutorial/explain`.

`house` and `house-essay` are chosen by a writer or a project, never assigned by
a path, and never gate a release.

## Gaps between groups

Learner block rate minus other block rate, in points, with a 95% Newcombe
interval. A negative gap means learner essays were blocked less often. The G1
line is 5 points either way, for the raw gap and for both within-group readings;
with both arms over 500 essays, both limits of the raw interval must also lie
within 10 points.

| Profile | Raw gap | 95% interval | Within score bands | Within prompt and score cells |
|:-|:-|:-|:-|:-|
| essay | -8.0 | [-9.3, -6.5] | -3.8 | -4.4 |
| academic/argue | -1.0 | [-1.3, -0.5] | -0.6 | -0.8 |
| marketing/explain | -0.8 | [-1.0, -0.2] | -0.5 | -0.3 |
| flavored | 0.0 | [0.0, 0.3] | 0.0 | 0.0 |
| research | 0.0 | [0.0, 0.3] | 0.0 | 0.0 |
| house | -6.7 | [-9.5, -4.0] | -0.9 | 0.0 |
| house-essay | -6.3 | [-8.8, -3.8] | 0.5 | -1.2 |

The receipt also stores an interval for each within-group gap: [-5.1, -2.3]
within bands and [-5.7, -2.9] within cells under `essay`. Each is approximate:
it takes the raw interval's width and centres it on the stratified gap, so it is
not an interval for the stratified gap itself. G1 gates on the within-group
point estimates only.

## Rules that fail G2

A matched comparison reads each blocking rule both ways. A rule fails when it is
skewed or inconclusive in either direction. Counts are essays on which the rule
fired; the ratio compares rates per 1,000 words.

| Rule | Learner essays | Other essays | Ratio toward | Ratio | 95% interval | State | Bound profiles |
|:-|:-|:-|:-|:-|:-|:-|:-|
| `MEDIUM\|closing-boilerplate/boilerplate-helpful-closer` | 0 | 5 | other | inf | not estimable | skewed | 12 |
| `MEDIUM\|hedge-stack/stacked-hedge` | 22 | 478 | other | 1.81 | [1.2, 3.12] | inconclusive | 12 |
| `MEDIUM\|idiom-cliche/idiom-set-phrase-cliche` | 0 | 18 | other | inf | not estimable | skewed | 12 |
| `MEDIUM\|marketing/marketing-superlative` | 5 | 153 | other | 2.91 | [1.42, 14.24] | skewed | 14 |
| `MEDIUM\|meta/back-reference-as-we-ve-seen-as-mentioned-earlie` | 0 | 51 | other | inf | not estimable | skewed | 12 |
| `MEDIUM\|meta/section-framing-imperative-let-s-break-it-down` | 0 | 9 | other | inf | not estimable | skewed | 12 |
| `MEDIUM\|throat-clearing/throat-clearing-opener` | 27 | 634 | other | 2.37 | [1.69, 3.72] | skewed | 12 |
| `MEDIUM\|unsupported-authority/authority-appeal-no-citation-in-the-sentence` | 5 | 186 | other | 2.11 | [1.04, 8.85] | skewed | 15 |
| `MEDIUM\|wordiness/deletable-padding-circumlocution` | 5 | 286 | other | 5.64 | [2.82, 27.19] | skewed | 12 |

"Bound profiles" counts the bound profiles under which the row fails.

"Not estimable": the rule never fired on a learner essay, so every bootstrap
resample gives an infinite ratio and the percentile interval collapses to
`[inf, inf]`. The pre-registered G2 rule reads such a row as skewed, and that
reading stands. Read post hoc: learner essays hold 7.8% of the words, and if the
rule's hits fell on the two arms in proportion to words, the chance of no
learner hit is about 0.61 for the helpful closer (6 hits), 0.38 for the
section-framing imperative (12), 0.25 for the set-phrase cliche (17) and 0.015
for the back-reference (52). The G2 verdict does not rest on these four rows.

The arms also differ in topic: 63.5% of learner essays answer three prompts,
against 19.8% of the other essays. G1 has a within-prompt reading and G2 does
not, so a rule that tracks a topic can read as a group difference here.

## Layout check (G4)

G4 asks that an essay's HIGH and MEDIUM findings, its density count and its
word count stay the same when it is rewrapped to one sentence per line or
hard-wrapped at 60 columns. Under `essay`, 31 of the 14,797 essays change; under
`memoir`, 504. The receipt counts essays and does not say which ones or why.

The same check failed in the report-only ELLIPSE run, which predates this one:
12 essays under `essay`.

## Report-only notes (G8)

Notes never block. G8 reads each one by the G2 rule toward the learner essays
only, where G2 reads a matched pair both ways, and records whether a writer sees
it by default. The table shows the notes named above. The receipt holds 76 keys
under `flavored`: 61 distinct notes, because two notes put a count in their rule
id (12 keys for paragraph uniformity, 5 for nominalization), which splits each
note's reading across keys.

| Profile | Note | Learner essays | Other essays | Ratio | State | Shown by default |
|:-|:-|:-|:-|:-|:-|:-|
| flavored | `LOW\|anaphora` | 49 | 244 | 2.29 | skewed | yes |
| flavored | `LOW\|hedge-cluster/3-hedges-in-one-sentence` | 298 | 1937 | 1.86 | inconclusive | yes |
| flavored | `LOW\|padded-purpose/padded-purpose-in-order-to` | 32 | 854 | 0.42 | not skewed | yes |
| flavored | `LOW\|unanchored-claim/unanchored-claim-state-of-the-art-no-comparison-` | 0 | 2 | 0.0 | not skewed | yes |
| flavored | `LOW\|expletive-opener/empty-opener-it-is-important-worth` | 18 | 262 | 0.75 | not skewed | yes |
| flavored | `LOW\|announcement/announces-what-the-text-will-do-in-this-essay-we` | 0 | 4 | 0.0 | not skewed | yes |

Under the principle of
[decision 3](../fairness/DECISIONS-PR9.md) on pull request 9, a note that measures as
skewed and carries no reliable reader cost belongs in the house pack, so
`anaphora` is a candidate. Moving it changes the ruleset, which now waits for a
corpus pre-registered for the next ruleset; this reading is exploratory for
that decision.

## Proficiency bands (ELLIPSE, report only)

ELLIPSE (Crossley et al., 2023) holds essays by English learners in grades 8 to
12, scored for overall proficiency. It never gates a release. Counts are essays
blocked in each band of the overall score.

| Profile | Overall 1.0 to 2.5 | Overall 3.0 to 3.5 | Overall 4.0 to 5.0 |
|:-|:-|:-|:-|
| essay | 37 of 1062 | 151 of 2170 | 99 of 679 |
| academic/argue | 2 of 1062 | 12 of 2170 | 6 of 679 |
| marketing/explain | 8 of 1062 | 18 of 2170 | 11 of 679 |
| flavored | 0 of 1062 | 0 of 2170 | 0 of 679 |
| house | 479 of 1062 | 1273 of 2170 | 466 of 679 |
| house-essay | 649 of 1062 | 1674 of 2170 | 595 of 679 |

Under the strict profiles, with 95% Wilson intervals:

| Band | Block rate (%) | 95% interval |
|:-|:-|:-|
| Overall 1.0 to 2.5 | 3.5 | [2.5, 4.8] |
| Overall 3.0 to 3.5 | 7.0 | [6.0, 8.1] |
| Overall 4.0 to 5.0 | 14.6 | [12.1, 17.4] |

The rate rises with proficiency. No trend test was run. Three limits sit
beside that reading. The band cut points were chosen after the second
timestamp, from the distribution of overall scores, before any block count was
seen. 449 of the 1,330 PERSUADE learner essays are also in ELLIPSE, so this is
not independent support for the confirmatory learner arm. And this receipt was
read before the confirmatory run (see the table above).

## How small a gap this run can see

The excess learner block rate whose 95% Newcombe interval would just exclude
zero, holding the other arm at its observed count. A true gap of this size is
detected about half the time:

| Profile | Gap seen about half the time (points) |
|:-|:-|
| essay | 2.0 |
| academic/argue | 0.7 |
| marketing/explain | 0.7 |
| flavored | 0.1 |
| research | 0.1 |
| house | 2.7 |
| house-essay | 2.3 |

Detecting a gap 80% of the time takes about 3.0 points under the strict
profiles, 1.1 under `academic/argue`, 1.0 under `marketing/explain`, 0.2 under
the profiles that block nothing, and 4.0 and 3.2 under the two house profiles
(simulated post hoc from the arm sizes and the other arm's rate).

Which gaps a row rules out is read from its own interval. Under the strict
profiles, [-9.3, -6.5] rules out every learner-directed gap. Under `flavored`,
[0.0, 0.3] leaves learner-directed gaps up to 0.3 points open.

## What these numbers do not show

- They show how these rules behave on these essays. They do not show who or what
  wrote any essay, or that any group trait causes a gap.
- The learner field is a school record. It does not name a writer's first
  language. The writers are school students in grades 6 to 12 on one kind of
  task; no adult academic writer is in this corpus.
- The gap shrinks within score bands, from -8.0 to -3.8 points under `essay`,
  and the ELLIPSE bands show the strict profiles blocking more as proficiency
  rises. That fits an account in which proficiency drives part of the gap. It
  does not prove one, and ELLIPSE shares a third of the learner essays.
- The arms differ in topic, and G2 has no within-prompt reading.
- Per-rule readings are many (13 blocking rules both ways under each bound
  profile, 61 notes under G8) and uncorrected. The gate errs toward failing,
  since an inconclusive rule fails. A single skewed note is a lead for review.
- G6, editor behavior by group, needs a model run and was not run.

## Rerun it

Get the training file named in `fairness/manifests/persuade-2.0.json` and put it
in a folder of your choice. Then run:

```
python -m articulate.fairness fairness/manifests/persuade-2.0.json --root FOLDER --out RECEIPT --jobs 8
python -m articulate.fairness --release-check fairness/receipts
```

The harness refuses a file whose SHA-256 differs from the manifest. `--jobs`
changes only how many processes scan the essays; the receipt is the same. The
release check recomputes the gate summary from the committed receipts, checks
each stored flag against its stored numbers and each receipt against its pin,
and trusts the stored per-rule states and layout counts.
