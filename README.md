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
- **Measure fairness in the open.** One writer's house style (the em dash,
  contrast devices, intensifiers, stock transitions and similar patterns) blocks
  only under the `house` or `house-essay` profile, which you choose, and no other
  profile shows it unless you ask with `--house-notes`. On the Liang et al.
  corpus the default profile blocks none of 306 human texts, the strict `essay`
  profile blocks 5 of them, and every release gate passes; the rules were tuned
  on that corpus, so that pass is exploratory. On the held-out corpus, 14,797
  school essays from PERSUADE 2.0, the default profile again blocks none, and
  the pre-registered release gate fails: the strict profiles block 14.0% of the
  essays by writers not recorded as English learners and 6.0% of the learner
  essays, and some essays change findings when rewrapped. The
  [fairness audit](docs/fairness-audit.md) and the
  [confirmatory run](docs/fairness-confirmatory.md) have the numbers with
  intervals.
- **Adapt by register, mode and genre.** Profiles (procedure, commit, research,
  readme, essay, narrative and more) set which findings block. Writing modes
  such as `memo/argue` and genres such as `memoir`, `screenplay` and `poetry`
  read each kind of writing by its own convention.
- **Edit for the reader.** `judge` reads judgment-level failures. `fix` writes
  each rewrite and re-checks it. `polish` keeps a pass only when no quality score
  falls and the gate does not go from ok to blocked. No instruction names an
  outside score, a sentence-length target or a vocabulary level.
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

`academic/prove` and `science-writing/explain` target technical exposition. A
`.tex` file checks under `research`, which blocks only the HIGH tier; add
`% writing-profile: essay` in the first ten lines for the strict gate. "With
respect to" is a LOW note that never blocks under any profile. It stays silent
after a derivative, gradient, partial, integral, Jacobian, convex, continuous,
measurable, differentiable, integrable or invariant, and before a Greek letter, a
subscripted symbol (`w_i`), a math span (`$`, `\(`, `\[`) or a single-letter
variable other than "a". The proof mode does not rewrite by default, because a wrong change to a
quantifier order or an inequality direction changes a theorem. On a `.tex` file
`fix` and `polish` mask every math span before each model call and splice each
span back byte for byte; a rewrite that drops or repeats a masked span is
refused. An ok gate or a `Match` receipt says nothing about whether a theorem is
true.

## Quotations and citations

Quoted text is the source's words, so the phrasing rules skip it: direct
quotations in double or curly quotes, LaTeX ``...'', Markdown block quotes and
LaTeX `quote` and `quotation` environments. The rule on a line where the speaker
calls itself software also skips tables, transcript turns ("User:" at a line
start), `verbatim` and `\texttt{}` or `\verb` spans, so a reflection that pastes
a tool's reply, as many courses ask, does not block. An interface markup token
and a hidden character block everywhere, quotes included. A quotation mark
exempts only what it encloses, scare quotes too.

An appeal to unnamed studies reports unless its sentence carries a citation
marker in any common style: a superscript or a number after the period (AMA,
Vancouver), `(12)` or `[12]`, `(Jones 118)` (MLA), a footnote `[^5]`, a Pandoc
key `[@key]`, LaTeX `\cite`, an alpha key `[Smi20]`, an author and year, a legal
citation (`998 F.3d 101`, `[2021] UKSC 5`), a link or "according to" a named
source. "Our data show" counts as your own evidence beside a figure, table or
test statistic. A count such as "in 1200 patients" is not a citation.

## Keeping a term of art

A line such as `writing-allow: substrate, load-bearing` (inside an HTML comment,
a `%` comment or YAML front matter works) in the first 15 lines keeps those
terms. A finding whose matched text contains an allowed term, as a substring and
in any case, is dropped for the whole file. The contrast and cadence devices
ignore the list, since each is a sentence structure. The match is by
substring, so allowing `revolutionary` also clears "a revolutionary product" in
the same file; choose the narrowest term that works.

## Privacy

The checks, receipts, process record and desk never touch the network. Each
command either stays on your machine or sends the full text to a hosted model:

| Command | Where the text goes |
|:-|:-|
| `articulate check`, `score`, `receipt`, `verify`, `audit`, `modes` | Nowhere: local |
| `articulate process`, `disclose`, `desk`, the LSP server | Nowhere: local |
| `python -m articulate.fairness`, `python -m articulate.bench` | Nowhere: local |
| The `check` and `score` tools of both MCP servers | Nowhere: local |
| `python -m articulate.editor --judge`, `--review` (alias `--advise`): advice | A hosted model, through the `claude` CLI and the service it is set up to use |
| `python -m articulate.editor --fix`, `--polish`: rewrites | A hosted model, through the `claude` CLI and the service it is set up to use |
| The `judge`, `fix` and `polish` tools of both MCP servers | A hosted model, through the `claude` CLI and the service it is set up to use |

Set `ARTICULATE_LOCAL_ONLY=1`, or pass `--local-only` to `python -m
articulate.editor`, and every hosted command exits with code 3 before any
network call; the MCP tools return an error that names the switch. Any value
other than an empty one, `0`, `false`, `no` or `off` turns the switch on. The
editor command line prints that the full text leaves the machine before each
hosted run; the MCP tool descriptions say so, and their results do not repeat
it. Under a brief that allows only spelling and
grammar help, use the local commands: `judge` and `review` give structural
advice, which such a brief may exclude. Do not run the hosted commands on a
manuscript or grant application under review, on health records, or on unfiled
patent material. A content-free receipt drops the matched text and
exact offsets; which rule fired and the line remain. The process log lives in
`.articulate/process/` beside your document with a `.gitignore` of its own. A
default export carries no salt; `--reveal N` exports draft N's salt with its
text, and nothing else.

## Status

Pre-1.0. Version 0.5.0 is on PyPI as `articulate-writing`; the changes on this
page are unreleased and listed in the [changelog](CHANGELOG.md). The fairness
harness has run on proxy corpora only. No arm yet groups adult academic writers
by first language, and none covers dictated text, disabled writers or World
Englishes. The release gate for the new ruleset passes on the Liang et al.
corpus, which the rules were tuned on, and fails on the held-out PERSUADE 2.0
corpus, so a release that ships this ruleset is blocked
([confirmatory run](docs/fairness-confirmatory.md)). The gate runs only when a
release changes the ruleset.
