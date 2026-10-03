# Features

Each section names what the feature gives you and how to reach it. For the exact
commands and flags, see the [CLI reference](cli.md). For what a verdict and a
receipt mean, see [Boundaries](boundaries.md).

## The deterministic detector

The core reads prose and flags the tells that make text read as generated, in
three confidence tiers:

- HIGH: banned rhetorical devices (antithesis, corrective negation, the triad,
  negative parallelism, em-dashes) and named register words. These are hits.
- MEDIUM: strong tells of current frontier-model prose, the stock transitions,
  the marketing superlatives, the participial closers, the email and blog tells.
- LOW: advisories that catch a real pattern and also fire on innocent prose, so
  they never block and expand only with `--verbose`.

It also carries keyword-free detection for a parallel-negation contrast pair, and
document-level signals for uniform cadence, repeated sentence openers, passive
density, and adverb density. Every finding carries a line, a column, and a
character span, so an editor can place a squiggle and a receipt can pin the exact
location.

Alongside the pass or fail gate, it emits a graded 0 to 100 texture score that
accumulates weak evidence by density. The score is a signal for grading and for
the benchmark, and it never changes the clean or flagged verdict.

## Register profiles

A profile is a register configuration expressed as data. It sets which detector
tiers block, a list of terms of art the detector never flags, and provenance
fields. The shipped profiles cover procedures, commits, error messages,
changelogs, release notes, API docs, specs, research, proofs, model cards,
readmes, legal text, journalism, social copy, chat, essays, and narrative.

The gate follows a slop level. `off` blocks nothing, for narrative where authorial
voice governs. `flavored` blocks the HIGH device tier, for docs and research.
`strict` blocks HIGH and MEDIUM, for procedures and essays that must be device
free. A profile resolves from an explicit flag, an in-file `writing-profile:` tag,
or the file path.

## Writing modes

A mode crosses a domain register with an articulation need, what the prose does to
the reader: explain, persuade, instruct, narrate, argue, or prove. A mode is a
base profile plus a small delta: terms of art to keep, categories to block even
under a lenient base, and editor guidance. Run `articulate modes` for the list.

A mode tunes style within the plain-writing standard. It may tighten the gate and
add terms of art. It may not re-enable a banned device on prose, with the single
exception of literary narrative, where nothing gates.

## The genre axis

Narrative and expressive prose read by their own convention, so a scanner tuned
for an essay misreads a novel. The genre axis adds `literary-fiction`,
`genre-fiction`, `ya-fiction`, `memoir`, `screenplay`, and `poetry`. Under a
fiction genre:

- Quoted speech is masked out of the device passes, so a character's line is
  never scored as the author's own prose.
- The craft devices report without blocking, because voice governs.
- A report-only lexicon flags generation artifacts, such as the somatic cliche or
  the "could not help but" reflexive. It never gates.

Screenplay classifies Fountain roles first, so only action lines face the device
gate and dialogue keeps the character's voice. Poetry reads by the line, and the
craft-device categories drop from its report, because they name legitimate
technique in verse.

## Science and mathematical writing

`academic/prove` and `science-writing/explain` target hard technical exposition:
stating the idea before the formalism, keeping a roadmap, defining each symbol
once. On a `.tex` file the editor masks every math span before a rewrite and
splices it back byte for byte, so a formula is never altered. The proof mode does
not rewrite by default, because a wrong change to a quantifier order or an
inequality direction changes a theorem; it routes to the judge, and the fix loop
is opt-in.

The boundary here is fixed and load-bearing: a clean gate or a passing receipt
means the prose was screened. It says nothing about whether the theorem is true.
A clear proof can still be false, and this tool never checks the mathematics.

## The editor layer

With a model, the editor adds judgment and rewriting:

- `judge` reads the judgment-level failures a regex cannot see: a fluent paragraph
  with no fact a reader could restate, vague abstraction, hedging with no
  committed position, a weak verb carrying the meaning. It reports.
- `fix` rewrites to a plain, skilled standard, checks protected spans, and
  re-runs the detector. Remaining findings stay visible.
- `polish` runs a monotonic loop that accepts a pass only when the gate stays
  clean and no assessed quality score drops. Missing scores leave host-submitted
  quality unassessed; the model loop keeps the best prior text. These checks bound acceptance;
  they cannot prove that the meaning or writing quality improved.

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

An edit can allow named kinds of protected change, such as a number it is meant
to update (`--allow-change number`, or `allow_change` on the MCP `fix`,
`polish` and `edit_plan` tools). An allowed change is reported in
`allowed_changes` in the result and the editor receipt; it is never accepted in
silence. The plan binds the allowed kinds (plan schema
`articulate/edit-plan/v3`), so a submission cannot widen them, and v1 and v2
plans still verify. Disclosure lines, an added first-person sentence, HTML and
math can never be allowed.

A change report (`--explain` on `fix`, `polish` and `submit`, or `explain` on
the MCP `fix`, `polish` and `edit_submit` tools) pairs each changed sentence
with its original and lists the findings it cleared, kept or added, the
paragraphs the guard kept and why, and every allowed change. It shows what the
checker saw in each sentence; it does not show why the editor made a change or
that the meaning held.

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

The document is treated strictly as data. A trust boundary is appended to every
model call, so a directive embedded in the text (a line that says to ignore the
standard or to reply approved) is edited as content and never obeyed. The rewrite
optimizes writing quality, and it never tunes prose toward a lower detector score.

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

A receipt records a detection result together with the exact text hash and a
fingerprint of the whole ruleset. Anyone replays it: recompute the findings on
the same text under the same ruleset and confirm they match, with no network and
no trust in whoever issued it first. The verdict uses a closed set of three:

- `Match`: same text, same ruleset, identical findings and gate.
- `Drift`: same text and ruleset, but the re-derived findings differ.
- `Unverifiable`: the ruleset moved, the text hash mismatches, or the text is
  below the signal floor. Re-derivation cannot be done, so nothing is asserted.

There is deliberately no trusted or approved value. The receipt certifies
re-derivability, and the issuer's identity is not load-bearing.

## Per-span mixed-authorship

`--spans` scores each paragraph on its own and reports its line range, so a single
generated paragraph in an otherwise clean document is flagged in place, and one
aggregate score cannot smear across the whole file. A per-span receipt records the
per-block verdicts, each with its own text hash.

## Sub-threshold calibration

Below a 30-word floor there are too few tokens to call a text clean human writing,
so a device-clean short text reads `unverifiable` and the receipt abstains rather
than emit a confident verdict on noise. A banned device is unambiguous at any
length, so a short text with a device still reads `flagged`.

## The content-free audit receipt

For a team that must retain a record without keeping the sensitive text, a
content-free receipt drops the matched substring and the exact offsets, and keeps
only which rule fired, its tier and category, and the line. It still replays to
`Match`, and `verify` rejects a mislabeled or a smuggling receipt. The `articulate
audit` command queries a directory of committed receipts locally, and with
`--reverify` it re-checks that each still holds against its source, failing the
gate only when a source drifted or changed since it was screened.

A content-free record is not zero-leakage. Which rules fired and the line remain,
which for a closed-vocabulary rule narrows the flagged word to that rule's small
public candidate set. Read [Boundaries](boundaries.md) before you rely on it.

## Binary inputs fail closed

A binary or an unsupported document (a `.docx`, a PDF, an image) is refused with
an explicit reason, so the tool never returns a spurious clean scan of a lossy
decode. A UTF-8 non-English document is screened, not refused; the patterns are
English literals, so they simply do not fire on it.

## Surfaces

The same detection reaches you through several surfaces:

- CLI: `check`, `score`, `receipt`, `verify`, `audit`, `modes`, `process`,
  `disclose`, `desk`, `plan`, `submit`, `judge`, `fix` and `polish`, plus the
  `house`, `voice`, `corpus`, `titles`, `interview` and `restructure` commands.
- LSP server: inline squiggles in VS Code, JetBrains through LSP4IJ, and Neovim.
  It is standard-library only, with no dependency.
- SARIF: `check --sarif` for GitHub code scanning, Azure DevOps, and reviewdog.
- MCP server: the detector and editor as tools for an agent.
- GitHub Action and a pre-commit hook, wired to gate a change and to re-verify
  committed receipts.
- A VS Code client in `editors/vscode/` and a JetBrains note in
  `editors/jetbrains/`.

## The benchmark

Quality is measured, not asserted. `articulate.bench` runs the detector over a
labeled corpus and reports recall on the AI-authored samples, specificity on the
human-authored samples, and a count of regressions. The exit code is the number
of misclassified files, so a checker can gate on it.
