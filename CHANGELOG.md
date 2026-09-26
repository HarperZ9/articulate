# Changelog

All notable changes to `articulate-writing` are recorded here. The package uses
semantic versioning. This is the package version. The detector ruleset carries its
own `RULESET_SEMVER`, which a receipt records so a replay knows which rules ran.

## Unreleased

### Fair signals, no origin claims, a writer-held process record (ruleset 0.7.0)

A 2023 study (Liang et al., Patterns 100779) found that perplexity detectors
flag plain, predictable English, common in second-language writing, as machine
text. An audit of Articulate 0.4.1 on the study's released texts found its
default profile blocked 38 of 91 learner exam texts against 21 of 70 US college
essay windows and 31 of 145 student abstract windows, and one rule fired about
11 times as often per word on the learner texts. This release answers that. The
measured before and after are in `docs/fairness-audit.md`; the new ruleset's
release gate does not yet pass on that corpus, and the page says why.

Rules and scanning:

- A house pack holds one writer's style: the em dash in every form, the contrast
  devices, the intensifiers, corporate verbs, register word lists and jargon,
  ordinal enumeration, stock transitions, closers, cadence beats and stock
  email, blog and marketing phrases. Only the new `house` and `house-essay`
  profiles gate it; every other profile reports it at LOW with `house: true`. No
  path rule resolves to a house profile.
- Every rule that can block outside the house pack carries a reader-cost reason
  and a published source (`rule_reasons.py`). No reason is how often a model
  uses a pattern.
- The old `essay` profile is now `house-essay`. The new `essay` is strict
  without the house pack, and `.tex`, `essays/`, `blog/` and `writing/` paths
  resolve to it.
- The four intensifiers report only outside the house pack; a valediction such as
  "Yours truly" is never one. A bare spoken affirmation reports only; a chat
  reply that hands over a deliverable still blocks. Self-identification needs
  the first person, so a quoted AI Act Article 2(12) raises nothing. A
  zero-width space blocks only inside Latin text. `wordiness` moves to MEDIUM.
- Paragraphs are read as logical lines with an offset map, so soft-wrapping and
  one sentence per line give the same findings; every match counts; line-start
  rules run at every sentence start; findings gain `end_line`. A period after
  "et al." or "e.g." no longer ends a sentence.
- Cadence flags need 12 sentences and 200 words and never block. The adverb rate
  leaves out the intensifiers. C2PA text manifests (Annex A.8 and A.9) are
  blanked before any rule runs.
- The ruleset fingerprint now covers the scanner's constants, the house pack, the
  reasons and a `SCAN_ALGO` counter, and a golden test pins every finding over
  `corpus/` to it.
- Seven category ids that named an origin are renamed (`assistant-residue` to
  `chat-interface-text`, `filler-intensifier` to `intensifier`, `register-word`
  to `inflated-word`, and four more). The profile field `slop` is now
  `gate_level`. Old names stay readable for one minor version.

Outputs:

- The texture score and `verdict` (with its 30-word floor) are retired. Results
  carry `findings` (`has_findings` or `no_findings`), `words`, per-rule counts,
  density per 1,000 words with an exact interval at 250 words or more, and
  `gates` on each finding. The gate is the only pass-or-block signal.
- Every machine-readable output carries `does_not_prove`. SARIF puts it, with
  the rule's reason, in each rule's help text and records the profile on each
  result.
- `--spans` reports per-paragraph counts by rule with no per-paragraph gate or
  label. Receipts are schema v2; a v1 receipt replays to Unverifiable with the
  reason.
- Product text everywhere reads "Local prose checks: named writing patterns,
  where they occur, and what each costs a reader." Both MCP servers read one
  description table (`tool_text.py`).
- The benchmark is an expected-findings regression over `corpus/patterns/` with
  a false-finding control over `corpus/control/`. The `.pangram` sidecars and
  the recall target are gone.

Editor:

- Every instruction targets the intended reader (`prompts.py`). No template
  names an outside score, a sentence-length target or a vocabulary level. The
  house writing standard reaches the model only under a house profile. The
  model-input block is now `CHECKER FINDINGS`, renamed together with the trust
  boundary.
- `editor.accept()` is the whole acceptance rule for the CLI and MCP `polish`.
  `fix` and `polish` take `--profile`.

New:

- `python -m articulate.fairness`: a harness that runs every bound profile over
  a hash-checked corpus manifest and writes a content-free receipt with the
  pre-registered gates G1 to G7 (`fairness/PREREG.md`), plus `--release-check`,
  now a step in the publish workflow.
- `articulate process`: a local, opt-in record of your own drafts as salted
  commitments, with order and day by default, private input methods, reveals a
  reader can check, and a C2PA-shaped process summary.
- `articulate disclose`: a statement of tool use and CRediT credit from the log
  that never lists a model as an author and refuses a no-tool claim when the log
  records assistance.
- `articulate desk`: the questions a reviewer should ask, inside the document and
  across the field, with no score, verdict or ranking.

Other changes on this branch:

- A Markdown table delimiter row such as `|---|---|` or `|:---:|` no longer raises
  a HIGH `em-dash` finding. The inline `---` check read the row's hyphen runs as an
  em-dash, so a Markdown paper with a table failed the gate under every
  non-fiction profile. `detector.is_md_table_sep` recognizes the row: at least one
  pipe, and every cell is hyphens with optional alignment colons. A real em-dash
  or a mid-line `---` inside a table cell still fires. `tests/test_md_tables.py`
  covers both sides. Findings change for any text with a table, so
  `RULESET_SEMVER` moves 0.5.0 to 0.5.1 and a receipt issued under 0.5.0 replays
  as `Unverifiable`, never as a misleading `Drift`. The ruleset fingerprint
  moves from `sha256:9f78a7484bb20f84` to `sha256:3835c2deace65a1e`.
- `articulate receipt --mode M` now screens under the mode and records it. The
  flag was accepted and then ignored: a receipt issued with
  `--mode academic/argue` recorded the base profile `research` and its gate, so
  it described a screening the author never ran. The receipt now carries a `mode`
  field beside the mode's base profile, and `verify` replays under that mode. A
  receipt whose mode is unknown or malformed, or whose profile is not the mode's
  base, reads `Unverifiable`. An unknown `--mode` or `--profile` exits 2 with a
  message and no output. `receipt.make_receipt` takes a `mode` keyword.
  `tests/test_receipt_mode.py` covers issuance, replay, and tampering.
- `--fix` now masks math on a `.tex` file. Only `--polish` called `mask_math`, so
  `--fix` sent every formula to the model while the README said the editor masks
  every math span before a rewrite. Both paths now go through
  `editor.masked_rewrite`, which also builds the prompt's detector summary from
  the masked text, since that summary quotes document lines and carried the math
  into the prompt under `--polish` as well. `splice_math` now refuses a rewrite
  that drops, repeats, or invents a placeholder (`MathSpliceError`), where it used
  to delete the formula silently. Masking runs in one pass, so a theorem, lemma,
  proof, or other listed environment is masked whole with the math inside it and
  every span restores byte for byte; before, inline math inside an environment
  got its own placeholder that the environment span then swallowed, which left a
  stray placeholder in polish output. Under `--polish` the quality scorer reads
  the masked text as well, and its notes reach the rewrite prompt with any math
  scrubbed, so no model call on a math file carries a formula. The MCP `fix` and
  `polish` tools take an `is_tex` flag with the same behavior. MCP `fix` reports
  a refused rewrite with a note that names the refusal, where it used to blame
  the backend, and MCP `polish` keeps the last accepted text, as the CLI does. `tests/test_fix_integrity.py`
  and `tests/test_math_masking.py` drive each path with a fake model and never
  call a hosted one.
- Both rewrite prompts drop "human" from their target and ask for "skilled
  writing that fully satisfies the standard". The target is the writing
  standard, never a reading of who wrote the text.
- `--fix` self-checks its rewrite under the chosen mode. The first pass read the
  detector under the mode's profile, and the post-rewrite checks ran under the
  default profile, so a rewrite under `academic/explain` that kept one of the
  mode's terms of art was reported as "still has tells". Both post-rewrite
  checks now take the mode's profile.
- The README, the walkthrough, and the MCP "unavailable" notes no longer say the
  editor defaults to a local model. The README lead, the hero image, the package
  docstring, the docs index, and the PyPI description now call only the detector
  local. The only editor backend is the `claude` CLI,
  which sends the full text to a hosted Anthropic model. The README's Privacy
  section now says so and warns against running the editor on text you may not
  upload. A local backend and an `--offline` mode stay on the roadmap.
- `--spans` is described as a writing-quality view that finds the paragraph
  carrying the findings. The help text said "localize mixed authorship", and the
  walkthrough and features pages framed spans the same way, which invited use as
  an authorship detector or an origin gate. The boundaries page gains a section
  stating that no verdict, span verdict, or receipt is an authorship finding. The
  word-floor text on the boundaries and features pages now says too few tokens
  "to call a text clean", without "human", and the walkthrough example and the
  spans tests no longer stage the paragraphs by who wrote them.

## 0.4.2

The editor commands `judge`, `fix` and `polish` now find the `claude` CLI in
more setups, and the model call runs with no tools. Detector findings and the
ruleset fingerprint do not change.

The editor started the CLI by the bare name `claude`. That failed in two cases.
A process that an MCP host or a bundled app starts can inherit a PATH that
holds only System32. And on Windows, subprocess without a shell looks only for
`claude.exe`, so it never found the `claude.cmd` shim that an npm install puts
on the PATH. In both cases the start raised an uncaught `FileNotFoundError`.

- New module `articulate.claude_cli` resolves the CLI. The environment variable
  `ARTICULATE_CLAUDE_CLI` names its path and wins when set. Its value must be an
  absolute path; a bare name or a relative path is refused.
- Otherwise the resolver walks the absolute PATH entries itself. It takes
  `claude.exe` from any entry first, and a `claude.cmd` or `claude.bat` shim
  only when no entry holds `claude.exe`. So a setup that ran `claude.exe`
  before still runs it, whatever the PATH order. The current directory is never
  searched, and neither is a `.` or empty PATH entry. On Windows,
  `shutil.which` looks in the current directory first, so a document repo that
  shipped a file named `claude.cmd` would have run in place of the real CLI.
- When nothing runnable is found, the editor raises `ClaudeUnavailable`. Its
  message names the variable and says the CLI must be installed and logged in.
  A start that fails with an `OSError` raises the same error. No message prints
  the value of the variable or the resolved path. A timeout message names only
  `claude`.
- The prompt now travels in a temporary file passed with
  `--append-system-prompt-file`, on every path, and the file is removed after
  the call. The argument list holds a fixed line, that path and fixed flags. A
  prompt with many detector findings could pass the Windows command-line limit
  of about 32K characters, which failed with a misleading "could not be
  started" error. And a `.cmd` file runs under cmd.exe, which cuts an argument
  at the first newline and treats `%`, `^`, `&`, `|`, `<`, `>` and `!` as
  commands. For a batch file, a path with one of those characters is refused.
- Every call passes `--strict-mcp-config --tools ""`, so the model session has
  no built-in tool and loads no MCP server. The document is untrusted input,
  and before this change the `claude -p` child inherited the user's allow
  rules and MCP servers.
- A timeout now stops the whole process tree: `taskkill /F /T` by its System32
  path on Windows, a process-group kill elsewhere. Before, a timeout on a batch
  shim killed only cmd.exe and then waited for the CLI to finish.
- `polish` now catches a judge failure inside its rewrite loop, such as a rate
  limit halfway through, keeps the best version so far and exits cleanly.
  Before, that failure ended in a traceback.

Changed for callers:

- The model's instructions now arrive as an appended system prompt, and the
  user turn holds a fixed line. The trust boundary text still ends the
  instructions, and the document stays on stdin.
- `editor.CLAUDE` is removed, and setting it has no effect. The variable
  `ARTICULATE_CLAUDE_CLI` now names the CLI.
- `editor.run` is removed. A test double that patched it would now reach the
  real CLI. A double now patches `articulate.claude_cli.run`.
- A missing CLI raises `ClaudeUnavailable`, a `RuntimeError`, where it used to
  raise `FileNotFoundError`, an `OSError`. `ClaudeUnavailable` moved to
  `articulate.claude_cli`; `articulate.editor` still exports it.
- `claude_cli.resolve` reads PATH from the `environ` mapping it is given.

Tests: `tests/test_claude_cli.py` and `tests/test_claude_cli_process.py` cover
the resolution order, a `claude` planted in the current directory, the closed
errors, the fixed argument list, every character cmd.exe reinterprets for both
`.cmd` and `.bat`, a 40,000-character prompt, and a timeout that must return
within 5 s while a grandchild sleeps. A parse of every source module checks
that no call asks for a shell. CI now also runs the suite on `windows-latest`,
where the stand-ins go through cmd.exe.

Not verified: a model reply through the batch path. A stand-in `claude.cmd`
around the real CLI 2.1.251 accepted the new arguments and reached the
backend, which answered with a credit error on the test machine.

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
