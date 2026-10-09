<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/HarperZ9/articulate/main/docs/art/hero-dark.svg">
  <img src="https://raw.githubusercontent.com/HarperZ9/articulate/main/docs/art/hero-light.svg" alt="articulate: Local writing-quality and AI-tell detection and editing, no network. A fan of ruled sheets drawn in fine lines, the top sheet lit by a bright core." width="100%">
</picture>

# articulate

Local writing-quality and AI-tell detection and editing, no network.

```
python -m articulate.cli check path/to/doc.md --gate
```

[![version: 0.9.0](https://img.shields.io/badge/version-0.9.0-e6e1d6?style=flat-square&labelColor=1a1712)](https://pypi.org/project/articulate-writing/)
[![CI](https://github.com/HarperZ9/articulate/actions/workflows/ci.yml/badge.svg)](https://github.com/HarperZ9/articulate/actions/workflows/ci.yml)
[![license](https://img.shields.io/badge/license-FSL--1.1--MIT-e6e1d6?style=flat-square&labelColor=1a1712)](https://github.com/HarperZ9/articulate/blob/main/LICENSE)
![python 3.9+](https://img.shields.io/badge/python-3.9%2B-e6e1d6?style=flat-square&labelColor=1a1712)

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
say what a verdict and a receipt mean and what they never claim. The
[house voice](docs/house-voice.md) spec and the guide to
[series review and your own voice](docs/series-and-voice.md) cover the 0.8.0
voice features.

## See it work, step by step

The [animated explainer](https://harperz9.github.io/repo-explainers/articulate.html)
follows one short draft through the checker: the six findings and their tiers,
how three profiles gate the same findings, how the texture score is computed,
per-span verdicts, and a receipt that replays to Match, Drift or Unverifiable.
Every value on it is output from this repository. Its source is
[docs/explainer/index.html](docs/explainer/index.html).

## Watch

No concept film fits this tool closely yet. The walkthrough below covers it in text, with real commands and output.

Video walkthrough: coming with the next release.

## Walkthrough

Install it, run it once, then use the main feature. Each command below is real, and so is its output.

1. **Install.** Install from PyPI. Python 3.9 or newer; the checker uses the standard library only and makes no network call.

   ```text
   $ python -m pip install articulate-writing
   ```

2. **First run: check a draft.** Check a draft against a profile. With `--gate` the command exits 1 when high findings block it.

   ```text
   $ articulate check post.md --profile readme --gate
   [articulate] post.md [readme]: 3 high, 2 medium (blocked)  texture 70/100
   ```

3. **Seal a receipt and re-derive it.** Write a receipt for the check, then verify it against the same file.

   ```text
   $ articulate receipt post.md --profile readme > post.receipt.json
   $ articulate verify post.receipt.json post.md
   [articulate] Match: re-derived 6 findings, gate blocked, texture 70
   ```

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
  detector score. Use the calling model, a configured backend, or mechanical
  fixes with no model. Every result names its backend and any failed attempts.

- **Give the model a voice.** The house voice is a published, versioned voice
  for AI models: answer first, numbers with denominators, "I" only for what the
  model did in the session, and no claim to a human life. It is opt-in:
  `articulate house on` turns it on, and `articulate house off` turns it off.
- **Build your own voice.** `articulate voice learn --mine` builds a profile from
  your own writing, on your computer. Compare drafts with it, run the
  authorship interview, and, when you ask, shape your own draft toward it.
- **Review a series.** `articulate corpus` reads several documents together and
  names repeated title formulas, shared scaffolds, even rhythm and missing
  perspective, with locations and no replacement prose.

## Use

Articulate includes no model. A connected client can call `edit_plan`, write the
rewrite with its selected model, and submit it through `edit_submit`. The model
account and conversation policy belong to that client. Local checks and host
edits require no publisher-hosted service or separate model API key.

Version 0.9.0 prepares [Windows x64 native ZIP and MCPB packages](docs/native-local-package.md)
with a Python runtime included. The [source plugin](docs/claude-plugin.md) remains
available for local Claude Code, Codex and portable MCP hosts with installed
Python. Native client installation and marketplace acceptance remain unverified.

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
`--judge`, and `--fix` is opt-in. On a `.tex` file the editor masks every math
span before a rewrite and splices it back byte for byte, so a formula is never
altered.

The boundary is fixed and load-bearing: a clean gate, a low texture score, or a
Match receipt means the prose was screened under a named ruleset. It says nothing
about whether the theorem is true. A clearly written proof can still be false, and
Articulate never checks the mathematics. Correctness comes from referees and proof
assistants (Lean, Coq, Isabelle), never from this tool.

### Editing from a host or the command line

In an MCP host, `fix`, `judge` and `polish` use sampling only when the client
advertises it. Otherwise they return an edit plan for the calling model.
The host reads the plan's instructions and masked text, then calls `edit_submit`
with the original text, its rewrite and the plan ID. Articulate checks protected
spans and returns the accepted text, gate changes and a host receipt. No second
model account is needed. Sampling and host edits follow the host's privacy policy.

```bash
articulate plan notes.md --goal fix > plan.json
articulate submit notes.md rewrite.md --plan PLAN_ID --model HOST_MODEL
articulate fix notes.md --backend none --out edited.md
articulate polish notes.md --backend ollama --json
```

Replace `PLAN_ID` with the ID in `plan.json`; the host writes `rewrite.md` from
the plan's masked text. The CLI's `auto` selection tries configured Anthropic,
the Claude CLI, configured OpenAI-compatible endpoints, Ollama and deterministic
editing in that order. A failed backend is recorded before the next is tried.
See the [backend configuration reference](docs/cli.md#backend-configuration).

## Privacy

The detector and `--backend none` never call a model or the network. Anthropic
and the Claude CLI send text to their provider; an OpenAI-compatible endpoint
receives text at its configured address. Ollama receives text at its configured
server. Host editing and MCP sampling share text with the calling host, which
may use a remote model. Set `ARTICULATE_LOCAL_ONLY=1` to allow only loopback
Ollama and deterministic editing; other editor backends are refused before a
connection. Plan payloads and edit results contain document text; handle them
as source material. A content-free audit receipt keeps no verbatim text: it drops the matched
substring and the exact offsets, keeping only which rule fired, its tier and
category, and the line. A team can retain and replay a record without storing the
sensitive source. Content-free is not zero-leakage: which rules fired and the line
remain, which for a closed-vocabulary rule narrows the flagged word to that rule's
small public candidate set. A personal voice profile is built only from files
you name, holds aggregates and no sample sentence, and stays in your local voice
store until `articulate voice delete --all`. The house-voice brief that enters a
model's context is the same published text for everyone. The `hash` mode keeps a sha256 for an equality check
against a known string, so it is dictionary-reversible for those closed-vocabulary
rules; use `drop` when the flagged word must stay secret. An auto-filled `reviewer`
(from `$GITHUB_ACTOR`) records CI attribution, and a named human sign-off needs an
explicit `--reviewer`. Committed receipts live as long as the repo, with no
automatic expiry (bounded retention is a later self-hosted tier). The full
[documentation](docs/) covers each surface and the boundaries in depth.

## Status

Pre-1.0. The core detector, profile system, writing modes (including the science
modes for proofs and technical exposition), the genre axis (fiction, memoir,
screenplay, poetry), the editor injection boundary, per-span mixed-authorship
verdicts, a sub-threshold "unverifiable" calibration, binary fail-closed input
guards, the benchmark, the editor layer, the CLI, the LSP and SARIF surfaces,
receipts, the content-free audit receipt, and the MCP server are built into this
one package. Version 0.9.0 is prepared for release as `articulate-writing`; the
[changelog](CHANGELOG.md) records what each release added. Optional adapters can
use a model you supply; no model is bundled. This release retains the published
v0.5.2 detector rules and fingerprint while extending packaging and rewrite
guards. It excludes withheld development-branch scanner changes. Retention does
not establish fairness, and accepted rewrites can still change meaning.
