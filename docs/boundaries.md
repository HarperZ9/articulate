# Boundaries

Articulate makes narrow claims on purpose. This page states what a finding, the
gate, a receipt, a process summary and the review desk mean, and what they never
mean. Read it before you rely on any of them.

<a id="no-verdict-is-an-authorship-finding"></a>

## No output is an authorship finding

No Articulate output shows who or what wrote a text. A finding, a per-rule count,
a density figure, a `--spans` paragraph, a receipt, a process record, a process
summary and a desk question each describe the text or the record. None of them
is evidence about its author. None of them is a basis for an accusation or a
penalty against a person.

The project declines to sell or support that use. It also declines to support
any deployment that requires a writer to keep a process record or hand one over:
consent that is a condition of an assignment is no free consent.

This is a documentation and sales rule. The code is open, and nothing technical
stops a desk from misusing a finding. The product's part is to emit nothing
shaped like an origin score: no verdict about the text, no likelihood, no 0 to
100 score. The gate says ok or blocked under the profile you chose, and nothing
more.

## Writing quality, never evasion

Articulate names patterns that cost a reader something and helps you rewrite for
your reader. It has no mode that aims at an outside score, and no editing target
names sentence-length variance, vocabulary level or any detector. Plain words
stay allowed, and the editor often prefers them.

That choice has a cost we state openly. Perplexity-based detectors tend to read
plain, predictable English as machine-like; a 2023 study found that rewriting
learners' essays with fancier vocabulary lowered their false flags. Articulate
will keep plain words where they serve the reader, even when a detector would
score the plainer text as more machine-like. We publish no claim about how
Articulate affects any outside detector.

## House style is a choice

The em dash, the contrast devices, the intensifiers, stock transitions and the
other house-pack patterns are one writer's style. Only the `house` and
`house-essay` profiles block on them. No other profile shows them unless you
pass `--house-notes`, and then they are low-tier notes that never block. No path
rule selects a house profile for you.

On the corpus run so far, the `house` profile blocked learner exam texts more
often than student abstracts (a gap of 24.8 points, 95% interval 13.1 to 36.2).
Against US college essay windows the gap was 12.1 points, and that interval
(-2.8 to 25.9) includes zero. A house profile is for your own text or your own
project's. Applying it to other people's writing, such as a course's
submissions, carries that gap to them. See [fairness-audit.md](fairness-audit.md).

## Exposition quality is no proof of correctness

For a proof or a scientific paper, an ok gate or a `Match` receipt means the
prose was screened under a named ruleset. It says nothing about whether the
theorem or the result is true. A clearly written proof can still be false.
Correctness is established by independent referee review or a machine-checked
formalization in a proof assistant such as Lean, Coq or Isabelle, by other
people, on a longer timescale. Articulate has no role in that step.

## A receipt attests a screening

A receipt records that a named, fingerprinted ruleset ran against a specific text
and produced specific findings and a gate, and that the same screening
re-derives on the same text. That is the whole claim. It makes no claim about
provenance or correctness and carries neither an EU AI Act Article 50 marking
nor a C2PA content credential. The replay result is `Match`, `Drift` or
`Unverifiable`, with no trusted or approved value.

## A process summary is declared provenance

A process summary shows that texts with its commitments were logged in its
order and which tools the writer declared. An anchor entry holds a git commit id
or a token hash as the writer recorded it. Articulate checks neither, and a
commit id shows only that the entry was written after that commit existed. The
summary does not show who composed the words, when anything happened, or that
the record is complete. Removing entries from the end of a log leaves a shorter
log that still checks. A writer can build a log after the fact, and an absent
record shows nothing about a writer. The summary is unsigned: it is no Content
Credential and no Article 50 marking.

The record keeps order and day by default. Word counts, change sizes and times
are opt-in and stay out of a default export, because paste size and typing time
are the signals that surveillance tools show graders. A default export carries
no value computed from them, so a reader cannot test guesses against it. How a
writer put words down (dictation, a screen reader, drafting in another
language) lives in a private file outside the log and stays out of every export
and statement unless the writer includes it.

## The desk asks and never ranks

The review desk prepares the questions a reviewer should ask, inside the
document and across the field. It checks the document's own statements and
cannot judge contribution, novelty or significance. It prints no score, no
verdict, no ranking and no question count, and it never reads a process record.
No study has measured how much time it saves a reviewer, and we claim none.

## Content-free is not zero-leakage

A content-free audit receipt keeps no verbatim text: it drops the matched
substring and the exact offsets. Which rules fired and the line remain, and for a
closed-vocabulary rule that narrows the flagged word to that rule's small, public
candidate set.

## Hash mode

A `--redact hash` receipt keeps a plain sha256 of each matched substring, for an
equality check against a string you already know. It is no confidentiality
measure: a holder can hash a rule's public vocabulary and recover the flagged
word. Use `--redact drop` when the word itself must stay secret.

## English patterns

The patterns are English literals. On a non-English document they simply do not
fire, so an empty result on non-English text means the English rules found
nothing. It is never a verification of the text.
