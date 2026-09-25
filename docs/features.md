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
once. On a `.tex` file both `fix` and `polish` mask every math span before the
model call, including in the detector summary the prompt quotes, and splice each
span back byte for byte. A rewrite that drops or repeats a masked span is refused,
so a formula is never altered. The MCP `fix` and `polish` tools do the same when
called with `is_tex: true`. Math in other file types, such as `$...$` in
Markdown, is not masked. The proof mode does
not rewrite by default, because a wrong change to a quantifier order or an
inequality direction changes a theorem; it routes to the judge, and the fix loop
is opt-in.

The boundary here is fixed and load-bearing: a clean gate or a passing receipt
means the prose was screened. It says nothing about whether the theorem is true.
A clear proof can still be false, and this tool never checks the mathematics.

## The editor layer

The editor adds the two things a detector cannot do:

- `judge` reads the judgment-level failures a regex cannot see: a fluent paragraph
  with no fact a reader could restate, vague abstraction, hedging with no
  committed position, a weak verb carrying the meaning. It reports.
- `fix` rewrites to a plain, skilled standard, preserving every number, name,
  citation, term of art, and code span, then re-runs the detector until clean.
- `polish` runs a monotonic loop that accepts a pass only when the gate stays
  clean and no quality score drops, so a rewrite never regresses.

The document is treated strictly as data. A trust boundary is appended to every
model call, so a directive embedded in the text (a line that says to ignore the
standard or to reply approved) is edited as content and never obeyed. The rewrite
optimizes writing quality, and it never tunes prose toward a lower detector score.

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

- CLI: `check`, `score`, `receipt`, `verify`, `audit`, and `modes`.
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
