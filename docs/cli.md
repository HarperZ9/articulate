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

- `--profile P`: force a register profile.
- `--mode M`: a writing mode, for example `memo/argue`. A mode wins over profile
  inference.
- `--gate`: exit 1 when any file is blocked or cannot be screened, otherwise 0.
- `--json`: a machine-readable payload with findings, cadence, and the verdict.
- `--sarif`: SARIF 2.1.0 for GitHub code scanning, Azure DevOps, and reviewdog.
- `--verbose`: expand the LOW advisories to line numbers.
- `--spans`: a per-paragraph verdict, so a mixed-authorship block is flagged in
  place.
- `--content-free`: omit every verbatim substring and exact offset from the
  console, JSON, and SARIF output.

## score

Print the graded texture score and the verdict, without the per-finding lines.

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
- `--spans`: record the per-paragraph verdicts in the receipt.
- `--redact drop`: a content-free audit receipt with the matched substring and the
  offsets dropped.
- `--redact hash`: as `drop`, keeping a hash of the match for an equality check
  against a known string. See the [hash caveat](boundaries.md#hash-mode).
- `--reviewer NAME`: record who screened it. Without it, the CI actor fills the
  field if one is set, and otherwise it stays unset.

## verify

Replay a receipt against text and return the verdict.

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
  was screened, or could not be read. A sub-threshold or stale-ruleset
  `Unverifiable` is reported, and it does not fail the gate.
- `--json`: the summary as JSON.

## modes

List the available writing modes.

```bash
articulate modes
```

## Editor commands

The editor layer is a separate entry point, because it needs a model backend.

```bash
python -m articulate.editor --judge FILE
python -m articulate.editor --fix FILE [--out OUT] [--passes N] [--mode M]
python -m articulate.editor --polish FILE [--out OUT] [--bar 1-5] [--mode M]
python -m articulate.editor --review FILE
```

## Exit codes

- `check --gate`: 1 if any file is blocked or unscreenable, else 0.
- `verify`: 0 Match, 1 Drift, 2 Unverifiable.
- `audit --reverify --gate`: 1 on a real integrity break, else 0.
- `articulate.bench`: the number of misclassified files, so 0 is a perfect run.
