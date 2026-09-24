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

On the Liang et al. corpus, the `house` profile blocked learner exam texts more
often than student abstracts (a gap of 24.8 points, 95% interval 13.1 to 36.2).
Against US college essay windows the gap was 13.5 points, and that interval
(-1.3 to 27.2) includes zero. On PERSUADE 2.0 it blocked most school essays in
both groups: 57% of learner essays and 64% of the others. A house profile is
for your own text or your own project's. Applying it to other people's writing,
such as a course's submissions, carries those rates to them. See the
[fairness audit](fairness-audit.md) and the
[confirmatory run](fairness-confirmatory.md).

## Exposition quality is no proof of correctness

For a proof or a scientific paper, an ok gate or a `Match` receipt means the
prose was screened under a named ruleset. It says nothing about whether the
theorem or the result is true. A clearly written proof can still be false.
Correctness is established by independent referee review or a machine-checked
formalization in a proof assistant such as Lean, Coq or Isabelle, by other
people, on a longer timescale. Articulate has no role in that step.

## The meaning guard is a surface screen

The meaning guard compares numbers, negations, modal strength, scope words, named
entities, links, code, math, citations, quotes, and freeze terms between an
original and a rewrite. Those are surface proxies for meaning. A rewrite can keep
every one and still say something else: a negation moved into another clause
keeps the count, and two swapped numbers keep the set. A reported change can also
be harmless. A `preserved` verdict means no listed invariant moved, and that is
all it means. Read a rewrite against its original before you ship it.

## Protected spans cover what the patterns recognize

A protected span (code, math, a link, a citation, a quote, a freeze term) is
masked before the model sees the text and spliced back byte for byte, and a
rewrite that loses or reorders a placeholder is refused. That guarantee holds
whatever the model returns. It applies to the spans the patterns recognize. A
citation style or a link form outside those patterns reaches the model as prose,
where only the meaning guard checks it.

The guard knows where a span sits only by paragraph. A citation that moves to
another paragraph is refused when the rewrite keeps the paragraph count. A
citation, link, or code span that moves to another sentence in the same
paragraph passes, and so does one that moves while the rewrite merges or splits
paragraphs.

## Domain rules are phrase lists and formulas

The domain profiles run deterministic rules: phrase lists, length limits, and a
readability formula. Each one sees the surface of the text. A readability grade
comes from sentence length and estimated syllables, so a low grade shows short
words and sentences and says nothing about whether a reader understands the page.
The code review rules match phrases, so they miss a paraphrase and cannot read
tone or intent. The BCP 14 rules check how keywords are written, and they cannot
judge whether a requirement is right. The controlled-English profile is inspired
by controlled-language practice. It does not implement ASD-STE100 or any other
specification, and a clean result is no conformance claim.

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

## What leaves your machine

The checks, the LSP server, and the MCP tools `check`, `score`, and `compare`
make no network call; no module imports a network library, and a test enforces
it. Articulate has no telemetry. Only the editor commands send text out, to the
model backend you run (today the `claude` CLI under your own account), and they
mask code, math, links, citations, quotes, and freeze terms before the text
leaves. The prose around those spans does reach the backend, under that
backend's own terms.

## Content-free is not zero-leakage

A content-free audit receipt keeps no verbatim text: it drops the matched
substring and the exact offsets, and it keys the repeated-phrase and
repeated-opener notes by category, since their rule ids would name the phrase
or the opener. Which rules fired and the line remain, and for a
closed-vocabulary rule that narrows the flagged word to that rule's small, public
candidate set.

A project terminology rule is the extreme case. Its rule id names its term, as in
`terminology/banned/whitelist`, and a receipt made under a project config embeds
the project's term lists so it can be replayed. A content-free record of such a
check therefore shows which listed term appeared and on which line.

## Hash mode

A `--redact hash` receipt keeps a plain sha256 of each matched substring, for an
equality check against a string you already know. It is no confidentiality
measure: a holder can hash a rule's public vocabulary and recover the flagged
word. Use `--redact drop` when the word itself must stay secret.

## English patterns

The patterns are English literals, and so are the domain rule packs, the
meaning guard's word lists and the readability formula. On a non-English document they simply do not
fire, so an empty result on non-English text means the English rules found
nothing. It is never a verification of the text.
