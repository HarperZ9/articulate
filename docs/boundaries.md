# Boundaries

Articulate makes narrow claims on purpose. This page states what a verdict and a
receipt mean, and what they never mean. Read it before you rely on either.

## Not an authorship detector

Articulate is a style tool. It is not an authorship detector. On 183 texts of known
origin it flagged all 84 AI texts and also 57 of 75 human texts (76%, 95%
interval 65% to 84%), among them 10 of 18 essays by English learners. The
figures and their limits are in the
[known-provenance results](../corpus/provenance/README.md) and
[`results.json`](../corpus/provenance/results.json).

A finding, a verdict, a texture score or a per-paragraph flag names devices in the
text. None of them is evidence about who or what wrote it. Never use one to accuse
a person of using AI, and never to grade, discipline or judge a student. Learner
English was flagged at a lower rate than other student essays in this sample (10
of 18 against 31 of 36), but both rates are high and the sample is small.

## Writing quality, never evasion

Articulate finds where prose uses a named device or breaks a plain-writing
standard, and it helps you rewrite to that standard. It is not a tool for slipping
past another detector. A detector score is never the target the tool optimizes
toward. The rewrite loop is gated on writing quality, and the benchmark
refuses to report a competitor-detector-evasion result as a feature.

## Exposition quality is not correctness

For a proof or a scientific paper, a clean gate, a low texture score, or a `Match`
receipt means the prose was screened under a named ruleset. It says nothing about
whether the theorem or the result is true. A clearly written proof can still be
false, and a false proof screens exactly as clean as a correct one, because
fluency shows that an author understood their own argument well enough to explain
it, and it never shows that the argument holds. Correctness is established by independent referee
review or a machine-checked formalization in a proof assistant such as Lean, Coq,
or Isabelle, by other people, on a longer timescale. Articulate has no role in
that verification step.

## A receipt attests a screening, not compliance

A receipt records that a named, fingerprinted ruleset ran against a specific text
and produced a specific verdict, and that the same screening re-derives on the
same text. That is the whole claim. A receipt is not a provenance attestation, not
a correctness claim, and not a regulatory or compliance artifact. It is not an EU
AI Act Article 50 marking, and it is not a C2PA content credential. The verdict
set is `Match`, `Drift`, or `Unverifiable`, with no trusted or approved value, so
a receipt cannot be read as a final determination against a person.

## Content-free is not zero-leakage

A content-free audit receipt keeps no verbatim text: it drops the matched
substring and the exact offsets. It is not information-free. Which rules fired and
the line remain, and for a closed-vocabulary rule that narrows the flagged word to
that rule's small, public candidate set. Store a content-free record when you must
retain a screening without the source text, and understand that the residual is
the rule and the line, and never the word.

## Hash mode

A `--redact hash` receipt keeps a plain sha256 of each matched substring, for an
equality check against a string you already know. It is not confidentiality.
Because most rules draw from a public, closed vocabulary, a holder can enumerate
that vocabulary and hash it to recover the flagged word. Use `--redact drop` when
the flagged word itself must stay secret.

## The tool abstains when it cannot tell

Below a 30-word floor there are too few tokens to call a text clean human writing,
so a device-clean short text reads `unverifiable` and the receipt makes no clean
claim. This is calibrated uncertainty, and it is deliberate. A banned device is
unambiguous at any length, so a short text with a device still reads `flagged`.

## English patterns, and an honest detection ceiling

The detector's patterns are English literals. A non-English document is screened,
and the patterns simply do not fire on it, so a clean result on non-English text
means the English rules found nothing, and it is never a verification of the text.

The detector reads devices, register, and structure with regular expressions. It
cannot read token probability, so a device-clean passage of machine writing can
score low. That is an honest ceiling, and it is why Articulate is a rule-based,
explainable signal and never a trained statistical classifier. A statistical
detector answers a different question, and the two are complementary.
