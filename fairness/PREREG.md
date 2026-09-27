# Fairness gates: pre-registration

This file fixes the gates the fairness harness applies before a ruleset release.
The harness is `python -m articulate.fairness`. Its code lives in
`src/articulate/fairness.py`, `fairness_gates.py`, `fairness_stats.py` and
`fairness_corpora.py`.

## Status and honest limits

- Written 26 September 2026. A git commit date can be set by whoever makes the
  commit, so the repository alone does not prove when this file was written.
  The file as it stood with the confirmatory amendment below (commit 5a30364)
  carries an RFC 3161 timestamp from a public time-stamping authority (FreeTSA)
  over its SHA-256. A later extension of the tier-change amendment says so where
  it starts, and that token does not cover it. A second FreeTSA token, taken
  after that extension and before any run on PERSUADE 2.0, covers the file as it
  stands at the commit that adds `fairness/anchor/PREREG-2.tsr`, including the
  ruleset fingerprint the confirmatory run measures. `fairness/anchor/README.md`
  holds both tokens and the commands that verify them. The pull request's
  creation time on GitHub is a further, weaker anchor.
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

Extended later on 26 September 2026, after the RFC 3161 token over this file
and before any run on the PERSUADE 2.0 corpus. A review of six writing domains
(students and second-language writers, STEM, humanities and law, publishers and
editors, graders, professional writers) found conventions the rules blocked.
Each change below was judged on reader cost under the blocking-tier principle of
the pull request 9 decisions, and none was adopted for its effect on a gate. All
were made after reading the Liang et al. corpus, so on that corpus they are
exploratory, like the two tier changes above.

- Quotations are masked. Every phrasing rule reads a text with its direct
  quotations (double and curly quotes, LaTeX ``...''), Markdown block quotes and
  LaTeX `quote` and `quotation` environments blanked. The first-person
  self-description rule also skips table rows, transcript turns, `verbatim`
  environments and `\texttt{}` or `\verb` spans. An interface markup token and a
  hidden character still read every character (`SCAN_ALGO` 6).
- `unsupported-authority` stays MEDIUM and reads a citation marker anywhere in
  its sentence, in every common style, and the writer's own data beside a
  figure, table or test statistic. A year counts only in citation position, so a
  four-digit count no longer silences it. Citation abbreviations ("ref.", "p.",
  "v.", "Cir.", "U.S.") no longer end a sentence.
- "It is important / worth / crucial / essential / necessary / vital to" and "It
  is worth noting that" leave the MEDIUM throat-clearing and worth-noting rules.
  The LOW `expletive-opener` note alone reports them, at a sentence start or
  after one leading clause. "It should be noted that" stays MEDIUM.
- The self-reference rule leaves MEDIUM `meta` for a LOW `announcement` note that
  fires only on announcement verbs. "With respect to" leaves MEDIUM `wordiness`
  for a LOW `padded-preposition` note, silent in its operator sense.
- Every report-only note gains a reader-cost reason. The fingerprint hashes the
  reason keys, so this moves it and changes no finding.
- Rerun on the Liang et al. corpus under ruleset `sha256:46e1485cd2c98caa`
  (receipt `fairness/receipts/sha256-46e1485cd2c98caa.json`): all 266 gate rows
  pass, as they did under `sha256:1c8f54b02d8aa211`, and no row changes state.
  The bound profiles block the same texts. Report-only rows move: under the
  house profiles one college window (`house`) and two (`house-essay`) no longer
  block, and G8 gains the `announcement` note (0 learner texts, 4 abstract
  windows, not skewed).
- Unchanged: every gate definition and threshold, the release requirements and
  the set of bound profiles. The `essays/`, `blog/` and `writing/` path rule stays
  for this release, so the profile set the confirmatory run measures is the one
  the amendment below names. A changed ruleset ships only after it passes on
  every listed corpus. The PERSUADE 2.0 receipt names the fingerprint it ran
  under; at this writing that is `sha256:46e1485cd2c98caa`.
- The first RFC 3161 token signs the file as it stood at commit 5a30364 and
  does not cover this extension. The second token (`PREREG-2.tsr`) signs the
  file with this extension, before the confirmatory run
  (`fairness/anchor/README.md`).

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

### Amendment of 27 September 2026: after the confirmatory run

Dated 27 September 2026, after the PERSUADE 2.0 receipt for ruleset
`sha256:46e1485cd2c98caa` was committed and read. The release gate fails on that
corpus, and nothing here changes that result. No gate definition, threshold,
corpus, sampling rule or seed changes. The items correct the record, tighten the
release check, and set how a later ruleset gets a confirmatory reading. The text
above stays as it was timestamped; where this amendment corrects it, this
amendment holds.

Corrections to the record. The status section says the second token came
"before any run on PERSUADE 2.0", and the confirmatory amendment says the file's
header and value counts were read "and nothing else". No gate result, block
count or finding count on PERSUADE 2.0 existed before the receipt run, and the
ruleset changes made after the first token used no PERSUADE output. Five
contacts with the corpus were left out of that account (times UTC):

- 26 September, 22:25: the value counts included a count of essays by prompt
  and English-learner status.
- 26 September, 22:25, before the commit that holds the confirmatory amendment:
  a timing probe measured 20 essays under every configuration and printed only
  their mean word count (415.25) and the seconds per essay (0.42).
- 26 September, 22:34, after the first token: a harness run under the earlier
  ruleset `sha256:1c8f54b02d8aa211` started and was stopped before it wrote a
  receipt. The harness prints and writes only at the end, so none of its
  results was seen.
- 27 September, 03:28 to about 07:21, after the second token: a first attempt
  at the receipt run timed 20 essays (mean words and seconds only) and stopped
  before it wrote a receipt. The receipt run started at 08:14.
- 27 September, 04:14 to 04:18: the report-only ELLIPSE receipt was read before
  the receipt run. 449 of the 1,330 PERSUADE learner essays share an id with the
  ELLIPSE file, 439 of them with the same text once whitespace and case are
  normalized, and none of the 13,467 other essays does. ELLIPSE is therefore not
  independent of the confirmatory learner arm.

Two harness commits landed after the second token: 628eca8 (a table set may
select rows by a list of values) and 7198706 (`--jobs`). Neither touches a rule,
a threshold, the corpus, the sampling or a seed. On every 20th PERSUADE essay the
harness as it stood at the second token and the harness of the receipt run wrote
the same bytes.

One sentence of the extension overstates a rule. It says a four-digit count no
longer silences `unsupported-authority`. That holds for a count in running text,
such as "in 1200 patients"; a count in parentheses, such as "(1600 patients)",
still reads as a citation year. That is a known defect, recorded as a test.

What the anchors cover. Each token signs the bytes of this file. Through its
text the second token fixes the manifest hash, the corpus hash, the thresholds,
the seed and the 64-bit ruleset fingerprint the run measured. Neither token
signs the harness code; git history and the byte-identity proof above pin it.
The pull request was opened on 26 September at 18:38 UTC, before the
confirmatory amendment, so its creation time anchors the original gate table
only and says nothing about the order of the confirmatory run. From the next
amendment on, the anchored text names the harness commit's tree hash.

The release check. These items tighten the check and change no gate:

- The published-ruleset record changes in a commit after a release publishes,
  never in the release commit. The check skips the gates only when the record
  names an earlier package version than the one being built. A record that
  names the version being built, or no readable version, never skips them. This
  replaces "the release commit updates it" in the amendment of 26 September:
  under that wording the release commit's own record passed the ruleset it
  introduced without reading a receipt.
- A second receipt for one ruleset from one manifest fails the check, whatever
  the file names.
- Each stored G1 and G2 flag is checked against the receipt's stored numbers,
  and the raw G1 gap and interval are recomputed from the stored counts. The
  check trusts each stored G2 state, within-group gap and count of changed
  documents, since it cannot recompute them without the documents.
- `fairness/receipts/SHA256SUMS` pins every committed receipt by its bytes, and
  the check refuses a receipt that differs from its pin. The confirmatory
  receipt's SHA-256 is
  `22992435165b85aa04f2096627060d0a5e0ccdb5b8cc9a72af2befd229f1e7a7`.
- An override counts as a regression every gate row that fails in the new
  receipt and did not fail in the published ruleset's receipt, a row that
  receipt lacked included. It compares only with a receipt of the published
  ruleset itself whose flags agree with its numbers, and it is refused when the
  record names the ruleset being released.
- No receipt of another ruleset on PERSUADE 2.0 made after 27 September 2026
  serves as an override's comparison base for `sha256:46e1485cd2c98caa`: such a
  base would be chosen with this result known. A later pre-registration names
  any override base before its first reading.

After the reading. PERSUADE 2.0 confirms `sha256:46e1485cd2c98caa` only. For any
other ruleset its receipt is exploratory: the outcome on these essays is known,
and a change made in response to it is tuned on it. A changed ruleset still needs
a passing receipt from both manifests in the release-requirements block, which
does not change, and it also needs a confirmatory receipt from a corpus
pre-registered for it. The check reads that binding from the confirmatory block
below and fails a changed ruleset with none. The amendment that names the next
confirmatory corpus lands and is timestamped before that corpus is read, and it:

- records an overlap check, by id and by normalized-text hash, against every
  corpus already read (Liang et al., PERSUADE 2.0 and ELLIPSE);
- names the ruleset fingerprint, the harness commit's tree hash and any
  override comparison base;
- settles what this run showed the rules leave open: a G2 reading for an arm
  with no hits (the percentile bootstrap gives `[inf, inf]`), a multiplicity
  statement for per-rule readings, whether the G4 rewrap keeps paragraph
  breaks, G4's wording (the code compares HIGH and MEDIUM findings, the density
  count and words), and a receipt key for the notes whose rule ids carry a
  count.

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

## Confirmatory manifests, machine-readable

A test checks that this block equals `fairness_release.CONFIRMATORY`: each
confirmatory manifest and the one ruleset fingerprint it confirms (amended 27
September 2026, see above).

```json
{
  "sha256:8de8a1e6414e18f03730156ef6c4e8c87dc2f68fe73f0549d42cf4ea0788b4c3":
    "sha256:46e1485cd2c98caa"
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
