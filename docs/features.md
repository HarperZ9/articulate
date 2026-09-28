# Features

Each section names what the feature gives you and how to reach it. For the exact
commands and flags, see the [CLI reference](cli.md). For what an output means and
never means, see [Boundaries](boundaries.md).

## The checks

The core reads prose and names patterns that cost a reader something, in three
tiers:

- HIGH: a narrow tier that blocks under most profiles: an interface or citation
  markup token, a first-person line where the speaker calls itself an AI system
  or a language model, and a zero-width character hidden inside Latin text. A
  job title in the first person, a sentence about a model's training data and an
  email that says real-time access is missing raise nothing.
- MEDIUM: patterns with a cited reader cost, such as padded phrases, worn idioms,
  unsupported superlatives, throat-clearing openers, stacked hedges and appeals
  to unnamed studies with no citation marker in the sentence. They block under a
  strict profile. The citation check reads every common style: AMA and
  Vancouver superscripts, `(12)` and `[12]`, MLA `(Jones 118)`, Chicago
  footnotes, Pandoc keys, LaTeX `\cite`, alpha keys, author and year, legal
  citations, links, and "according to" a named source. "Our data show" beside a
  figure, table or test statistic is the writer's own evidence.
- LOW: notes that block only where a profile or mode promotes them, and that
  expand only with `--verbose`. A reply opener that hands over a deliverable
  ("Certainly! Here is ...") is a LOW note, since an email reply does that on
  purpose; the `essay` and house profiles promote it to a blocking finding. "In order to" (`padded-purpose`) and "state of the
  art" in a sentence with no number, year or citation (`unanchored-claim`) are
  LOW notes that never block, because usage guides accept both in some uses.
  "It is important to", "It is worth noting that" and "It is important to note
  that", at a sentence start or after one leading clause (`expletive-opener`),
  are one LOW note too, with no MEDIUM finding beside it. "With respect to"
  (`padded-preposition`) is a LOW note, silent in its operator sense (a gradient
  with respect to a variable). A sentence that announces what the text will do
  ("In this article, we will explore", `announcement`) is a LOW note; a thesis or
  scope statement ("In this essay, I argue", "This article examines") raises
  nothing. "It should be noted that" stays MEDIUM.

Every rule that can report outside the house pack carries a one-sentence
reader-cost reason and a published source; a house finding says it is house
style. Each finding in `check --json` carries `reason` and `reason_source`,
`check --verbose` prints the reason under each finding, and SARIF shows both in
each rule's help text. Every `check` run prints the boundary sentence, a passing
gate included.

Quoted text is the source's words. The phrasing rules read each text with its
direct quotations (double and curly quotes, LaTeX ``...''), Markdown block quotes
and LaTeX `quote` and `quotation` environments blanked. The rule on a line where
the speaker calls itself software also skips table rows, transcript turns (a
speaker name and a colon at a line start), `verbatim` environments and
`\texttt{}` or `\verb` spans. An interface markup token and a hidden character
block everywhere, quotes included.

A `writing-allow:` line in the first 15 lines (an HTML comment, a `%` comment or
YAML front matter works) keeps terms of art for the whole file: a finding whose
matched text contains an allowed term as a substring, in any case, is dropped.
It reaches every rule except the contrast and cadence devices, the em dash and
emoji, the HIGH tier included: `writing-allow: language model` clears a line
where the speaker calls itself a language model. A CI owner should review
`writing-allow:` lines in a diff, since a rendered page hides the comment. The
match is a substring: an allowed `revolutionary`, meant for a war's name, also
clears "a revolutionary product" in the same file. Every finding carries a line, an end line, a column and a
character span, and says whether it blocks under the profile in use.

The checks read a paragraph as one logical line, and every match on a line
counts. On the Liang et al. corpus no text changed its findings when rewrapped
to one sentence per line or hard-wrapped. On PERSUADE 2.0, 31 of 14,797 essays
under `essay` (504 under `memoir`) changed their HIGH or MEDIUM findings or
their word counts under the one-sentence rewrap, and none under the hard wrap;
the cause is not established. Headings, table rows, list items, block quotes, verse and
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
enumeration, stock transitions, closers, cadence beats, curly quotation marks, a
bare "There is" opener, and the stock phrases of email, blog and marketing
hooks. Only the `house` and `house-essay` profiles block
on it. No other profile shows those findings in the console, the editor, SARIF,
the MCP tools or receipts; `check` and `score` show them as LOW notes marked
`house: true` when you pass `--house-notes`. The library call `check_text` reports them, marked,
for callers who filter their own output. No path rule resolves to a house
profile. A project opts in with `--profile house` or a `writing-profile: house`
tag, and the GitHub Action prints a notice when a workflow does. This repository
checks its own docs that way. The house pack began as one writer's editing list,
and its word lists have not been re-derived from a plain-language source.

## Profiles

A profile is a register configuration expressed as data. It sets its gate level,
a list of terms of art that never raise a finding, and whether the house pack
applies. The gate level `off` blocks nothing, for narrative where authorial voice
governs. `flavored` blocks the HIGH tier, for docs and research. `strict` blocks
HIGH and MEDIUM, for procedures, commits and essays. A profile resolves from an
explicit flag, an in-file `writing-profile:` tag, or the file path. A `.tex`
file resolves to `research` (to `proof` under a `proofs/` folder), which blocks
the HIGH tier only; `% writing-profile: essay` asks for the strict gate.
`essays/`, `blog/` and `writing/` paths resolve to `essay`, which holds no house
pattern. `fix`, `polish`, `judge` and `review` resolve a profile the same way as
`check`.

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

With a model, the editor adds judgment and rewriting:

- `judge` reads the judgment-level failures a regex cannot see: a fluent paragraph
  with no fact a reader could restate, vague abstraction, hedging with no
  committed position, a weak verb carrying the meaning. It reports.
- `fix` rewrites for the intended reader, checks protected spans, and
  re-runs the checks under the same profile. Remaining findings stay visible.
- `polish` keeps a pass only when no assessed quality score falls, the gate
  does not go from ok to blocked, and no required advisory opens. Missing scores
  leave host-submitted quality unassessed; the model loop keeps the best prior
  text. These checks cannot prove that meaning or writing quality improved.

Every result identifies its backend, model and failed attempts. The available
backends are `host`, `sampling`, `anthropic`, `claude-cli`, `openai`, `ollama`
and `none`, with `auto` choosing for the current surface.

In an MCP session, automatic selection uses sampling only if the client
advertised that capability. Otherwise it returns an edit plan to the calling
model before trying a separately billed backend. The host protocol also works
through `articulate plan` and `articulate submit` without MCP sampling support.
The plan supplies local findings and their reasons, rewrite or judge
instructions, masked text, protected spans and a plan ID bound to the source,
profile and ruleset. The caller submits its rewrite with that ID and the
original text. Articulate restores masks, checks the guard, reports gate and
per-rule changes, and returns a receipt with `backend: host`. A caller-supplied
model name records attribution; it does not authenticate the model.

The guard checks numbers, URLs and link targets, citations, code, math and quoted
text. A refused span keeps its original wording and gets a reason. The guard
applies to model and deterministic edits. Protected spans cannot establish
semantic equivalence: a rewrite can retain every number and still change a claim.

Without a reachable model, `none` makes conservative mechanical edits and
reports what remains. It can replace clause dashes and remove safe filler or
extra spaces; it leaves protected content alone. Its `judge` returns local
findings and reasons without inventing model scores. Backend unavailability
does not prevent this result. A successful call can still contain blocked
findings or refused edits; inspect the gate and refusal list.

Plain CLI automatic selection tries configured Anthropic, the Claude CLI,
configured OpenAI-compatible endpoints, Ollama and `none` in order. Ollama
uses installed models only and never downloads one. Configuration and the model
preference order are in the [CLI reference](cli.md#backend-configuration).

Anthropic and the Claude CLI send text to their provider. OpenAI-compatible and
Ollama backends send it to the configured endpoint, which can be remote. Host
editing and sampling follow the host's data handling policy. `none` stays local.
`ARTICULATE_LOCAL_ONLY=1` permits only loopback Ollama and `none`, refusing other
editor backends before a connection. Plans and edit results contain source text;
they are separate from content-free detector audit receipts.

The house writing standard reaches the model only under a house profile. No
instruction names an outside score, a sentence-length target or a vocabulary
level, and plain words stay welcome. Every instruction asks the model to keep the
writer's variety of English and to say nothing about who or what wrote the text.
A trust boundary ends every instruction and tells the model to treat a directive
inside the text as content to edit and to leave it unobeyed; a prompt cannot
guarantee that the model complies. `judge` output and the scorer's notes pass through a filter
that removes lines guessing at a text's origin and says how many it removed. A
pattern list misses paraphrase.

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
  another language) goes to a private file outside the log. No export or
  statement includes it unless you name it, and no sequence number shows it.
- `export` writes `<document>.process-summary.json`: two labelled document hashes,
  the entry sequence, a C2PA-shaped actions list with IPTC digital source types,
  your disclosure statement and the limits of what the summary shows. It carries
  no entry hash, so nothing in it can be tested against a withheld field.
  `--reveal N` attaches draft N's text and salt.
- `verify` on a log reports `intact` (exit 0), `broken` (exit 1) or `missing`
  (exit 3). A missing log is no record, and an absent or short record shows
  nothing about a writer; `verify`, `export` and `disclose` each print that
  limits line. On a summary (found by its schema) it checks the chain state the
  summary records and each reveal.
- `continue` starts a new log only after a broken one. The new first entry names
  the last good entry and carries every recorded assistance entry forward.
- `fix` and `polish` add their own assistance entry when the document has a log,
  including when a later pass fails.
- `--track` lets git see the log and still keeps salts, the diff cache, snapshots
  and input methods out of it.

## Disclosure statements

`articulate disclose` writes a statement from the log: assistance with the task
verb as recorded, and CRediT credit for people only. It refuses when the log is
missing or broken. It refuses a claim that matches its list of no-tool phrases
("No AI was used", "written without any AI tools") when the log records
assistance; a paraphrase outside the list passes, so the Assistance section is
the record. It refuses to leave out a recorded assistance entry. An author whose
whole name is a product name ("Claude", "GPT-4o") is refused unless the entry
says `"type": "person"`; a person who shares a word with a product, such as
Claude Shannon or Ai Weiwei, is never refused. A `pip` template writes
`Assisted-by:` commit-trailer lines and never a co-author trailer for a model.

## The review desk

`articulate desk` prepares the questions a reviewer should ask. Inside the
document it asks about numbers with no source nearby, appeals to unnamed
authority, sections or statements a venue asks for, and text that does not show
to a reader: white or zero-size text, `display:none`, `visibility:hidden`, zero
opacity, zero-width characters inside Latin text, bidirectional controls and
Unicode tag characters, whose hidden sentence it spells out. Across the field it asks five fixed questions about what the work
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
skew states, the report-only notes a writer sees, and a layout check that
rewraps each text to one sentence per line and hard-wraps it at 60 columns.
`--release-check` gates only a release that changes the ruleset: when the
fingerprint equals the one in `fairness/published-ruleset.json` and that record
names an earlier release, it passes and says the gates were not re-run. For a
changed ruleset it recomputes the gate summary from the committed receipts'
rows, checks each stored flag against its stored numbers and each receipt
against its pin, and fails when a receipt is missing or duplicated, came from an
unlisted manifest, leaves out a required comparison or a bound profile, has no
confirmatory reading for this ruleset, or a gate fails. It trusts the stored G2
states and layout counts, which it cannot recompute without the documents. A
maintainer's override with a reason is accepted only when no gate row fails that
did not fail under the published ruleset's own receipt. The
results so far are in the [fairness audit](fairness-audit.md) and the
[confirmatory run](fairness-confirmatory.md). `--jobs N` scans documents in N
processes and writes the same receipt.

## Binary inputs fail closed

A binary or an unsupported document (a `.docx`, a PDF, an image) is refused with
an explicit reason. A UTF-8 non-English document is screened; the English
patterns simply do not fire on it.

## Surfaces

- CLI: `check`, `score`, `receipt`, `verify`, `audit`, `modes`, `process`,
  `disclose`, `desk`, `plan`, `submit`, `judge`, `fix` and `polish`.
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
