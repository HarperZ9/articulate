# Changelog

All notable changes to `articulate-writing` are recorded here. The package uses
semantic versioning. This is the package version. The detector ruleset carries its
own `RULESET_SEMVER`, which a receipt records so a replay knows which rules ran.

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
