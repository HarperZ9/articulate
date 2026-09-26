# Fairness audit

This page reports how Articulate's rules treat writing from different groups, on
the corpora run so far, before and after ruleset 0.7.0. Every number here comes
from a content-free receipt in `fairness/receipts/`, and a test fails when a
number on this page differs from the receipt it cites.

Receipts: before = `fairness/receipts/baseline-sha256-96ebbd442c9dc938.json`,
after = `fairness/receipts/sha256-0840131b065593fb.json`.

## The short version

- Before 0.7.0 the default profile blocked 38 of 91 learner exam texts, against
  21 of 70 US college essay windows and 31 of 145 student abstract windows. One
  rule, the intensifier list (`really`, `actually`, `truly`, `genuinely`), fired about 11
  times as often per word on the learner texts.
- After 0.7.0 the default profile blocks none of the 306 human texts. The
  intensifiers and the rest of the house style still report as low-tier notes,
  and only a house profile a writer chooses blocks on them.
- The strict `essay` profile now blocks 2 of 91, 2 of 70 and 19 of 145. It still
  fails the pre-registered gap gate in the other direction: it blocks student
  abstracts more often than learner texts. That result is recorded here and not
  tuned away.
- These are proxy corpora with small arms. At these sizes an interval spans
  from about 2 to about 15 points either side of its estimate, and no arm covers adult academic
  writers, dictated text, disabled writers or World Englishes yet.

## What was tested

| Arm | Texts | Source | What it stands in for |
|:-|:-|:-|:-|
| Learner exam scripts | 91 | Liang et al. (2023) release, TOEFL forum texts | Second-language learners; the texts read like prepared speaking-task scripts, so this arm also stands in for spoken register |
| College essay windows | 70 | Same release, US college admission essays, first window of about 104 words | A first-language proxy; writers' first language is not recorded |
| Abstract windows | 145 | Same release, Stanford course project abstracts, first window | Academic register; writers' first language is not recorded |
| Rewritten learner texts | 91 | Same release, the learner texts after a GPT-4 rewrite | Paired check only; it concerns rewriting and never gates |

The release is Liang, Yuksekgonul, Mao, Wu and Zou, "GPT detectors are biased
against non-native English writers" (Patterns 4, 100779, 2023; data at
github.com/Weixin-Liang/ChatGPT-Detector-Bias, tag v1.0.0). It carries no licence
file, so its texts stay outside this repository and every run is local.

Windows are sentence-aligned runs of about 104 words, the learner texts' median,
so length does not drive the comparison. The US eighth-grade essays the study
used did not run: their text is withheld under the Kaggle competition terms.

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
identical: `wordiness` moved to the medium tier and the chat-reply opener rule
narrowed.

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

The smallest gap each arm could tell from zero, at its own block rate, was 15.0
and 11.9 points for the default profile before the change; it is 2.4 and 1.7
points after it, and 4.9 and 7.5 points for `essay`.

## The gates

The gates are fixed in `fairness/PREREG.md`. That file was written after the
exploratory audit had read these texts, so on this corpus the gates are not
pre-registered; they bind every licensed corpus added later.

| Gate | Before | After | What drives the result after |
|:-|:-|:-|:-|
| G1 gap within 5 points, both directions | fails | fails | `essay`, `commit`, the essay-based modes and `journalism/explain` block abstracts more often than learner texts (-10.9 [-17.6, -3.8]), from marketing superlatives such as `state-of-the-art` and padded phrases such as `with respect to`; `marketing/explain` gives -5.5 [-10.5, -0.7] |
| G2 no skewed or inconclusive blocking rule | fails | fails | `wordiness` fires on 1 learner text and 2 college windows; the arm is too small to call it either way, and the rule says inconclusive fails |
| G4 findings unchanged by rewrapping | fails, 78 of 306 texts changed | passes, 0 changed | |
| G5 cadence | report only | report only | No cadence signal blocks or enters an editing target |
| G6 editor behavior by group | not run | not run | Needs editor runs through a model on every arm |
| G7 block rate on human text above 10% opens a review | all three arms | abstracts | `essay` blocks 13.1% of abstract windows |

So the release gate for ruleset 0.7.0 does not pass on this corpus. A failed
gate blocks a ruleset release; it never blocks anyone's run. The open choices are
to drop or narrow `marketing` and `wordiness` in the strict profiles, or to grow
the arms with licensed corpora before deciding.

## Rules, one by one

The intensifier rule (`really`, `actually`, `truly`, `genuinely`) was the only rule the
exploratory audit called skewed: it fired on 26 learner texts, 2 college windows
and 4 abstract windows, about 10.6 times the college rate per 1,000 words. An
earlier draft of this change kept `truly` and `genuinely` as blocking and moved
only `really` and `actually` to report-only. That split followed the audit data
(learners use `really`; model rewrites use `truly`) and so rested on how often
models use a word, a reason this project no longer accepts. All four now report
only, outside the house pack.

Other rules left the default gate for the same reason, or because learners are
taught them: the em dash, the contrast devices, `instead` and `rather than`,
ordinal enumeration ("Firstly,"), stock transitions, closers, cadence beats, the
register word lists, and the stock phrases of email, blog and marketing hooks.
A bare "Of course," or "Absolutely." reports only; a chat reply that hands over a
deliverable ("Certainly! Here is your essay:") still blocks. A zero-width space
blocks only between Latin letters, since Thai, Khmer, Lao and Myanmar text uses
it at word boundaries.

Each rule that can still block a writer who did not choose the house style
carries a one-sentence reader-cost reason and a published source
(`src/articulate/rule_reasons.py`). A person other than the maintainer has not
yet reviewed those reasons.

## What writers still see

Report-only findings still show in the console with `--verbose`, as SARIF notes
and as editor hints. On these texts the intensifier note still appears on 26 of
91 learner texts against 2 of 70 college windows. Nothing blocks on it, and the
density figure leaves house-style findings out, yet a learner still sees more of
these notes. Whether house-style notes should show at all outside a house
profile is an open decision.

## Paired rewrites

Before the change, the default profile blocked 38 original learner texts and 25
of their GPT-4 rewrites (24 originals only, 11 rewrites only, exact McNemar
p = 0.041). After it, the default profile blocks none of either. This check
concerns rewriting and never gates.

## What these numbers do not show

They show how these rules behave on these texts. They do not show who wrote any
text, that first language causes any gap (the arms also differ in age, task,
topic and register), fairness to any group or genre not listed above, or the
accuracy of any detector. A gate that blocks nothing passes the gap test
trivially; that is why the reported findings above are listed as well.

## Rerun it

Get the release and write a manifest in the schema
`articulate/fairness-manifest/v1` (corpora, sets with group labels and window
rules, documents with SHA-256 hashes, comparisons). Then run:

```
python -m articulate.fairness MANIFEST --out RECEIPT
python -m articulate.fairness --release-check fairness/receipts
```

The first writes a content-free receipt. The second fails when the current
ruleset has no committed receipt, a gate fails, or a bound profile is missing.
