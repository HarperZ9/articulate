# Features

Each section names what the feature gives you and how to reach it. For the exact
commands and flags, see the [CLI reference](cli.md). For what an output means and
never means, see [Boundaries](boundaries.md).

## The checks

The core reads prose and names patterns that cost a reader something, in three
tiers:

- HIGH: a narrow tier that blocks under most profiles: text left over from a chat
  interface (a reply opener that hands over a deliverable, a leaked interface
  token, a first-person line where a chat tool names itself) and a zero-width
  character hidden inside Latin text.
- MEDIUM: patterns with a cited reader cost, such as padded phrases, worn idioms,
  unsupported superlatives, throat-clearing openers, stacked hedges and appeals
  to unnamed studies. They block under a strict profile.
- LOW: notes that never block and expand only with `--verbose`.

Every rule that can block a writer who did not choose a house style carries a
one-sentence reader-cost reason and a published source. SARIF shows both in each
rule's help text. Every finding carries a line, an end line, a column and a
character span, and says whether it blocks under the profile in use.

The checks read a paragraph as one logical line, so the same text gives the same
findings whether you soft-wrap it or put one sentence per line, and every match
on a line counts. Headings, table rows, list items, block quotes, verse and
screenplay lines keep their own lines. A C2PA text manifest (Annex A.8 or A.9)
is blanked before any rule runs, so a credential raises nothing.

`check` reports the findings and the gate, `ok` or `blocked`. That is the only
pass-or-block signal. `findings` says only whether any HIGH or MEDIUM finding
exists. `score` reports per-rule counts and density per 1,000 words, counted
over blocking findings with a cited reason, with an exact Poisson interval, shown
at 250 words or more. No output carries a 0 to 100 score or a verdict about the
text.

## The house style

One writer's standard lives in a house pack: the em dash in every form, the
contrast devices (`not X but Y`, a trailing `, not Y`, `never ... always`), the
intensifiers, corporate verbs, register word lists and jargon, ordinal
enumeration, stock transitions, closers, cadence beats, and the stock phrases of
email, blog and marketing hooks. Only the `house` and `house-essay` profiles block
on it; every other profile reports those findings at LOW with `house: true`. No
path rule resolves to a house profile. A project opts in with `--profile house`
or a `writing-profile: house` tag. This repository checks its own docs that way.

## Profiles

A profile is a register configuration expressed as data. It sets its gate level,
a list of terms of art that never raise a finding, and whether the house pack
applies. The gate level `off` blocks nothing, for narrative where authorial voice
governs. `flavored` blocks the HIGH tier, for docs and research. `strict` blocks
HIGH and MEDIUM, for procedures, commits and essays. A profile resolves from an
explicit flag, an in-file `writing-profile:` tag, or the file path; `.tex` files
and `essays/`, `blog/` and `writing/` paths resolve to `essay`, which holds no
house pattern.

## Writing modes

A mode crosses a domain register with an articulation need: explain, persuade,
instruct, narrate, argue or prove. A mode is a base profile plus a small delta:
terms of art to keep, categories to block under a lenient base, and editor
guidance. Run `articulate modes` for the list.

## The genre axis

`literary-fiction`, `genre-fiction`, `ya-fiction`, `memoir`, `screenplay` and
`poetry` read by their own convention. Under a fiction genre quoted speech is
masked, craft devices report without blocking, and a report-only list names stock
fiction phrases. Screenplay classifies Fountain roles first. Poetry reads by the
line.

## Science and mathematical writing

`academic/prove` and `science-writing/explain` target technical exposition. On a
`.tex` file `fix` and `polish` mask every math span before each model call and
splice each span back byte for byte; a rewrite that drops or repeats a masked span
is refused. The proof mode does not rewrite by default. An ok gate says nothing
about whether a theorem is true.

## The editor layer

- `judge` reads judgment-level failures: a fluent paragraph with no fact a reader
  could restate, vague abstraction, hedging with no position, a weak verb.
- `fix` rewrites so the intended reader can follow the text on one read,
  preserving every number, name, citation, term of art and code span, then
  re-checks the rewrite under the same profile.
- `polish` keeps a pass only when `accept()` allows it: no quality score falls,
  the gate does not go from ok to blocked, and no required advisory opens.

The house writing standard reaches the model only under a house profile. No
instruction names an outside score, a sentence-length target or a vocabulary
level, and plain words stay welcome. The document is treated strictly as data: a
trust boundary ends every instruction, and a directive inside the text is edited
as content and never obeyed.

## The process record

`articulate process` keeps a local log of your own process in
`.articulate/process/` beside the document, with a `.gitignore` of its own.
Nothing records until you run a command.

- A draft entry holds a salted commitment to the text, its sequence and the day.
  Word counts, lines changed, times and snapshots are opt-in per log and stay out
  of a default export.
- Notes, sources, declared tool assistance (generated, drafted, edited,
  translated), reviews by role, anchors to a git commit or a timestamp token, and
  a continuation entry for a log that broke.
- How you put words down (dictation, a screen reader, switch access, drafting in
  another language) is a private entry kind. No export or statement includes it
  unless you name it.
- `export` writes `<document>.process-summary.json`: two labelled document hashes,
  the entry sequence, a C2PA-shaped actions list with IPTC digital source types,
  your disclosure statement and the limits of what the summary shows. `--reveal N`
  attaches draft N's text and salt, and `verify` checks each reveal and the chain.
- `fix` and `polish` add their own assistance entry when the document has a log.

## Disclosure statements

`articulate disclose` writes a statement from the log: assistance with the task
verb as recorded, and CRediT credit for people only. It refuses a claim that no
tool was used when the log records assistance, refuses to leave out a recorded
assistance entry, and never lists a model as an author. A `pip` template writes
`Assisted-by:` lines and never a co-author trailer for a model.

## The review desk

`articulate desk` prepares the questions a reviewer should ask. Inside the
document it asks about numbers with no source nearby, appeals to unnamed
authority, sections or statements a venue asks for, and text that does not show
to a reader. Across the field it asks five fixed questions about what the work
adds, and quotes only the authors' own claims beside them. It prints no score,
no verdict, no ranking and no question count, and it never reads a process record.
`--author` asks the same questions before submission.

## Re-derivable receipts

A receipt records the findings and the gate with the exact text hash and a
fingerprint of the whole ruleset, including the scanner's constants and the
house pack. Anyone replays it with no network. The replay result is `Match`,
`Drift` or `Unverifiable`, with no trusted or approved value. A content-free
receipt drops the matched text and the exact offsets. `articulate audit` queries
committed receipts locally and can re-verify each against its source.

## The fairness harness

`python -m articulate.fairness MANIFEST` runs the checks over a hash-checked
corpus under every profile a writer can land on without choosing it, and writes a
content-free receipt with block rates by group, both gap directions, per-rule
skew states and a layout check. `--release-check` fails a ruleset release when
the committed receipt is missing, a gate fails, or a bound profile is absent.
The results so far are in the [fairness audit](fairness-audit.md).

## Binary inputs fail closed

A binary or an unsupported document (a `.docx`, a PDF, an image) is refused with
an explicit reason. A UTF-8 non-English document is screened; the English
patterns simply do not fire on it.

## Surfaces

- CLI: `check`, `score`, `receipt`, `verify`, `audit`, `modes`, `process`,
  `disclose` and `desk`.
- LSP server: inline diagnostics in VS Code, JetBrains through LSP4IJ and Neovim.
- SARIF for GitHub code scanning, Azure DevOps and reviewdog.
- Two MCP servers that share one description table: `articulate-mcp` from a bare
  install, and `articulate.mcp_server` under the `[mcp]` extra.
- A GitHub Action and a pre-commit hook.

## The benchmark

`python -m articulate.bench` is an expected-findings regression: each text in
`corpus/patterns/` must still raise the categories `expect.json` lists, and each
public text in `corpus/control/` must raise no blocking finding. It sets no
target on text from any source.
