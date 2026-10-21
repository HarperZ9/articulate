# Articulate documentation

Articulate is a local writing-quality tool. It flags writing devices common in AI
output and in weak prose, scores how densely a passage uses them, and rewrites
prose to a plain, skilled standard. The core runs on the
standard library with no network call, and every verdict is one a reviewer can
reproduce.

## Read in this order

- [Getting started](getting-started.md): install, a first check, a first receipt,
  and an editor squiggle in about five minutes.
- [Walkthrough](walkthrough.md): a full pass over one document, from screening to
  a rewrite to a committed audit record a reviewer can replay.
- [Features](features.md): every capability, what it gives you, and how to reach
  it. The detector, profiles, modes, the genre axis, the science modes, the editor
  layer, receipts, per-span verdicts, the content-free audit receipt, and the
  surfaces.
- [CLI reference](cli.md): each command and every flag, with the exit codes.
- [Boundaries](boundaries.md): what a verdict and a receipt mean, and what they
  never claim. Read this before you rely on a receipt.

## The one boundary worth stating up front

Articulate is a style tool. It is not an authorship detector. On 183 texts of known
origin it flagged all 84 AI texts and also 57 of 75 human texts (76%, 95%
interval 65% to 84%), among them 10 of 18 essays by English learners. The
figures and their limits are in the
[known-provenance results](../corpus/provenance/README.md) and
[`results.json`](../corpus/provenance/results.json). Never use a finding to accuse a person of using AI, and never to
judge a student's work.

It is not an evasion tool, and a receipt attests that a named ruleset ran and
re-derives, never that a result is correct or that a document meets a regulation.
The full statement is in [Boundaries](boundaries.md).

- [Claude plugin](claude-plugin.md): local checks and host editing in Claude Code.
