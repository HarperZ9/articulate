# CLI reference

The command is `articulate`. With no file, a command reads standard input. A
profile is chosen by an explicit flag, then an in-file `writing-profile:` tag,
then a glob in the project config, then the file path, then the default.

`check`, `score`, `receipt`, and `compare` read the nearest `.articulate.json`
above each file. `--config PATH` names the config file to use, and `--config
none` turns discovery off. See [Project config](features.md#project-config).

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
articulate receipt [FILE ...] [--profile P] [--spans]
                   [--redact {none,drop,hash}] [--reviewer NAME]
```

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

## compare

Run the meaning guard on an original and a rewrite. Each surface invariant is
reported as kept, dropped, added, or changed, with its line and column in each
file. See [the meaning guard](features.md#the-meaning-guard).

```bash
articulate compare ORIGINAL REWRITE [--json] [--gate] [--show-kept]
                   [--freeze TERM] [--allow-change KINDS]
```

- `--json`: the full report, with every item, its status, and both locations.
- `--gate`: exit 1 when an invariant that may not change was dropped, added, or
  changed.
- `--show-kept`: list the kept invariants too.
- `--freeze TERM`: a term that must survive verbatim. Repeat the flag for more.
- `--allow-change KINDS`: kinds that may change without failing the gate, as a
  comma list such as `number,entity`, or `all`. The kinds are `code`, `math`,
  `url`, `citation`, `quote`, `freeze`, `number`, `modal`, `scope`, `negation`,
  and `entity`.
- `--config PATH`: the project config whose freeze terms join `--freeze`. By
  default the nearest one above the original file is read.

## config

Show which project config applies to a path, the profile it resolves to, and
what the config sets.

```bash
articulate config [PATH] [--config PATH] [--json]
```

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

`--fix` and `--polish` take the meaning-guard flags:

- `--allow-change KINDS`: let these invariant kinds change. Without it, a rewrite
  that changes any invariant is refused and the previous text is kept.
- `--freeze TERM`: a term every rewrite must keep verbatim. Repeat for more. A
  freeze term is also a protected span, so the model never sees it.
- `--unprotect KINDS`: let the model edit block quotes or quoted material
  (`quotes`, `blockquotes`). Code, math, links, citations, and freeze terms
  always stay protected.
- `--config PATH`: the project config whose freeze terms and protect switches
  apply. By default the nearest one above the file is read.
- `--explain [text|json]`: after the run, print the change report: each changed
  sentence before and after, the detector findings that sentence carried, the
  findings left in the new sentence, the meaning-guard rows for the pair, and
  every refused candidate with its reason. `text` is the default.

## Exit codes

- `check --gate`: 1 if any file is blocked or unscreenable, else 0.
- `verify`: 0 Match, 1 Drift, 2 Unverifiable.
- `audit --reverify --gate`: 1 on a real integrity break, else 0.
- `compare --gate`: 1 if an invariant that may not change moved, 2 if a file
  cannot be read, else 0.
- `articulate.bench`: the number of misclassified files plus the number of domain
  corpus mismatches, so 0 is a perfect run. `articulate.bench_domains` runs the
  domain corpus alone.
