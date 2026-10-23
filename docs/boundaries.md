# Boundaries

This page states what a verdict and a receipt mean, so you can rely on each for
what it shows. Read it before you rely on either.

## A style tool

Articulate is a style tool. It is not an authorship detector. On 183 texts of known
origin it flagged all 84 AI texts and also 57 of 75 human texts (76%, 95%
interval 65% to 84%), among them 10 of 18 essays by English learners. The
figures and their limits are in the
[known-provenance results](../corpus/provenance/README.md) and
[`results.json`](../corpus/provenance/results.json).

A finding, a verdict, a texture score or a per-paragraph flag names devices in the
text, and says the same about a person's writing as about a model's. Use it to
edit. Accusing a person of using AI, or grading, disciplining or judging a
student, is outside what it can support. Learner English was flagged at a lower
rate than other student essays in this sample (10 of 18 against 31 of 36); both
rates are high and the sample is small.

## Writing quality is the target

Articulate finds where prose uses a named device or breaks a plain-writing
standard, and it helps you rewrite to that standard. The rewrite loop is gated on
writing quality for the reader. Detector scores, its own and other tools', play
no part, and the benchmark refuses to report a detector-evasion result as a
feature.

## Clear writing and correct results are checked separately

For a proof or a scientific paper, a clean gate, a low texture score, or a `Match`
receipt means the prose was screened under a named ruleset. A false proof screens
exactly as clean as a correct one: fluency shows the author can explain the
argument, and the argument's soundness is a separate check. Correctness comes
from independent referee review or a machine-checked formalization in a proof
assistant such as Lean, Coq or Isabelle.

## A receipt attests a screening

A receipt records that a named, fingerprinted ruleset ran against a specific text
and produced a specific verdict, and that the same screening re-derives on the
same text. That is the whole claim. For provenance, use a C2PA content
credential; for EU AI Act Article 50, use the marking that article requires. The
verdict set is `Match`, `Drift`, or `Unverifiable`, three statements about the
screening, so a receipt is the wrong basis for a final determination against a
person.

## What a content-free receipt keeps

A content-free audit receipt drops the matched substring and the exact offsets.
It keeps which rules fired and on which line, and for a closed-vocabulary rule
that narrows the flagged word to that rule's small, public candidate set. Store
a content-free record when you must retain a screening while discarding the
source text. What it reveals is the rule and the line.

## Hash mode

A `--redact hash` receipt keeps a plain sha256 of each matched substring, for an
equality check against a string you already know. Most rules draw from a
public, closed vocabulary, so a holder can hash that vocabulary and recover the
flagged word. Use `--redact drop` when
the flagged word itself must stay secret.

## The tool abstains on short texts

Below a 30-word floor a text is too short to call clean, so a device-clean short
text reads `unverifiable` and the receipt abstains. A banned device is
unambiguous at any length, so a short text with a device still reads `flagged`.

## English patterns and a rule-based ceiling

The detector's patterns are English literals. A document in another language is
screened, and a clean result there means the English rules came back empty.

The detector reads devices, register, and structure with regular expressions, so
a device-clean passage of machine writing can score low. Every finding names the
rule and the line that produced it. A trained statistical classifier answers a
different question, and the two are complementary.
