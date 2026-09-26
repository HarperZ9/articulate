# CLI reference

The command is `articulate`. With no file, a command reads standard input. A
profile is chosen by an explicit flag, then an in-file `writing-profile:` tag,
then the file path, then the default.

## check

Screen one or more files and report the findings.

```bash
articulate check [FILE ...] [--profile P] [--mode M] [--gate] [--json]
                 [--sarif] [--verbose] [--spans] [--content-free]
```

- `--profile P`: force a profile. `house` and `house-essay` apply the house style;
  no path selects them for you.
- `--mode M`: a writing mode, for example `memo/argue`. A mode wins over profile
  inference.
- `--gate`: exit 1 when any file is blocked or cannot be screened, otherwise 0.
- `--json`: a machine-readable payload with the findings, whether each one
  blocks, per-rule counts, the gate, density, cadence statistics and the
  `does_not_prove` line.
- `--sarif`: SARIF 2.1.0 for GitHub code scanning, Azure DevOps, and reviewdog.
  Each rule's help text carries its reader-cost reason and the does-not-prove
  line, and each result records the profile.
- `--verbose`: expand the LOW advisories to line numbers.
- `--spans`: per-paragraph counts by rule, in document order. No paragraph gets
  a gate, a label or a score; see
  [Boundaries](boundaries.md#no-output-is-an-authorship-finding).
- `--content-free`: omit every verbatim substring and exact offset from the
  console, JSON, and SARIF output.

## score

Print the gate, the word count, density per 1,000 words with an exact interval
(shown at 250 words or more) and per-rule counts.

```bash
articulate score [FILE ...] [--profile P] [--mode M]
```

## receipt

Emit a re-derivable receipt as JSON on standard output.

```bash
articulate receipt [FILE ...] [--profile P] [--mode M] [--spans]
                   [--redact {none,drop,hash}] [--reviewer NAME]
```

- `--mode M`: screen under a writing mode, as `check --mode` does. The receipt
  records the mode in a `mode` field beside the mode's base profile, and `verify`
  replays it under the same mode. A mode wins over `--profile`.
- `--spans`: record the per-paragraph counts in the receipt.
- `--redact drop`: a content-free audit receipt with the matched substring and the
  offsets dropped.
- `--redact hash`: as `drop`, keeping a hash of the match for an equality check
  against a known string. See the [hash caveat](boundaries.md#hash-mode).
- `--reviewer NAME`: record who screened it. Without it, the CI actor fills the
  field if one is set, and otherwise it stays unset.

## verify

Replay a receipt against text.

```bash
articulate verify RECEIPT FILE
```

The exit code is 0 for `Match`, 1 for `Drift`, and 2 for `Unverifiable`.

## audit

Query a directory of committed receipts locally.

```bash
articulate audit [PATH ...] [--days N] [--reverify] [--gate] [--json]
```

- `PATH`: receipt files or directories. The default is the current directory.
- `--days N`: the recent-activity window for the summary. The default is 30.
- `--reverify`: replay each receipt against its source file, and report `Match`,
  `Drift`, `source-changed`, `source-missing`, or `source-unreadable`.
- `--gate`: with `--reverify`, exit 1 when any source drifted, changed since it
  was screened, or could not be read. A stale-ruleset `Unverifiable` is
  reported, and it does not fail the gate.
- `--json`: the summary as JSON.

## modes

List the available writing modes.

```bash
articulate modes
```

## process

Keep a local, opt-in record of your own process. See the
[feature reference](features.md#the-process-record).

```bash
articulate process init DOC [--track] [--opt-in words,diff,time,snapshot]
articulate process draft DOC
articulate process note DOC (--text-file F | --label L) [--shareable]
articulate process source DOC CITATION [--shareable]
articulate process assist DOC --tool T --verb {generated,drafted,edited,translated}
                          [--sections S,...] [--model M] [--version V]
                          [--source-type CODE --languages SRC,TGT]
articulate process input DOC --method M [--sections S,...]
articulate process review DOC --role R --reviewed W --outcome O [--editorial] [--name N]
articulate process anchor DOC [--commit ID | --token-sha256 H]
articulate process continue DOC --reason R
articulate process export DOC [--include F,...] [--reveal N[=FILE]] [--contributions F]
articulate process verify (DOC | DOC.process-summary.json)
```

`export --include` names the fields a default export leaves out: `words`, `diff`,
`time`, `labels`, `citations`, `review_names` and `input_method`.

## disclose

Write a statement of tool use and contributor credit from the process log.

```bash
articulate disclose DOC [--template {general,pip}] [--contributions F]
                    [--include input_method] [--claim SENTENCE]
```

It exits 2 and writes nothing when the request would misstate the log.

## desk

Prepare the questions a reviewer should ask, inside the document and across the
field.

```bash
articulate desk FILE [--venue {none,paper,course}] [--disclosure F] [--author] [--json]
```

## The fairness harness

```bash
python -m articulate.fairness MANIFEST [--out RECEIPT]
python -m articulate.fairness --release-check DIR
```

## Editor commands

The editor layer is a separate entry point, because it needs a model backend.

```bash
python -m articulate.editor --judge FILE
python -m articulate.editor --fix FILE [--out OUT] [--passes N] [--mode M] [--profile P]
python -m articulate.editor --polish FILE [--out OUT] [--bar 1-5] [--mode M] [--profile P]
python -m articulate.editor --review FILE
```

These commands run the model through the `claude` CLI, which must be installed
and logged in. The editor looks for it in two places. If `ARTICULATE_CLAUDE_CLI`
is set, its value must be the absolute path of the CLI, such as
`C:\Users\you\.local\bin\claude.exe`. Otherwise the editor searches the
absolute entries on the PATH. It prefers `claude.exe` in any entry, and on
Windows it falls back to the `claude.cmd` shim from an npm install. The search
for the CLI skips the current directory. Set the variable when the editor runs
from a process whose PATH does not hold the CLI, such as an MCP host or a
bundled app. When neither place gives a runnable file, the command stops with
an error that names the variable.

The model session gets the prompt in a temporary file, the document on stdin,
no tools and no project settings. Every call passes
`--setting-sources user --strict-mcp-config --tools ""`. The CLI starts in a
new empty folder under the temporary directory, which the editor removes after
the call. It never starts in your current directory. `claude -p` skips the
workspace trust prompt and reads `.claude/settings.json` from its working
directory, so a document folder that holds one could otherwise run its hooks.
On Windows the child also gets `NoDefaultCurrentDirectoryInExePath=1`, so the
npm shim's `node` comes from the PATH.

The editor is tested with CLI version 2.1.251. The first version that accepts
all four flags is unknown. An older CLI that rejects one of them stops the
command with an error that says to upgrade.

## Exit codes

- `check --gate`: 1 if any file is blocked or unscreenable, else 0.
- `verify`: 0 Match, 1 Drift, 2 Unverifiable.
- `audit --reverify --gate`: 1 on a real integrity break, else 0.
- `desk`: 0 whenever the run completes, 2 on unreadable or binary input.
- `disclose`: 2 when the statement is refused.
- `python -m articulate.fairness --release-check`: 1 when the release gate fails.
- `articulate.bench`: the number of failed expectations, so 0 means every one held.
