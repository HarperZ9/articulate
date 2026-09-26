# Fairness audit

This page reports how Articulate's rules treat writing from different groups, on
the corpora run so far, before and after ruleset 0.7.0. The numbers come from
two content-free receipts in `fairness/receipts/`. A test compares every row of
every table on this page with the receipt it cites, and the release sentence
with the stored result. Numbers in running text that no table carries are marked
as counted by hand.

Receipts: before = `fairness/receipts/baseline-sha256-96ebbd442c9dc938.json`,
after = `fairness/receipts/sha256-22a7b980e3dba991.json`.

## The short version

- Before 0.7.0 the default profile blocked 38 of 91 learner exam texts, against
  21 of 70 US college essay windows and 31 of 145 student abstract windows. One
  rule, the intensifier list (`really`, `actually`, `truly`, `genuinely`), fired
  about 11 times as often per word on the learner texts.
- After 0.7.0 the default profile blocks none of the 306 human texts and none of
  the 91 rewritten ones. Under it, only two rule families can block at all: a
  line where the speaker calls itself software (or an interface markup token),
  and a hidden character inside Latin text. A gate that blocks almost nothing
  passes a gap test easily, so the notes a writer still sees are measured below.
- The house style's notes (the intensifiers among them) no longer show outside a
  house profile unless the writer asks. Two notes that still show by default are
  skewed toward the learner texts: the typographic apostrophe and the empty
  opener ("There is", "It is important").
- Fourteen stricter profiles and modes, `essay` among them, block 19 of 145
  abstract windows against 2 of 91 learner texts. That fails the gap gate in the
  other direction, so the release gate fails. It is recorded here and not tuned
  away.
- These are proxy corpora with small arms. A 95% interval here spans from about
  4 to about 16 points either side of its estimate. No arm groups adult
  academic writers by first language, and none covers dictated text, disabled
  writers or World Englishes.

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
rules, and whether those rules forbid this use is unknown, so the study's own
native comparison has not run here. It is the next arm to run.

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
| after | essay | 2 of 91 | 2 of 70 | 19 of 145 |
| after | house | 37 of 91 | 20 of 70 | 23 of 145 |
| after | house-essay | 47 of 91 | 30 of 70 | 87 of 145 |

`flavored` is the default profile. Before 0.7.0, `essay` held the full house
style; after it, that profile is `house-essay` and `essay` holds only rules with a
stated reader cost. The `house` profile is close to the old default but not
identical: `wordiness` moved to the medium tier, and the reply opener and the
self-description rule narrowed.

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
| after | essay | learner vs college | -0.7 | [-7.8, 5.2] |
| after | essay | learner vs abstracts | -10.9 | [-17.6, -3.8] |
| after | house | learner vs college | 12.1 | [-2.8, 25.9] |
| after | house | learner vs abstracts | 24.8 | [13.1, 36.2] |

A house profile is chosen, never assigned by a path, and it never gates a
release. Its gap is larger than the old default's was. A project that sets
`profile: house` in the GitHub Action applies it to every contributor, and the
Action prints a notice when it does.

## How small a gap each arm can see

The smallest gap whose 95% Newcombe interval would exclude zero, holding the
comparison arm at its observed count. It states power and reports no result.

| Receipt | Profile | Comparison | Smallest detectable gap |
|:-|:-|:-|:-|
| after | flavored | learner vs college | 6.6 |
| after | flavored | learner vs abstracts | 4.4 |
| after | essay | learner vs college | 9.2 |
| after | essay | learner vs abstracts | 10.0 |

So against the 70 college windows the default profile cannot tell a gap under
6.6 points from zero, which is above the 5-point line G1 draws. The before
receipt stores the older normal approximation (15.0 and 11.9 points); the same
search on its counts gives 16.2 and 11.6 points (counted by hand from the
receipt's counts).

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
pre-registered; they bind every corpus added later. Its dated amendments only
tighten them.

| Gate | Before | After | What drives the result after |
|:-|:-|:-|:-|
| G1 gap within 5 points, both directions | fails | fails | 12 strict profiles and modes block abstracts more often than learner texts, -10.9 [-17.6, -3.8]: `essay`, `commit`, `journalism/explain`, `legal/argue`, `marketing/persuade`, `memo/argue`, `memo/explain`, `memo/instruct`, `persuasive-essay/argue`, `persuasive-essay/persuade`, `technical-docs/instruct` and `tutorial/instruct`. `marketing/explain` and `marketing/narrate` give -5.5 [-10.5, -0.7]. That is 14 of the 38 bound profiles. |
| G2 no skewed or inconclusive blocking rule | fails | fails | `wordiness` fires on 1 learner text and 2 college windows; the arm is too small to call it either way, and the rule says inconclusive fails |
| G4 findings unchanged by layout | fails, 78 of 306 texts changed | passes, 0 changed | Now checked two ways: one sentence per line, and a hard wrap at 60 columns that breaks at hyphens |
| G5 cadence | report only | report only | No cadence signal blocks or enters an editing target; see Cadence above |
| G6 editor behavior by group | not run | not run | Needs editor runs through a model on every arm |
| G7 block rate on human text above 10% opens a review | all three arms | abstracts | `essay` blocks 13.1% of abstract windows |
| G8 notes a writer sees, by group | not measured | report only | See "What writers still see" |

Under `essay`, the 19 blocked abstract windows break down like this (counted by
hand from a local run, with no text kept): 8 by the padded-phrase rule alone,
where every match is `in order to`; 7 by the superlative rule alone, mostly
`state of the art`; 1 by both; 2 by `when it comes to`; and 1 by
`research suggests`.

So the release gate for ruleset 0.7.0 does not pass on this corpus. Every
package release runs the check, so no release publishes until the gate passes
or a maintainer records an override with a reason. It never blocks anyone's
run. The open choices are to judge `in order to` and `state of the art` on
reader cost (academic writing guides teach both), to narrow `marketing` and
`wordiness` in the strict profiles, or to grow the arms before deciding.
Deciding from these counts alone would fit the gate to the corpus it was tuned
on, so any change needs a new corpus to confirm it.

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
(`src/articulate/rule_reasons.py`). A person other than the maintainer has not
yet reviewed those reasons.

## What writers still see

Report-only notes show in the console with `--verbose`, as SARIF notes and as
editor hints. House notes no longer show outside a house profile unless the
writer passes `--house-notes`. These report-only notes under the default
profile are skewed toward the learner texts by the G2 rule:

| Receipt | Profile | Comparison | Note | Learner texts | Comparator texts | Ratio per 1,000 words | Shown by default |
|:-|:-|:-|:-|:-|:-|:-|:-|
| after | flavored | learner vs abstracts | `LOW\|curly-quote/curly-quotation-mark-apostrophe` | 14 | 2 | 29.79 | yes |
| after | flavored | learner vs abstracts | `LOW\|expletive-opener/empty-opener-there-is-it-is-important` | 9 | 1 | 15.32 | yes |
| after | flavored | learner vs college | `LOW\|expletive-opener/empty-opener-there-is-it-is-important` | 9 | 1 | 7.34 | yes |
| after | flavored | learner vs abstracts | `LOW\|intensifier/genuinely-really-truly-actually` | 26 | 4 | 15.75 | no |
| after | flavored | learner vs college | `LOW\|intensifier/genuinely-really-truly-actually` | 26 | 2 | 15.1 | no |
| after | flavored | learner vs abstracts | `LOW\|enumeration/ly-ordinal-enumeration-firstly-secondly` | 6 | 1 | 10.21 | no |

A typographic apostrophe costs a reader nothing, and the empty opener is taught
in many writing courses. Whether either should show by default is an open
decision; nothing blocks on them, and the density figure leaves them out.

## Paired rewrites

The same learner text before and after a GPT-4 rewrite. This check concerns
rewriting and never gates.

| Receipt | Profile | Originals only | Rewrites only | McNemar p |
|:-|:-|:-|:-|:-|
| before | flavored | 24 | 11 | 0.041 |
| after | flavored | 0 | 0 | 1.0 |
| after | essay | 1 | 7 | 0.0703 |
| after | house | 23 | 11 | 0.0576 |

Before the change the default profile blocked 38 original learner texts and 25
of their rewrites. Under `house`, rewrites pass more often than the originals.

## What these numbers do not show

They show how these rules behave on these texts. They do not show who wrote any
text, that first language causes any gap (the arms also differ in age, task,
topic and register), fairness to any group or genre not listed above, or the
accuracy of any detector. A gate that blocks nothing passes the gap test
trivially; that is why the report-only notes above are measured as well.

## Rerun it

Get the release and write a manifest in the schema
`articulate/fairness-manifest/v1` (corpora, sets with group labels and window
rules, documents with SHA-256 hashes, comparisons). Then run:

```
python -m articulate.fairness MANIFEST --out RECEIPT
python -m articulate.fairness --release-check fairness/receipts
```

The first writes a content-free receipt. The second recomputes the gates from
the committed receipt for the current ruleset. It fails when that receipt is
missing, came from a manifest not listed in `fairness/PREREG.md`, leaves out a
required comparison or a bound profile, or a gate fails.
