# Articulate documentation

Articulate is a writing-quality and AI-tell detector that runs locally, plus an
optional editor. The detector flags the prose and formatting tells that make text
read as generated and scores how machine-textured a passage is. It runs on the
standard library with no network call, and a reviewer can reproduce every
detector verdict. The editor rewrites prose to a plain, skilled standard. It
sends the text to a hosted model through the `claude` CLI, and its output is a
suggestion that no receipt reproduces.

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

Articulate does detection and writing quality. It is not an evasion tool, it never
disguises machine authorship, and a receipt attests that a named ruleset ran and
re-derives, never that a result is correct or that a document meets a regulation.
The full statement is in [Boundaries](boundaries.md).
