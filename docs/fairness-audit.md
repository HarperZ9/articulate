# Fairness audit

This page reports how Articulate's rules treat writing from different groups on
the Liang et al. (2023) corpus: under the rules of the published 0.5.0 package,
and under ruleset `sha256:46e1485cd2c98caa`, the rules this release candidate
carries. The numbers come from two content-free receipts in
`fairness/receipts/`. A test compares every row of every table on this page with
the receipt it cites, checks that the after receipt is the current ruleset's,
and checks the release sentence against the stored result. Numbers in running
text that no table carries are marked as counted by hand or simulated.

Receipts: before = `fairness/receipts/baseline-sha256-96ebbd442c9dc938.json`,
after = `fairness/receipts/sha256-46e1485cd2c98caa.json`.

The before receipt measures the rules of the published 0.5.0 package. Two
earlier drafts of the new rules also have receipts in the repository. The first,
`sha256-22a7b980e3dba991.json`, failed two gates on this corpus; "What changed
after the first run" below says what moved. Its report-only rows for the
repeated-phrase and repeated-opener notes were removed, because their keys
quoted three to five words of the corpus, and the receipt says so. The second,
`sha256-1c8f54b02d8aa211.json`, gave the same gate rows as the current ruleset.

## The short version

- Under the 0.5.0 rules the default profile blocked 38 of 91 learner exam texts,
  against 21 of 70 US college essay windows and 31 of 145 student abstract
  windows. One rule, the intensifier list (`really`, `actually`, `truly`,
  `genuinely`), fired about 11 times as often per word on the learner texts.
- Under the new rules the default profile blocks none of the 306 human texts
  and none of the 91 rewritten ones. Under it, only two rule families can block
  at all: a line where the speaker calls itself software (or an interface markup
  token), and a hidden character inside Latin text. A gate that blocks almost
  nothing passes a gap test easily, so the notes a writer still sees are
  measured below.
- The strict `essay` profile blocks 1 of 91 learner texts, 0 of 70 college
  windows and 4 of 145 abstract windows. Every gap lies inside 5 points.
- Every release gate passes on this corpus. The rules were changed after
  reading it, so the pass is exploratory. On PERSUADE 2.0, the corpus the rules
  were not tuned on, the release gate fails; see
  [the confirmatory run](fairness-confirmatory.md).
- The house style's notes (the intensifiers among them) show only under a house
  profile or when the writer asks. One note that shows by default is skewed
  toward the learner texts by the G2 rule: the repeated-phrase note, on 8 of 91
  learner texts and 1 of 70 college windows.
- These are proxy corpora with small arms. On this corpus a 95% interval reaches
  between about 3 and about 15 points from its estimate (counted from the gap
  rows below). No arm groups adult academic writers by first language, and none
  covers dictated text, disabled writers or World Englishes.

## What was tested

| Arm | Texts | Source | What it stands in for |
|:-|:-|:-|:-|
| Learner exam scripts | 91 | Liang et al. (2023) release, TOEFL forum texts | Second-language learners; the texts read like prepared speaking-task scripts, so this arm also stands in for spoken register |
| College essay windows | 70 | Same release, US college admission essays, first window of about 104 words | A first-language proxy; writers' first language is not recorded |
| Abstract windows | 145 | Same release, Stanford course project abstracts, first window | Academic register; writers' first language is not recorded |
| Rewritten learner texts | 91 | Same release, the learner texts after a GPT-4 rewrite | Paired check only; it concerns rewriting and never gates |

The release is Liang, Yuksekgonul, Mao, Wu and Zou, "GPT detectors are biased
against non-native English writers" (Patterns 4, 100779, 2023; data at
github.com/Weixin-Liang/ChatGPT-Detector-Bias, tag v1.0.0). It has no licence
file (its README shows an MIT badge), so its texts stay outside this repository
and every run is local.

Windows are sentence-aligned runs of about 104 words, the learner texts' median,
so length does not drive the comparison. The release also includes the US
eighth-grade essays the study used as its native comparison. We removed their
text from our local build under our reading of the Kaggle ASAP competition
rules. Whether those rules allow this use is unverified, so that arm does not
run here. The held-out arm of written learner essays is PERSUADE 2.0, on the
[confirmatory page](fairness-confirmatory.md).

Before any new result, the harness had to reproduce the earlier exploratory
audit on the same texts. It did, exactly: 38, 21 and 31 blocked under the
default profile, 44, 30 and 86 under the old essay profile, and the same
intervals and McNemar p-value.

## Block rates

A text is blocked when the profile's gate says `blocked`. Counts are texts.

| Receipt | Profile | Learner scripts | College windows | Abstract windows |
|:-|:-|:-|:-|:-|
| before | flavored | 38 of 91 | 21 of 70 | 31 of 145 |
| after | flavored | 0 of 91 | 0 of 70 | 0 of 145 |
| before | essay | 44 of 91 | 30 of 70 | 86 of 145 |
| after | essay | 1 of 91 | 0 of 70 | 4 of 145 |
| after | house | 37 of 91 | 19 of 70 | 23 of 145 |
| after | house-essay | 46 of 91 | 27 of 70 | 82 of 145 |

`flavored` is the default profile. Under the 0.5.0 rules, `essay` held the full
house style; under the new rules that profile is `house-essay` and `essay` holds
only rules with a stated reader cost. The `house` profile is close to the old
default but not identical: `wordiness` moved to the medium tier, `in order to`
and `state of the art` became notes that never block, and the reply opener and
the self-description rule narrowed.

Under `essay`, the receipt's per-rule counts show what still blocks: in the
abstract windows, the throat-clearing opener in 2, a marketing superlative in 1
and an authority appeal with no citation in 1; in the learner texts, the stock
phrase "plays a vital role" or "a testament to" in 1.

## Gaps between groups

Learner block rate minus comparator block rate, in points, with a 95% Newcombe
interval. A positive gap means learner texts were blocked more often.

| Receipt | Profile | Comparison | Gap | 95% interval |
|:-|:-|:-|:-|:-|
| before | flavored | learner vs college | 11.8 | [-3.3, 25.7] |
| before | flavored | learner vs abstracts | 20.4 | [8.3, 32.2] |
| after | flavored | learner vs college | 0.0 | [-5.2, 4.1] |
| after | flavored | learner vs abstracts | 0.0 | [-2.6, 4.1] |
| before | essay | learner vs college | 5.5 | [-9.9, 20.4] |
| before | essay | learner vs abstracts | -11.0 | [-23.5, 2.0] |
| after | essay | learner vs college | 1.1 | [-4.2, 6.0] |
| after | essay | learner vs abstracts | -1.7 | [-5.9, 3.5] |
| after | house | learner vs college | 13.5 | [-1.3, 27.2] |
| after | house | learner vs abstracts | 24.8 | [13.1, 36.2] |

A house profile is chosen, never assigned by a path, and it never gates a
release. Its gap is larger than the old default's was. A project that sets
`profile: house` in the GitHub Action applies it to every contributor, and the
Action prints a notice when it does.

## How small a gap each arm can see

The gap whose 95% Newcombe interval would just exclude zero, holding the
comparison arm at its observed count. A true gap of that size is detected about
half the time. It states power and reports no result.

| Receipt | Profile | Comparison | Smallest detectable gap |
|:-|:-|:-|:-|
| after | flavored | learner vs college | 6.6 |
| after | flavored | learner vs abstracts | 4.4 |
| after | essay | learner vs college | 6.6 |
| after | essay | learner vs abstracts | 6.0 |

Detecting a gap 80% of the time takes about 8.4 points against the college
windows under either profile, and about 6.0 (`flavored`) and 8.7 (`essay`)
against the abstracts (simulated post hoc from the arm sizes and the comparison
arm's rate). So against the 70 college windows neither profile can reliably
tell a gap near the 5-point G1 line from zero. A G1 pass here says the observed
gap is small; it cannot say a 5-point gap is absent. The before receipt stores
the older normal approximation (15.0 and 11.9 points); the same search on its
counts gives 16.2 and 11.6 points (counted by hand from the receipt's counts).

## Cadence

Uniform cadence is an even run of medium-length sentences: the sentence-length
statistic that perplexity detectors use for burstiness.

| Receipt | Profile | Comparison | Learner flagged | Comparator flagged | Gap | 95% interval |
|:-|:-|:-|:-|:-|:-|:-|
| before | flavored | learner vs college | 12 of 91 | 1 of 70 | 11.8 | [3.5, 20.3] |
| before | flavored | learner vs abstracts | 12 of 91 | 0 of 145 | 13.2 | [7.1, 21.6] |
| after | flavored | learner vs college | 0 of 91 | 0 of 70 | 0.0 | [-5.2, 4.1] |
| after | flavored | learner vs abstracts | 0 of 91 | 0 of 145 | 0.0 | [-2.6, 4.1] |

The flag skewed toward learner texts before the change. After it the flag needs
12 sentences and 200 words, and every learner text is shorter (153 words at
most by the checker's count, counted by hand from the corpus), so the zero comes
from the length floor. On texts of 200 words or more the flag is unmeasured.
It never blocked. It is now left out of `check --json` and the MCP `score` tool,
and only the fairness harness reads it.

## The gates

The gates are fixed in `fairness/PREREG.md`. That file was written after the
exploratory audit had read these texts, so on this corpus the gates are not
pre-registered; they bind every corpus added later. Its dated amendments
tighten the gates, narrow the release block to ruleset changes and, after the
confirmatory run, tighten the release check.

| Gate | Before | After | What drives the result after |
|:-|:-|:-|:-|
| G1 gap within 5 points, both directions | fails | passes | 0 of the 38 bound profiles fail. The widest gaps are under `essay` and 11 other strict profiles and modes: 1.1 [-4.2, 6.0] against college windows and -1.7 [-5.9, 3.5] against abstracts |
| G2 no skewed or inconclusive blocking rule | fails | passes | Under `essay`, four rules block any text; each is not skewed toward learner texts or bounded (it fires on at most 2% of every arm) |
| G4 findings unchanged by layout | fails, 78 of 306 texts changed | passes, 0 changed | Checked two ways: one sentence per line, and a hard wrap at 60 columns that breaks at hyphens |
| G5 cadence | report only | report only | No cadence signal blocks or enters an editing target; see Cadence above |
| G6 editor behavior by group | not run | not run | Needs editor runs through a model on every arm |
| G7 block rate on human text above 10% opens a review | all three arms | none | The highest bound-profile rate is 2.8%, 4 of 145 abstract windows under `essay` |
| G8 notes a writer sees, by group | not measured | report only | See "What writers still see" |

So the release gate passes on this corpus for ruleset `sha256:46e1485cd2c98caa`:
all 266 gate rows (one gate, one bound profile and, for G1, G2 and G5, one
comparison) pass (counted from the receipt). Against the before receipt, 173
rows move from fail to pass and none from pass to fail (counted from both
receipts). The pass is exploratory, since the rules were changed after reading
this corpus.

## What changed after the first run

The first run of the new rules failed G1 and G2. Under `essay` it blocked 19 of
145 abstract windows against 2 of 91 learner texts. Of those 19, 16 were blocked
by `in order to` or `state of the art` alone or together (counted by hand from a
local run, with no text kept). Both phrases were then judged on reader cost,
before re-measuring:

- `in order to` became a LOW note, `padded-purpose`. Usually "to" does the same
  work, and usage guides keep it where it separates a purpose from a
  complement, so it is sometimes the clearer choice.
- `state of the art` became a LOW note, `unanchored-claim`, that fires only when
  its sentence carries no number, year or citation marker. In research writing
  the phrase names the best published result on a named benchmark.
- Two notes that showed by default and skewed toward learner texts moved to the
  house pack: the typographic quotation mark, which word processors and phone
  keyboards insert, and a bare "There is" opener. "It is important" at a
  sentence start stays a default note.

None of these can block. On PERSUADE 2.0, which the rules were not tuned on,
neither `padded-purpose` nor `unanchored-claim` is skewed toward learner essays.

## Rules, one by one

The intensifier rule (`really`, `actually`, `truly`, `genuinely`) was the only rule the
exploratory audit called skewed: it fired on 26 learner texts, 2 college windows
and 4 abstract windows, about 10.6 times the college rate per 1,000 words. An
earlier draft of this change kept `truly` and `genuinely` as blocking and moved
only `really` and `actually` to report-only. That split followed the audit data
(learners use `really`; model rewrites use `truly`) and so rested on how often
models use a word, a reason this project no longer accepts. All four are now
house style.

Other rules left the default gate for the same reason, or because learners are
taught them: the em dash, the contrast devices, `instead` and `rather than`,
ordinal enumeration ("Firstly,"), stock transitions, closers, cadence beats, the
register word lists, and the stock phrases of email, blog and marketing hooks.
A bare "Of course," or "Absolutely." reports only. A reply opener that hands
over a deliverable ("Certainly! Here is your essay:") also reports only under
the default, since an email reply does that on purpose; `essay` and the house
profiles block it. The self-description rule needs "AI" or "language model"
beside the first person, so "As an assistant, I managed the calendars", "my
training data" and "I don't have real-time access" raise nothing. A zero-width
space blocks only between Latin letters, since Thai, Khmer, Lao and Myanmar
text uses it at word boundaries.

Each rule that can still block a writer who did not choose the house style
carries a one-sentence reader-cost reason and a published source
(`src/articulate/rule_reasons.py`), and so do the two new notes. A person other
than the maintainer has not yet reviewed those reasons.

## What writers still see

Report-only notes show in the console with `--verbose`, as SARIF notes and as
editor hints. House notes show only under a house profile or when the writer
passes `--house-notes`. Under the default profile, these notes are skewed toward
the learner texts by the G2 rule:

| Receipt | Profile | Comparison | Note | Learner texts | Comparator texts | Ratio per 1,000 words | Shown by default |
|:-|:-|:-|:-|:-|:-|:-|:-|
| after | flavored | learner vs college | `LOW\|ngram-repetition` | 8 | 1 | 6.53 | yes |
| after | flavored | learner vs abstracts | `LOW\|curly-quote/curly-quotation-mark-apostrophe` | 14 | 2 | 29.79 | no |
| after | flavored | learner vs abstracts | `LOW\|existential-opener/existential-opener-there-is-there-are` | 9 | 1 | 15.32 | no |
| after | flavored | learner vs college | `LOW\|existential-opener/existential-opener-there-is-there-are` | 9 | 1 | 7.34 | no |
| after | flavored | learner vs abstracts | `LOW\|intensifier/genuinely-really-truly-actually` | 26 | 4 | 15.75 | no |
| after | flavored | learner vs college | `LOW\|intensifier/genuinely-really-truly-actually` | 26 | 1 | 30.19 | no |
| after | flavored | learner vs abstracts | `LOW\|enumeration/ly-ordinal-enumeration-firstly-secondly` | 6 | 1 | 10.21 | no |
| after | flavored | learner vs college | `LOW\|enumeration/ly-ordinal-enumeration-firstly-secondly` | 6 | 0 | inf | no |

Every one of them but the first is a house note. The first, the repeated-phrase
note, shows by default. Its own reason concedes that repeating a key term is
plain-language practice, so its cost to a reader depends on the use. By the
principle of decision 3 on pull request 9, that makes it a candidate for the
house pack. Moving it changes the ruleset, so it waits for the next
pre-registered ruleset.

These notes that show by default are inconclusive at these sizes, so a skew
cannot be ruled out either:

| Receipt | Profile | Comparison | Note | Learner texts | Comparator texts | Ratio per 1,000 words | Shown by default |
|:-|:-|:-|:-|:-|:-|:-|:-|
| after | flavored | learner vs abstracts | `LOW\|ellipsis-char/ellipsis-character-u-2026` | 2 | 0 | inf | yes |
| after | flavored | learner vs abstracts | `LOW\|hedge-cluster/3-hedges-in-one-sentence` | 2 | 0 | inf | yes |
| after | flavored | learner vs abstracts | `LOW\|superlative/hedged-superlative-one-of-the-most-x` | 4 | 4 | 1.7 | yes |
| after | flavored | learner vs college | `LOW\|closer-question/rhetorical-question` | 1 | 2 | 0.27 | yes |
| after | flavored | learner vs college | `LOW\|concessive-opener/concession-then-resolution-opener-despite-x-y` | 2 | 2 | 0.82 | yes |
| after | flavored | learner vs college | `LOW\|hedge-cluster/3-hedges-in-one-sentence` | 2 | 1 | 1.63 | yes |
| after | flavored | learner vs college | `LOW\|padded-purpose/padded-purpose-in-order-to` | 1 | 2 | 0.41 | yes |
| after | flavored | learner vs college | `LOW\|superlative/hedged-superlative-one-of-the-most-x` | 4 | 1 | 3.26 | yes |
| after | flavored | learner vs college | `LOW\|vague-quantifier/vague-quantifier-no-number-given` | 7 | 2 | 2.86 | yes |

Nothing blocks on any of them, and the density figure leaves them out.

## Paired rewrites

The same learner text before and after a GPT-4 rewrite. This check concerns
rewriting and never gates.

| Receipt | Profile | Originals only | Rewrites only | McNemar p |
|:-|:-|:-|:-|:-|
| before | flavored | 24 | 11 | 0.041 |
| after | flavored | 0 | 0 | 1.0 |
| after | essay | 1 | 6 | 0.125 |
| after | house | 23 | 11 | 0.0576 |
| after | house-essay | 4 | 35 | below 0.0001 |

The after receipt computes this for 25 configurations. Under the 12 strict
profiles it reads 1 and 6 (p 0.125), under `house-essay` 4 and 35, under `house`
23 and 11, and under every other profile at most 1 either way (p 1.0). Before
the change the default profile blocked 38 original learner texts and 25 of
their rewrites. Under `house`, rewrites pass more often than the originals;
under `house-essay` and the strict profiles, rewrites are blocked more often.
Each p-value is exact and uncorrected, and exploratory: the rules were tuned on
this corpus, the rewrites come from one GPT-4 prompt, and there are 91 pairs. A
difference here shows how the rules read a rewrite. It is no signal of who or
what wrote a text.

## What these numbers do not show

They show how these rules behave on these texts. They do not show who wrote any
text, that first language causes any gap (the arms also differ in age, task,
topic and register), fairness to any group or genre not listed above, or the
accuracy of any detector. A gate that blocks nothing passes the gap test
trivially; that is why the report-only notes above are measured as well. A pass
on the corpus the rules were tuned on does not confirm the rules, and on the
held-out corpus the gate fails.

## Rerun it

The manifest the release check pins is `fairness/manifests/liang-2023.json`. It
names each text by a path of the form `essays/<subset>/<n>.txt` in a local build
of the release, one file per text, and pins each file's SHA-256. The build step
that writes those files from the release is not part of this repository. The
harness refuses any text whose hash differs, so a rebuild that matches every
hash reproduces the receipt, and one that does not fails loudly. Then run:

```
python -m articulate.fairness fairness/manifests/liang-2023.json --root BUILD --out RECEIPT
python -m articulate.fairness --release-check fairness/receipts
```

The first writes a content-free receipt. Rules whose labels quote the text (the
n-gram repetition and anaphora notes) are keyed by category, so no corpus words
reach it. The second checks the current ruleset. When its fingerprint equals the
one in `fairness/published-ruleset.json` and that record names an earlier
release, it passes and says the gates were not re-run. Otherwise it recomputes
the gate summary from the committed receipts, checks each stored flag against
its stored numbers and each receipt against its pin, and fails when a receipt is
missing or duplicated, came from a manifest not listed in `fairness/PREREG.md`,
leaves out a required comparison or a bound profile, has no confirmatory
reading for this ruleset, or a gate fails. An override for one exact ruleset
passes only when no gate row fails that did not fail in the published ruleset's
own receipt, and the check prints that comparison.
