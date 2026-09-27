# CLI reference

The command is `articulate`. With no file, a command reads standard input. A
profile is chosen by an explicit flag, then an in-file `writing-profile:` tag,
then the file path, then the default. The editor commands resolve it the same
way.

## check

Screen one or more files and report the findings.

```bash
articulate check [FILE ...] [--profile P] [--mode M] [--gate] [--json]
                 [--sarif] [--verbose] [--spans] [--content-free] [--house-notes]
```

- `--profile P`: force a profile. `house` and `house-essay` apply the house style;
  no path selects them for you.
- `--mode M`: a writing mode, for example `memo/argue`. A mode wins over profile
  inference.
- `--gate`: exit 1 when any file is blocked or cannot be screened, otherwise 0.
- `--json`: a machine-readable payload with the findings, whether each one
  blocks and its `reason` and `reason_source`, `blocking` (the count of blocking
  findings), per-rule counts, the gate, density (with `measures`, what it
  counts), passive-voice and adverb rates and the `does_not_prove` line. The
  `clean` key (no HIGH or MEDIUM finding) is deprecated: it echoes the retired
  verdict, keeps its value in 0.6.0 and is removed in 0.7.0. Read `blocking` or
  `gate`.
- `--sarif`: SARIF 2.1.0 for GitHub code scanning, Azure DevOps, and reviewdog.
  Each rule's help text carries its reader-cost reason and the does-not-prove
  line, and each result records the profile.
- `--verbose`: expand the LOW advisories to line numbers and print each
  finding's reader-cost reason under it. A LOW finding that the profile promotes
  to blocking always prints. Every console run ends with the does-not-prove line,
  a passing gate included.
- `--house-notes`: also report the house style's patterns as LOW notes marked
  `house style` (SARIF: `house: true`). Without it no profile but `house` and
  `house-essay` shows them.
- `--spans`: per-paragraph counts by rule, in document order. No paragraph gets
  a gate, a label or a score; see
  [Boundaries](boundaries.md#no-output-is-an-authorship-finding).
- `--content-free`: omit every verbatim substring and exact offset from the
  console, JSON, and SARIF output.

## score

Print the gate, the word count, density per 1,000 words with an exact interval
(shown at 250 words or more) and per-rule counts.

```bash
articulate score [FILE ...] [--profile P] [--mode M] [--house-notes]
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
articulate process verify (DOC | SUMMARY.json)
```

`export --include` names the fields a default export leaves out: `words`, `diff`,
`time`, `labels`, `citations`, `review_names` and `input_method`. `continue` works
only on a broken log. `verify` reads a file as a summary when its `schema` field
says so, whatever its name; on a document it reports `intact` (exit 0),
`broken` (exit 1) or `missing` (exit 3). A missing log is no record: "an absent or
short record shows nothing about a writer". `verify`, `export` and `disclose`
each print that limits line.

## disclose

Write a statement of tool use and contributor credit from the process log.

```bash
articulate disclose DOC [--template {general,pip}] [--contributions F]
                    [--include input_method] [--claim SENTENCE]
```

It exits 2 and writes nothing when the log is missing or broken, or when the
request would misstate the log.

## desk

Prepare the questions a reviewer should ask, inside the document and across the
field.

```bash
articulate desk FILE [--venue {none,paper,course}] [--disclosure F] [--author] [--json]
```

An unknown `--venue` exits 2 with the list of venues. The JSON output carries a
`does_not_prove` line.

## The fairness harness

```bash
python -m articulate.fairness MANIFEST [--root DIR] [--out RECEIPT] [--jobs N]
python -m articulate.fairness --release-check DIR [--published FILE]
```

`--root` names the folder the corpus files sit in when they are not beside the
manifest. `--jobs N` scans the documents in N processes and computes every
statistic in one, so the receipt is byte-identical to a single-process run; a
test pins this.

The release check reads the published-ruleset record, `published-ruleset.json`
beside `DIR` unless `--published` names another. A commit after each release
updates that record; the release commit never edits it. When the current ruleset
fingerprint equals the published one and the record names an earlier package
version than the one being built, the check passes and prints
`ruleset unchanged since X (FINGERPRINT); gates not re-run`. A record that names
the version being built never skips the gates.

Otherwise it reads `DIR/<fingerprint>*.json`, exactly one receipt per listed
manifest; a second receipt from the same manifest fails the check. Each
receipt's stored G1 and G2 flags must agree with its stored numbers (the raw G1
gap is recomputed from its counts; stored G2 states, within-group gaps and
layout counts are trusted), every gate recomputed from its rows must pass, and
when `DIR/SHA256SUMS` exists each receipt must match its pin there
(`sha256sum -c SHA256SUMS` checks the same thing). A changed ruleset also needs
a receipt from a corpus pre-registered to confirm it: PERSUADE 2.0 confirms only
`sha256:46e1485cd2c98caa`.

A maintainer can let a changed ruleset publish while a gate fails by committing
`DIR/<fingerprint>.override.json` with `ruleset_version`, `reason` and
`decided_by`. The check accepts it only when no gate row fails in the new receipt
that did not fail in the published ruleset's own receipt, a row that receipt
lacked included; it prints that comparison, the reason and every failure. It
refuses an override whose comparison base is not a sound receipt of the
published ruleset itself, and an override never excuses a malformed receipt.

## Editor commands

The editor layer is a separate entry point, because it needs a model backend.

```bash
python -m articulate.editor --judge FILE
python -m articulate.editor --fix FILE [--out OUT] [--passes N] [--mode M] [--profile P]
python -m articulate.editor --polish FILE [--out OUT] [--bar 1-5] [--mode M] [--profile P]
python -m articulate.editor --review FILE     # --advise FILE is the same
python -m articulate.editor --local-only --judge FILE   # refused, exit 3
```

Each command sends the full text to a hosted model and says so before it
starts. With `ARTICULATE_LOCAL_ONLY=1` set, or `--local-only` passed, every one
exits 3 before any subprocess starts; the `judge`, `fix` and `polish` tools of
both MCP servers return an error whose note names the switch. The switch fails
closed: any value other than an empty one, `0`, `false`, `no` or `off` turns it
on. `articulate --help` prints the map of local and
hosted commands.

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
- `process verify`: 0 when intact, 1 when broken or missing.
- `python -m articulate.fairness --release-check`: 0 when the ruleset is
  unchanged since the published one or every gate passes; 1 when a gate fails
  and no accepted override names the current ruleset, or a receipt is missing
  or malformed.
- `articulate.bench`: the number of failed expectations, so 0 means every one held.
