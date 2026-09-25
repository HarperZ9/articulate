# Articulate

![Articulate: a local writing-quality and AI-tell detection and editing tool. Lines of prose bow around a verified core, one span is marked as drift, and the verdict lattice reads Match, Drift, Unverifiable.](assets/articulate-hero.svg)

A local writing-quality and AI-tell detection and editing tool. It flags the
prose devices and machine-writing tells that make text read as generated, scores
how machine-textured a passage is, and (with an LLM backend) rewrites prose to a
plain, skilled standard. The core runs standard-library-only with no network
call. Detection quality and writing quality are the goals; a detector score is a
benchmark and a byproduct, never something the tool optimizes toward, and it is
not an evasion tool.

## Documentation

Full docs are in [`docs/`](docs/): [getting started](docs/getting-started.md), a
thorough [walkthrough](docs/walkthrough.md), the [feature reference](docs/features.md),
the [CLI reference](docs/cli.md), and the [boundaries](docs/boundaries.md) that
say what a verdict and a receipt mean and what they never claim.

## What it does

- **Detect.** Flags banned rhetorical devices (antithesis including keyword-free
  parallel-negation contrast pairs, corrective negation, rule-of-three, em-dashes,
  filler intensifiers, corporate verbs), current frontier-model register,
  marketing, and email/blog tells, and Williams/Orwell signals (expletive openers,
  nominalization density, passive voice, adverb density, cadence uniformity,
  opener repetition). Emits a graded 0-100 texture score and a clean/flagged gate.
- **Adapt by register.** A profile system (procedure, commit, research, readme,
  essay, narrative, and more) sets which findings block. Fiction gates nothing;
  procedures and essays gate strictly. Profiles resolve from `--profile`, an
  in-file `writing-profile:` tag, or the file path.
- **Choose a mode or a genre.** A writing mode crosses a domain register with an
  articulation need, such as `memo/argue` or `technical-docs/explain`. The genre
  axis reads narrative and expressive prose by its own convention: `literary-fiction`,
  `genre-fiction`, `ya-fiction`, `memoir`, `screenplay`, `poetry`. Under a fiction
  genre, quoted speech is masked out of the device passes so a character's line is
  never scored as the author's prose; the craft devices report but never block; and
  a report-only lexicon flags generation artifacts such as the somatic cliche or the
  "could not help but" reflexive. Screenplay classifies Fountain roles first, so only
  action lines face the device gate. Poetry reads by the line and drops the
  craft-device categories from its report. Run `articulate modes` to list them.
- **Edit.** `judge` reads the judgment-level failures a regex cannot see
  (confident emptiness, vague abstraction, hedging with no position, weak verbs).
  `fix` rewrites to the standard, self-checked against the detector. `polish`
  loops until five qualities (concreteness, commitment, economy, rhythm, a
  restatable fact per paragraph) clear a bar. Gated on writing quality, never a
  detector score. Runs through the `claude` CLI, which sends the text to a
  hosted Anthropic model.

## Use

```bash
# lint (exit 1 when blocked under the file's profile)
python -m articulate.cli check path/to/doc.md --gate
python -m articulate.cli check essay.md --profile essay --verbose
echo "some prose" | python -m articulate.cli score

# library
python -c "import articulate; print(articulate.check_text('...', profile=articulate.profiles.load('research'))['gate'])"

# receipt: a re-derivable verdict (Match / Drift / Unverifiable)
python -m articulate.cli receipt doc.md --profile research > doc.receipt.json
python -m articulate.cli verify doc.receipt.json doc.md   # replay; exit 0/1/2

# content-free audit receipt: replayable, but stores no verbatim text (drop or hash
# the matched substring). For a team that must retain a record without the source.
python -m articulate.cli receipt doc.md --redact drop --reviewer alice > receipts/doc.json
python -m articulate.cli check doc.md --content-free --sarif > doc.sarif  # no substrings

# audit: query committed receipts locally (no server), and re-verify they still hold
python -m articulate.cli audit receipts/                 # recorded verdicts, blocked rules
python -m articulate.cli audit receipts/ --reverify --gate   # exit 1 if a source drifted

# SARIF for CI (GitHub Code Scanning, Azure, reviewdog)
python -m articulate.cli check src/**/*.md --sarif > articulate.sarif

# LSP server (inline squiggles in VS Code, JetBrains via LSP4IJ, Neovim). Stdlib
# only, no dependency. Point your editor's LSP client at:
python -m articulate.lsp_server

# benchmark (regression-gated corpus) and MCP server
python -m articulate.bench
python -m articulate.mcp_server
```

### Editor setup

The LSP server speaks standard LSP over stdio, so any LSP client can drive it.
A minimal Neovim registration:

```lua
vim.lsp.start({ name = "articulate", cmd = { "python", "-m", "articulate.lsp_server" },
  filetypes = { "markdown", "text", "tex" } })
```

For VS Code, a thin client that launches the same command as a `LanguageClient`
is all that is needed; no server code lives in the extension.

### Scientific and mathematical writing

`academic/prove` and `science-writing/explain` target hard technical exposition:
stating the idea before the formalism, keeping a roadmap, defining each symbol
once. The proof mode does not rewrite by default, because a wrong change to a
quantifier order or an inequality direction changes a theorem; it routes to
`--judge`, and `--fix` is opt-in. On a `.tex` file `--fix` and `--polish` mask
every math span before the model call, including in the detector summary the
prompt quotes, and splice each span back byte for byte. A rewrite that drops or
repeats a masked span is refused, so a formula is never altered. The MCP `fix`
and `polish` tools do the same when called with `is_tex: true`. Math in other
file types, such as `$...$` in Markdown, is not masked.

The boundary is fixed and load-bearing: a clean gate, a low texture score, or a
Match receipt means the prose was screened under a named ruleset. It says nothing
about whether the theorem is true. A clearly written proof can still be false, and
Articulate never checks the mathematics. Correctness comes from referees and proof
assistants (Lean, Coq, Isabelle), never from this tool.

## Privacy

The detector never touches the network. The editor layer (`judge`, `fix`,
`polish`, `review`) has one backend today: the `claude` CLI (`claude -p`), which
sends the full text to a hosted Anthropic model. No local-model backend exists
yet, so do not run the editor on text you may not upload, such as a manuscript
you received for review. A local backend and an `--offline` mode are on the
roadmap. A content-free audit receipt keeps no verbatim text: it drops the matched
substring and the exact offsets, keeping only which rule fired, its tier and
category, and the line. A team can retain and replay a record without storing the
sensitive source. Content-free is not zero-leakage: which rules fired and the line
remain, which for a closed-vocabulary rule narrows the flagged word to that rule's
small public candidate set. The `hash` mode keeps a sha256 for an equality check
against a known string, so it is dictionary-reversible for those closed-vocabulary
rules; use `drop` when the flagged word must stay secret. An auto-filled `reviewer`
(from `$GITHUB_ACTOR`) records CI attribution, and a named human sign-off needs an
explicit `--reviewer`. Committed receipts live as long as the repo, with no
automatic expiry (bounded retention is a later self-hosted tier). The full
[documentation](docs/) covers each surface and the boundaries in depth.

## Status

Pre-1.0. The core detector, profile system, writing modes (including the science
modes for proofs and technical exposition), the genre axis (fiction, memoir,
screenplay, poetry), the editor injection boundary, per-paragraph span
verdicts, a sub-threshold "unverifiable" calibration, binary fail-closed input
guards, the benchmark, the editor layer, the CLI, the LSP and SARIF surfaces,
receipts, the content-free audit receipt, and the MCP server are built into this
one package. Version 0.4.1 is on PyPI as `articulate-writing`; the
[changelog](CHANGELOG.md) records what each release added. A local-model editor
backend and a labeled non-native corpus for a fairness check remain on the roadmap.
