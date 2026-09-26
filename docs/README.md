# Articulate documentation

Articulate runs local prose checks: named writing patterns, where they occur, and
what each costs a reader. It runs on the standard library with no network call,
and a reviewer can reproduce every check. An optional editor rewrites for the
reader through the `claude` CLI, which sends the text to a hosted model; its
output is a suggestion that no receipt reproduces.

## Read in this order

- [Getting started](getting-started.md): install, a first check, a first receipt
  and an editor squiggle in about five minutes.
- [Walkthrough](walkthrough.md): one document from a first check to a receipt, a
  process record, a statement of tool use and a reviewer's questions.
- [Features](features.md): every capability, what it gives you and how to reach
  it.
- [CLI reference](cli.md): each command and every flag, with the exit codes.
- [Fairness audit](fairness-audit.md): how the rules treat learner, college and
  academic writing, before and after ruleset 0.7.0, with the gates that pass and
  the ones that do not.
- [Boundaries](boundaries.md): what each output means and never means. Read this
  before you rely on any of them.

## The one boundary worth stating up front

No Articulate output shows who or what wrote a text, and no finding, count,
receipt, process record or desk question is a basis for an accusation. The tool
aims at the reader and never at an outside score. The full statement is in
[Boundaries](boundaries.md).
