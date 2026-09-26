# Articulate

![Articulate: local prose checks, named and located. Lines of prose bow around a verified core, one span is marked as drift, and the replay lattice reads Match, Drift, Unverifiable.](assets/articulate-hero.svg)

Local prose checks: named writing patterns, where they occur, and what each
costs a reader. The checks run on your machine with no network call and the
standard library only. An optional editor rewrites for your reader through the
`claude` CLI, which sends the text to a hosted model.

No Articulate output shows who or what wrote a text, and no finding is a basis
for an accusation. Read [the boundaries](docs/boundaries.md#no-output-is-an-authorship-finding)
before you rely on any output.

## What it does

- **Check.** Each finding names a rule, its span and its tier. A rule that can
  block a writer carries a one-sentence reader-cost reason with a published
  source. The gate says `ok` or `blocked` under the profile in use, and that is
  the only pass-or-block signal. `score` reports per-rule counts and density per
  1,000 words with an exact interval, shown at 250 words or more.
- **Stay fair by default.** One writer's house style (the em dash, contrast
  devices, intensifiers, stock transitions and similar patterns) blocks only
  under the `house` or `house-essay` profile, which you choose. Every other
  profile reports those patterns as notes. The [fairness audit](docs/fairness-audit.md)
  shows the before and after on learner, college and academic texts, including
  the gate that still fails.
- **Adapt by register, mode and genre.** Profiles (procedure, commit, research,
  readme, essay, narrative and more) set which findings block. Writing modes
  such as `memo/argue` and genres such as `memoir`, `screenplay` and `poetry`
  read each kind of writing by its own convention.
- **Edit for the reader.** `judge` reads judgment-level failures. `fix` and
  `polish` rewrite so the intended reader can follow the text on one read, and
  accept a pass only when no quality score falls and the gate stays ok. No
  instruction names an outside score, a sentence-length target or a vocabulary
  level.
- **Keep your own process record.** `articulate process` keeps a local,
  opt-in log of your drafts as salted commitments, with order and day only by
  default, and exports a process summary you control. `articulate disclose`
  writes a statement of tool use from it.
- **Prepare a reviewer's questions.** `articulate desk` lists the questions a
  reviewer should ask, inside the document and across the field, with no score,
  verdict or ranking.
- **Replay a screening.** A receipt pins the text hash and the ruleset
  fingerprint, so anyone can re-derive the same findings.

## Use

```bash
# check (exit 1 when blocked under the file's profile)
python -m articulate.cli check path/to/doc.md --gate
python -m articulate.cli check essay.md --profile house-essay --verbose
echo "some prose" | python -m articulate.cli score

# receipt: a re-derivable screening (Match / Drift / Unverifiable)
python -m articulate.cli receipt doc.md --profile research > doc.receipt.json
python -m articulate.cli verify doc.receipt.json doc.md   # exit 0/1/2
python -m articulate.cli receipt doc.md --redact drop > receipts/doc.json   # content-free
python -m articulate.cli audit receipts/ --reverify --gate

# SARIF for CI; each rule's help text carries its reason and the does-not-prove line
python -m articulate.cli check docs/*.md --sarif > articulate.sarif

# your process record, and a statement of tool use from it
python -m articulate.cli process init essay.md
python -m articulate.cli process draft essay.md
python -m articulate.cli process export essay.md --reveal 2
python -m articulate.cli disclose essay.md --contributions contributions.json

# a reviewer's questions
python -m articulate.cli desk paper.md --venue paper

# the fairness harness on a corpus manifest you hold
python -m articulate.fairness manifest.json --out receipt.json

# editor, LSP server, benchmark, MCP servers
python -m articulate.editor --polish draft.md --mode memo/explain
python -m articulate.lsp_server
python -m articulate.bench
articulate-mcp
```

## Documentation

[Getting started](docs/getting-started.md), a [walkthrough](docs/walkthrough.md),
the [feature reference](docs/features.md), the [CLI reference](docs/cli.md), the
[fairness audit](docs/fairness-audit.md) and the [boundaries](docs/boundaries.md).

## Scientific and mathematical writing

`academic/prove` and `science-writing/explain` target technical exposition. The
proof mode does not rewrite by default, because a wrong change to a quantifier
order or an inequality direction changes a theorem. On a `.tex` file `fix` and
`polish` mask every math span before each model call and splice each span back
byte for byte; a rewrite that drops or repeats a masked span is refused. An ok
gate or a `Match` receipt says nothing about whether a theorem is true.

## Privacy

The checks, receipts, process record and desk never touch the network. The
editor layer (`judge`, `fix`, `polish`, `review`) has one backend today, the
`claude` CLI, which sends the full text to a hosted Anthropic model, so do not run
it on text you may not upload. A content-free receipt drops the matched text and
exact offsets; which rule fired and the line remain. The process log lives in
`.articulate/process/` beside your document with a `.gitignore` of its own, and
its salts never leave through an export.

## Status

Pre-1.0. Version 0.4.2 is on PyPI as `articulate-writing`; the changes on this
page are unreleased and listed in the [changelog](CHANGELOG.md). The fairness
harness has run on proxy corpora only. No arm yet covers adult academic writers,
dictated text, disabled writers or World Englishes, and the release gate for the
new ruleset does not pass on the corpus run so far.
