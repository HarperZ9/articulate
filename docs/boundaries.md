# Boundaries

Articulate makes narrow claims on purpose. This page states what a verdict and a
receipt mean, and what they never mean. Read it before you rely on either.

## Detection and writing quality, never evasion

Articulate finds where prose reads as machine-written or breaks a plain-writing
standard, and it helps you rewrite to that standard. It is not a tool for slipping
past another detector, and it never disguises machine authorship. A lower detector
score is a byproduct of clearer writing, and it is never the target the tool
optimizes toward. The rewrite loop is gated on writing quality, and the benchmark
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

A project terminology rule is the extreme case. Its rule id names its term, as in
`terminology/banned/whitelist`, and a receipt made under a project config embeds
the project's term lists so it can be replayed. A content-free record of such a
check therefore shows which listed term appeared and on which line.

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
