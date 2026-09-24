# Changelog

All notable changes to `articulate-writing` are recorded here. The package uses
semantic versioning. This is the package version. The detector ruleset carries its
own `RULESET_SEMVER`, which a receipt records so a replay knows which rules ran.

## Unreleased

Changes on the main branch since 0.4.1. The package version stays 0.4.1 until a
release is cut.

- Meaning guard. `articulate compare ORIGINAL REWRITE` reports each surface
  invariant as kept, dropped, added, or changed, with line and column: numbers
  with units, dates, times, and versions; negations; modal strength (with BCP 14
  capitals as their own value); scope words; the direction of a bound on a
  number or date ("under 50%", "up to 10 MB", "before May 5"); named entities;
  URLs and emails; code; math; citations; quoted strings; and freeze terms.
  `--gate` exits 1 on a change, and `--allow-change KINDS` exempts named kinds.
- `fix` and `polish` run every model rewrite through the guard. A rewrite that
  changes an invariant is refused, the previous text is kept, and the output
  names the invariant. `--allow-change` and `--freeze` configure it.
- Both MCP servers gain a local `compare` tool, and `fix` and `polish` take an
  `allow_change` argument and report a refusal with its blocking invariants.
- Limit: the invariants are surface proxies. A rewrite can keep all of them and
  still change the meaning. The report says so in a `does_not_prove` field.
- Protected spans. The math masking that `.tex` files had is now a general layer
  used before every model rewrite: fenced and inline code, math, URLs and emails,
  citations, block quotes, quoted material, and freeze terms become placeholders
  the model never sees. Every placeholder must come back exactly once and in
  order, and is spliced back byte for byte; a missing, duplicated, invented,
  reordered, or mangled placeholder refuses the rewrite, and so does one moved
  into another paragraph when the paragraph count holds. `--unprotect
  quotes,blockquotes` releases the two configurable kinds, and the meaning
  guard then reads a released quote as prose.
- Change report. `--explain` (text) or `--explain json` after `--fix` or
  `--polish` lists each changed sentence before and after, the detector findings
  it carried (rule id and message), the findings left in the new sentence, the
  meaning-guard rows for the pair, and every refused candidate with its reason.
  The MCP `fix` tool returns the same per-sentence records.
- Project config. A `.articulate.json` found by walking up from each file (JSON,
  because the package supports Python 3.9) sets profiles by path glob, banned
  and preferred terms with reasons and suggestions, allowed terms of art, freeze
  terms, the protect switches, and rule-pack options. Terminology findings carry
  their own rule ids (`terminology/banned/<term>`, `terminology/preferred/<form>`)
  and show in `check`, SARIF, the LSP server, per-span verdicts, and receipts.
  `--config PATH` or `--config none` overrides discovery on every command, and
  `articulate config PATH` shows what applies. A malformed file stops the command
  with the reason.
- Receipts made under a config embed the project rules and their hash, so a
  replay re-derives with no access to the project.
- Ruleset semver moves 0.5.0 to 0.6.0. Older receipts read `Unverifiable` under
  this build, as a ruleset change should.
- Domain profiles, each backed by a rule pack with its own rule ids:
  `ux-microcopy` (length limits for buttons, labels, and errors; case; vague
  error text; link text such as "click here"), `code-review` (condescension
  markers, requests with no reason, absolute language about a person),
  `plain-language` (a Flesch-Kincaid grade gate, default 8, plus long sentences
  and wordy phrases), and `controlled-english` (sentence length, one instruction
  per sentence, idioms, phrasal verbs, a sentence-initial pronoun with no noun).
  The existing `normative-spec` register gains RFC 2119 / RFC 8174 checks:
  mixed-case keywords (gating), keywords without the boilerplate, "MAY NOT",
  lowercase keywords in a declared document, SHALL mixed with MUST, and the
  pre-8174 boilerplate. Every numeric default is a config option and names its
  source in the docs; heuristic rules sit in LOW and never block.
- `corpus/domains/` holds synthetic samples with an `expect.json`; the benchmark
  now counts a domain mismatch as a regression.
- Drafting provenance. `articulate drafts record|show|verify FILE` keeps a local,
  append-only, hash-chained log of a document's drafts in `.articulate/drafts/`
  beside it: text hash, time, word count, texture score, lines added and removed
  since the previous draft, and an optional `--actor` label. Draft text is stored
  content-addressed so `verify` re-derives each entry; `--no-snapshot` keeps
  hashes only. A broken log is never extended. It records that drafts were
  logged in an order; it does not prove who typed them, its times come from the
  local clock, a deleted tail is undetectable without an external anchor, and it
  is not a tool for passing a detector.
- Docs state the scope and the privacy posture concretely: the rules read English
  only; the core makes no network call and has no telemetry; only the editor
  sends text, to the user's own backend, with protected spans masked. A test now
  fails the build if any module imports a network library or if a module other
  than the editor starts a subprocess. The README no longer says the editor
  defaults to a local model: the code supports the `claude` CLI only, and a
  local-model backend stays on the roadmap.

## 0.4.1

Fixed quadratic run time in the markup masks. Findings do not change, and the
ruleset fingerprint does not move.

Before the prose passes run, the detector blanks URLs, e-mail addresses, and HTML
tags on every line, plus quoted speech under a dialogue-exempt genre. It did this
with `re.sub` and patterns that backtrack quadratically on a long line where a
match never completes. `strip_markup` runs up to six times per line, so one such
line stalled `check_text` far past the 3 s budget the ReDoS test enforces.

Time for one `check_text` call, before and after:

- `"v1." * 10000` under flavored: 16.0 s before, 0.08 s after.
- `"1.1.1.1." * 5000` under flavored: 53.2 s before, 0.14 s after.
- `("1.1.1.1." * 5000) + "@"` under flavored: 47.8 s before, 0.14 s after.
- `"twenty-" * 8000` under flavored: 29.5 s before, 0.08 s after.
- `"<a " * 40000` under flavored: 23.5 s before, 0.33 s after.
- `"\u201ca " * 20000` under literary-fiction: 13.6 s before, 0.21 s after.

Before and after were measured on one machine, each pair in one session. That
machine was under load from other work, so the absolute numbers are noisy.

- The e-mail part of the URL pattern retried every word boundary inside a long
  run of word characters, dots, or hyphens, and rescanned the rest of the run
  each time. The tag pattern rescanned to the end of the line from every
  unclosed `<`. The quote pattern did the same from every unclosed curly quote.
- New module `articulate.masking` returns exactly what `re.sub` returns with
  each pattern, in linear time. The e-mail scan tests each run once, because
  every start inside one run succeeds or fails together. The tag mask stops at
  the last `>` in the line, since no tag can start after it. The quote mask
  skips an opening mark once one of its kind has failed to close before the
  next newline.
- The patterns themselves are unchanged and remain the definition of record as
  `detector.URL`, `detector.TAG`, and `detector.QUOTED`. `tests/test_masking.py`
  compares each mask with `re.sub` on 4,000 generated lines and a set of hand
  cases. It also holds each mask, and the detector functions `strip_markup` and
  `mask_quotes` that apply them, to 0.25 s per call on long hostile lines, so a
  call site that goes back to `re.sub` fails as well.
- `tests/test_redos.py` adds the inputs above, so the 3 s per-input budget now
  covers them. The tag and curly-quote inputs use 40000 and 20000 repeats. With
  10000 repeats the old code took 0.3 s to 0.6 s on the tag input and 3.3 s to
  5.0 s on the quote input, so a regression there could pass the budget.
- Checked for identical output: full `check_text` results (rule ids, spans,
  labels, gate, texture, cadence) and per-line masks were compared before and
  after on every tracked file except the VS Code extension's lockfile, under no
  profile and under all 18 profiles, 6 genres, and 29 modes. The same check ran
  on 612 further documents (Markdown, HTML, SVG) under 9 configurations. No
  result differed. The benchmark output is byte-identical.
  The fingerprint hashes the tier patterns and leaves the mask patterns out. It
  reads `sha256:9f78a7484bb20f84` before and after, so `RULESET_SEMVER` stays
  0.5.0.

Tests: 181 pass.

## 0.4.0

Added a stdio MCP server that runs from a bare install.

The existing MCP surface is built on fastmcp, which is declared under the `mcp`
extra. A plain `pip install articulate-writing` produced a package whose MCP
entry point raised `ModuleNotFoundError: No module named 'fastmcp'` the moment a
host launched it. The install reported success and the server never started.

- `articulate.local_mcp` serves the same five tools over stdio JSON-RPC 2.0
  (protocol `2025-06-18`) with nothing but the standard library, plus
  `articulate.status` and `articulate.doctor`. `doctor` reports which tools run
  local (`check`, `score`) and which need an LLM backend (`judge`, `fix`,
  `polish`), so a host with no backend knows what it still gets.
- New console script `articulate-mcp`. The fastmcp server stays available under
  the `[mcp]` extra as `articulate.mcp_server`.
- The tool bodies are unchanged and shared. Both transports call the same
  `do_check`, `do_score`, `do_judge`, `do_fix` and `do_polish`, and a test parses
  the fastmcp module for its `@mcp.tool` functions to assert the stdio server
  exposes every one of them. The two surfaces cannot drift apart.
- `tests/test_version_alignment.py` binds `pyproject.toml`, `articulate.__version__`
  and the version the MCP server reports. The three had no guard tying them
  together, so a release could ship reporting the previous version.
- The publish workflow now pins every action by commit SHA. A tag can be moved to
  point at different code, which matters in a workflow that holds publishing
  authority. It also checks the release tag against the declared version, records
  artifact digests, resolves every console script in a clean venv, and rebuilds a
  wheel from the sdist before uploading.

## 0.3.0

Added three cadence detectors for prose that reads clean under the earlier ruleset
yet still carries a machine rhythm a reader hears.

- Demonstrative summary-beat, "That is the ... half / side / piece / layer / angle
  / story / trick". Tier MEDIUM, so it gates under a strict profile. A compound noun
  like "That is the side effect" and a plain "That is the file" do not fire.
- Two-imperative parallel slogan, "Verb the X, verb the Y." Tier LOW and advisory,
  since an everyday instruction is often an imperative pair. It anchors to a full
  line of two comma-joined bare-verb clauses, and a determiner or pronoun opener
  blocks it.
- Evaluative fragment opener, "Strong foundation." Tier LOW and advisory,
  paragraph-initial only, and fragment-shaped so a full sentence does not match.

Detector internals:

- Ruleset semver moves 0.4.0 to 0.5.0, and `FRAGMENT_OPENER` folds into the ruleset
  fingerprint, so a replay against an older receipt reports the ruleset change
  explicitly.
- A verse genre suppresses the two new LOW categories.
- Every new pattern uses bounded quantifiers and stays covered by the ReDoS safety
  test.
- The demonstrative extension fires on none of a 26-snippet human control corpus.

Tests: 151 pass.

## 0.2.0

Detector expanded to the full device catalogue. It reached 18 HIGH, 55 MEDIUM, and
12 LOW tells, plus 7 standard-library statistical advisories. The tells cover
lexical and structural devices, cadence, delivery, and formatting.
False-positive-controlled against a 22-snippet human corpus with zero false HIGH or
MEDIUM. Ruleset semver 0.4.0. Tests: 143 pass. Published to PyPI as
`articulate-writing`.

## 0.1.0

First public release. The core detector, register profiles, writing modes, the
genre axis, per-span mixed-authorship verdicts, an "unverifiable" sub-threshold
calibration, binary fail-closed input guards, the benchmark, the editor layer, the
CLI, the LSP and SARIF surfaces, receipts, the content-free audit receipt, and the
MCP server. The core runs standard-library-only with no network call.
Source-available under FSL-1.1-MIT. Published to PyPI as `articulate-writing`.
