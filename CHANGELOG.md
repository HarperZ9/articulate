# Changelog

All notable changes to `articulate-writing` are recorded here. The package uses
semantic versioning. This is the package version. The detector ruleset carries its
own `RULESET_SEMVER`, which a receipt records so a replay knows which rules ran.

## Unreleased

### Reader-cost rules, no origin claims, a writer-held process record

The release check blocks this ruleset. Ruleset `sha256:46e1485cd2c98caa` fails
the pre-registered fairness gate on the held-out PERSUADE 2.0 corpus (G1, G2 and
G4; `docs/fairness-confirmatory.md`), and a package release that changes the
ruleset publishes only when that gate passes. The notes below describe the
changes and the evidence as they stand.

A 2023 study (Liang et al., Patterns 100779) found that perplexity detectors
flag plain, predictable English, common in second-language writing, as machine
text. An audit of Articulate 0.4.1, whose rules 0.5.0 kept, on the study's
released texts found its default profile blocked 38 of 91 learner exam texts
against 21 of 70 US college essay windows and 31 of 145 student abstract
windows, and one rule fired about 11 times as often per word on the learner
texts. These changes answer that audit.
The decisions behind them, with their reasons, are in
`fairness/DECISIONS-PR9.md`.

What you gain:

- **Reasons you can check.** Every rule that can block outside the house style
  carries a one-sentence reader cost and a published source. `check --verbose`
  prints it, and JSON and SARIF carry it. No reason rests on how often a model
  uses a pattern. No reader other than the maintainer has checked these reasons
  yet.
- **House style on request.** One writer's style (the em dash, the contrast
  devices, intensifiers, stock transitions and similar patterns) blocks only
  under the `house` and `house-essay` profiles, and shows elsewhere only with
  `--house-notes`.
- **Fewer blocks on plain and scholarly English.** Under the default profile
  only an interface token, a first-person claim to be an AI or a language model,
  and a hidden character inside Latin text can block. The phrasing rules skip
  quoted text, and an appeal to studies accepts every common citation style.
- **A local-only switch.** `ARTICULATE_LOCAL_ONLY=1` or `--local-only` refuses
  every hosted command before any subprocess starts. Any value other than an
  explicit off value counts as on.
- **Content-free outputs that carry no word of the text.** `check
  --content-free` and `receipt --redact` key the two notes whose rule ids quoted
  the text by category.
- **A process record you hold.** `articulate process` keeps an opt-in local log
  of your drafts as salted commitments, `articulate disclose` writes a statement
  of tool use from it, and `articulate desk` lists a reviewer's questions with
  no score.
- **Fairness measured in the open.** `python -m articulate.fairness` measures
  every profile a writer can land on over a hash-checked corpus and writes a
  content-free receipt. Its release check blocks a ruleset whose
  pre-registered gates fail.

Breaking for callers:

- `check_text` and `check --json`: `verdict`, `sufficient`, `texture_score` and
  `elevated` are removed, and `slop` is now `gate_level`. The cadence record no
  longer carries `cv` or `uniform`; the library returns them with
  `cadence_detail=True`. New keys: `blocking`, `findings` (`has_findings` or
  `no_findings`), `counts`, `words`, `rule_counts`, `density`, `house` and
  `does_not_prove`, and on each finding `gates`, `house`, `reason`,
  `reason_source` and `end_line`.
- `clean` and `blocking_count` are deprecated and leave in package 0.7.0. The
  equal of `clean` is `findings == "no_findings"`; `blocking` carries the
  number `blocking_count` did, and `gate` is the pass-or-block signal.
- Outside a house profile, `check_text` reports house-style findings at LOW with
  `house: true`, where 0.5.0 reported the em dash and similar patterns as HIGH
  or MEDIUM. Pass `house_notes=False` to leave them out.
- MCP `check`: `verdict`, `texture_score` and `elevated` are removed, `clean`
  stays until package 0.7.0, and `gate`, `findings`, `blocking`, `rule_counts`,
  `density` and `does_not_prove` are new. MCP `score`: `texture_score`,
  `elevated`, `hard_hits`, `advisories` and `uniform_cadence` are removed; it
  returns `gate`, `words`, `rule_counts`, `density`, `passive_rate`,
  `adverb_rate` and `does_not_prove`.
- Seven category ids are renamed, which changes SARIF rule ids:
  `assistant-residue` to `chat-interface-text`, `assistant-closer` to
  `closing-boilerplate`, `email-tell` to `email-stock-phrase`, `blog-tell` to
  `blog-stock-phrase`, `fiction-slop-lexicon` to `fiction-stock-phrase`,
  `register-word` to `inflated-word` and `filler-intensifier` to `intensifier`.
  The old ids and the profile field `slop` are read until package 0.7.0.
- The old `essay` profile is now `house-essay`; the new `essay` is strict
  without the house style. `essays/`, `blog/` and `writing/` paths resolve to
  `essay`, and a `.tex` file to `research` (`proof` under `proofs/`).
- Receipts are schema v2 and the ruleset fingerprint changed, so a 0.5.0 receipt
  replays to `Unverifiable` with the reason.
- The editor's model-input block is named `CHECKER FINDINGS`.

Evidence and its limits:

- Liang et al. corpus, which the rules were tuned on, so every result here is
  exploratory: the default profile blocks none of the 306 human texts, `essay`
  blocks 1 of 91 learner texts, 0 of 70 college windows and 4 of 145 abstract
  windows, and all 266 gate rows pass (`docs/fairness-audit.md`).
- PERSUADE 2.0, pre-registered and timestamped before the run: 88 of 152 gate
  rows pass. Under the 12 strict profiles, 6.0% of 1,330 learner essays and
  14.0% of 13,467 other essays are blocked, a gap of -8.0 points [-9.3, -6.5]
  (-3.8 within score bands). G2 fails under 17 profiles, with nine rules, all
  toward the other essays. G4 fails under 35 of 38 profiles: 31 to 504 essays
  per profile change findings or word counts when rewrapped to one sentence per
  line. The default profile blocks none of the 14,797 essays.
- Power: against the 70 college windows a gap must reach about 8.4 points to be
  detected 80% of the time; on PERSUADE 2.0 about 3.0 points under the strict
  profiles.
- Not covered: adult academic writers grouped by first language, dictated text,
  disabled writers as a group, World Englishes, and editor behavior by group
  (G6, not run).

Known defects. Each is recorded as a strict expected-failure test. Fixing any
of them changes the ruleset, which now needs a corpus pre-registered for it, so
the fixes wait for that:

- A mention of `\begin{quote}` in inline code, a comment or a code fence hides
  the rest of the file from the phrasing rules.
- An inch mark, a backtick typed as an apostrophe or an autocorrected quote
  before a year blanks the writer's prose up to the next mark. Guillemets and
  other languages' quotation marks, csquotes `\enquote` and a LaTeX quotation
  with an apostrophe inside are not blanked.
- A cite key or a URL does not anchor "state of the art". A citation marker
  right after the closing period does not anchor an appeal to studies. A count
  in parentheses such as "(1600 patients)", or "according to researchers",
  still reads as a citation.
- The sentence splitter joins a sentence that ends in "no" or "Ed" to the next.
- Nine masking and splitting patterns are outside the ruleset fingerprint.

Rules and scanning:

- The house pack holds one writer's style: the em dash in every form, the
  contrast devices, the intensifiers, corporate verbs, register word lists and
  jargon, ordinal enumeration, stock transitions, closers, cadence beats, curly
  quotation marks, a bare "There is" opener, and stock email, blog and marketing
  phrases. No path rule resolves to a house profile.
- A valediction such as "Yours truly" is never an intensifier. A bare spoken
  affirmation reports only, and so does a reply opener that hands over a
  deliverable (`reply-opener`, LOW), which `essay` and the house profiles
  promote to blocking. Self-description needs the first person beside "AI" or
  "language model". A zero-width space blocks only inside Latin text. A Markdown
  table delimiter row is never an em dash.
- New LOW notes that never block by themselves: `padded-purpose` ("in order
  to"), `unanchored-claim` ("state of the art" in a sentence with no number,
  year or citation), `expletive-opener` ("It is important to", "It is worth
  noting that"), `announcement` ("In this essay, we will explore") and
  `padded-preposition` ("with respect to", silent in its math sense). "It should
  be noted that" stays MEDIUM, and "In this essay, I argue" raises nothing.
- Quotations are the source's words. The phrasing rules blank direct quotations
  in double or curly quotes, LaTeX ``...'', Markdown block quotes and LaTeX
  `quote` and `quotation` environments. The self-description rule also skips
  tables, transcript turns, `verbatim` and `\texttt{}` or `\verb` spans. An
  interface token and a hidden character block everywhere, quotes included.
- `unsupported-authority` stays MEDIUM and reads a citation marker anywhere in
  its sentence: superscripts, `(12)` and `[12]`, MLA, footnotes, Pandoc keys,
  LaTeX `\cite`, alpha keys, author and year, legal citations, links and
  "according to" a named source. "Our data show" beside a figure, table or test
  statistic is the writer's own evidence. A year counts only in citation
  position, so "in 1200 patients" does not silence it. Its reason names both
  repairs.
- Paragraphs are read as logical lines with an offset map. Every match counts,
  line-start rules run at every sentence start, and findings gain `end_line`.
  "et al.", "e.g.", "ref.", "p.", "v." and "U.S." do not end a sentence. A line
  that ends in a hyphen after a letter joins the next with no space.
- Cadence flags need 12 sentences and 200 words and never block. The adverb
  rate leaves out the intensifiers. A C2PA text manifest is blanked before any
  rule runs.
- The ruleset fingerprint covers the scanner's constants, the house pack, the
  reasons and a `SCAN_ALGO` counter (now 6). A golden test pins every finding
  over `corpus/` to it, and its writer refuses a new digest under the same
  fingerprint.
- `corpus/control/ptacek-tweets.txt` is removed: no licence for redistribution
  was recorded. Two paragraphs of National Weather Service prose, a public-domain
  work of the United States federal government, replace it.

Outputs:

- Results carry `findings`, `words`, per-rule counts, density per 1,000 words
  with an exact interval at 250 words or more, and `gates` on each finding. The
  gate is the only pass-or-block signal, and every `check` run prints the
  does-not-prove line.
- Every machine-readable output carries `does_not_prove`. SARIF puts it, with
  the rule's reason, in each rule's help text and records the profile on each
  result.
- `--spans` reports per-paragraph counts by rule, with no per-paragraph gate or
  label.
- `articulate receipt --mode M` screens under the mode and records it, and
  `verify` replays under it. An unknown `--mode` or `--profile` exits 2.
- Every command has a help line, and the command map in `--help` and the README
  lists which commands send text and which stay local.

Editor:

- Every instruction targets the intended reader and asks the model to keep the
  writer's variety of English. No template names an outside score, a
  sentence-length target or a vocabulary level, and the house writing standard
  reaches the model only under a house profile.
- `editor.accept()` is the whole acceptance rule for the CLI and MCP `polish`.
  `fix` and `polish` take `--profile` and re-check under the chosen mode.
- On a `.tex` file both `fix` and `polish` mask every math span before each
  model call and refuse a rewrite that drops, repeats or invents one.
- The judge and scorer notes pass through a filter that removes guesses about a
  text's origin. MCP `judge`, `fix` and `polish` carry `does_not_prove`, and a
  local-only refusal says so in its note.
- The editor command line prints that the full text leaves the machine before
  each hosted run. `--advise` is `--review` under a name that cannot be read as
  peer review.

Process record, disclosure and desk:

- `articulate process`: salted commitments with order and day by default, opt-in
  word counts, times and snapshots, private input methods, reveals a reader can
  check, and a C2PA-shaped summary with no entry hash. `verify` reports
  `intact` (exit 0), `broken` (1) or `missing` (3).
- `articulate disclose`: assistance with the recorded task verb and CRediT
  credit for people only, with the NISO role names. It refuses a broken or
  missing log, a claim that matches its list of no-tool phrases while the log
  records assistance, and an author whose whole name is a product name.
- `articulate desk`: questions about numbers with no source nearby, unnamed
  authority, sections a venue asks for and text a reader cannot see, and five
  fixed questions across the field. It prints no score, verdict or ranking.

Fairness harness and release check:

- `python -m articulate.fairness MANIFEST` runs every bound profile over a
  hash-checked corpus manifest and writes a content-free receipt with the gates
  G1 to G8 (`fairness/PREREG.md`). `--jobs N` scans in N processes and writes
  the same receipt, byte for byte. The manifests for the Liang et al., PERSUADE
  2.0 and ELLIPSE corpora are committed; the texts are not.
- `--release-check` gates only a release that changes the ruleset. It skips the
  gates only when `fairness/published-ruleset.json` names an earlier package,
  and a commit after each release updates that record. A changed ruleset needs
  exactly one receipt per listed manifest, each matching its pin in
  `fairness/receipts/SHA256SUMS`, with flags that agree with its numbers and
  gates that pass, and a confirmatory receipt pre-registered for it. An override
  is accepted only when no gate row fails that did not fail in the published
  ruleset's own receipt.
- A receipt of the first draft of these rules is kept, with the report-only rows
  whose keys quoted words of the corpus removed.

## 0.5.0

A document folder can no longer run commands through `judge`, `fix` or
`polish`. Detector findings and the ruleset fingerprint do not change.

In 0.4.2 the `claude -p` child started in the caller's working directory. The
CLI reads `.claude/settings.json` from there, and `-p` skips the workspace trust
prompt. So a document folder that shipped a settings file ran its command hooks
on every editor call, on every platform, and its `env` block reached the
session. On Windows an npm `claude.cmd` shim added a second path: it runs
`node` by bare name, and cmd.exe looked for `node` in the working directory
before the PATH.

- The CLI now starts in a new private folder that `tempfile.mkdtemp` creates.
  That folder holds the prompt file and an empty working folder for the child,
  and the editor removes it after the call.
- Every call now passes `--setting-sources user`, so project and local
  settings never load. The full list is
  `--setting-sources user --strict-mcp-config --tools ""`.
- On Windows the child's environment sets `NoDefaultCurrentDirectoryInExePath=1`,
  so cmd.exe finds the shim's `node` on the PATH only.
- For a batch shim, `)` in an unquoted argument is now refused too. cmd.exe
  reads it as the end of a parenthesized block. A path with a space, such as
  one under `Program Files (x86)`, is quoted and still runs. The check covers
  the prompt file's path as well as the CLI path, so a `TEMP` folder with `&`
  in its name is refused.
- A temporary folder that cannot be written now raises `ClaudeUnavailable`,
  and the message leaves out the path. In 0.4.2 the `OSError` escaped as a
  traceback.
- The editor searches the CLI's output for backend errors, such as a rate
  limit, only when the call fails. A `fix` of a document that mentions rate
  limits used to fail as `ClaudeUnavailable`. A call that exits nonzero now
  always fails, even when it printed output.
- An older CLI that rejects one of the flags now raises `ClaudeUnavailable`
  with a message that says to upgrade. The flags are tested with CLI 2.1.251.
  The first version that accepts all of them is unknown.

Breaking for callers:

- This release carries the minor version that 0.4.2 should have had. The
  0.4.2 changes for callers below were breaking, and a `~=0.4.1` pin picked
  them up as a patch.
- The runner that `claude_cli.run` calls now receives `cwd` and `env` keyword
  arguments. A test double must accept them.

Tests: the new `tests/test_claude_cli_batch.py`, `tests/test_claude_call.py`
and `tests/test_no_shell_calls.py` and the updated CLI tests cover each change.
A unit test checks that the child's working folder is new, empty and apart
from the prompt file. A process test starts a stand-in from a folder that holds
`.claude/settings.json` and checks where it ran. A Windows test runs npm's own
`claude.cmd` template with a `node.cmd` planted in the caller's folder. A
Windows test runs every punctuation character through cmd.exe and checks that
the refused set matches what cmd.exe changes. The shell-call scan now also
catches `**` keywords on process calls, a command whose first word names a
shell, `COMSPEC` and `os.posix_spawn`. Each of those has a sample it must catch.

Checked by hand, not in CI: the real CLI 2.1.251, started through
`claude_cli.run` from a folder with project `SessionStart` and
`UserPromptSubmit` hooks and with the API address on a closed local port, ran
both hooks under 0.4.2 and neither under this release. Not tested: whether a
folder's `env` block could have sent requests to another host, or whether a
`CLAUDE.md` there steered the judge. Both need files in the caller's folder,
which the CLI no longer reads.

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

Changed for callers. These changes are breaking, and the release should have
raised the minor version; 0.5.0 carries that bump:

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
