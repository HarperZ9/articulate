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
  findings), per-rule counts, the gate, `findings` (`has_findings` when any HIGH
  or MEDIUM finding exists), density (with `measures`, what it counts),
  passive-voice and adverb rates and the `does_not_prove` line. Two keys are
  deprecated and leave in package 0.7.0: `clean`, true when no HIGH or MEDIUM
  finding exists, whose equal is `findings == "no_findings"`; and
  `blocking_count`, the same number as `blocking`. `clean` does not say whether
  the gate passed: a text with one MEDIUM finding under the default profile
  reads `clean: false` and `gate: ok`. Read `gate` or `blocking` for the gate.
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
  console, JSON, and SARIF output. The repeated-phrase and repeated-opener notes
  are keyed by category, since their rule ids would name the phrase or opener.

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

The main CLI exposes model editing and deterministic fixes:

```bash
articulate judge FILE --backend auto --json
articulate fix FILE --backend none --out edited.md
articulate polish FILE --backend ollama --json
```

All three accept `--backend auto|host|sampling|anthropic|claude-cli|openai|ollama|none`,
`--mode M`, `--profile P`, `--out OUT` and `--json`. The legacy editor also
accepts `--local-only` to enable the same restriction as the environment switch.
Sampling requires an MCP
session that advertised sampling; a plain CLI cannot request the host's model
through that transport. `host` returns a plan for a calling model to complete.
Without a model, `none` makes conservative mechanical fixes and reports remaining
findings; its judge reports local findings and rule reasons. Inspect the gate
and refused spans even when a call succeeds.

The legacy entry point remains available:

```bash
python -m articulate.editor --judge FILE --backend auto
python -m articulate.editor --fix FILE --backend none --out edited.md
python -m articulate.editor --polish FILE --backend ollama --mode memo/argue
python -m articulate.editor --review FILE     # --advise FILE is the same
python -m articulate.editor --fix FILE --local-only --backend none
```

### plan and submit

Use a calling agent's model without a separate model account:

```bash
articulate plan FILE [--mode M] [--profile P] [--goal fix|polish|judge]
                     [--is-html] [--is-tex]
articulate submit FILE REWRITE --plan PLAN_ID [--scores JSON] [--model NAME]
```

`plan` writes JSON with the local findings, their reasons, the hardened model
instructions, masked text, protected spans and a plan ID. Give the model those
instructions and the masked text. Save its output as `REWRITE`, then submit it
with the unchanged original `FILE` and the plan ID. Keep mask tokens intact.
The optional model name is caller-reported attribution. `--scores` accepts a
JSON object with `before` and `after` objects, each holding integer scores from
1 to 5 for `concreteness`, `commitment`, `economy`, `rhythm` and `restatable`.
For polish, these scores support the quality non-regression check. Without
them, quality is reported as `unassessed`; gate and span checks still apply.
Mode, profile, goal and mask settings are carried in the plan ID and need not
be repeated on submission.

Submission checks the source and plan configuration against the plan ID,
restores masks and runs the meaning guard. Protected numbers, URLs, citations,
code, math and quotations must survive; refused spans retain their original
wording and report a reason. The result includes accepted text, gates before
and after, per-rule deltas and a host receipt. A matching plan ID binds inputs;
it is not authentication or proof of semantic equivalence. A plan and its
result can contain source text, so store them with the document's protections.

### Backend configuration

Use `--backend` to select a backend for one call, or set `ARTICULATE_BACKEND`
for the process. The default is `auto`.

- `host`: the calling model uses `plan` and `submit`; text follows the calling
  host's model policy.
- `sampling`: the MCP client must advertise sampling at initialization; text
  goes to the host's selected model.
- `anthropic`: `ANTHROPIC_API_KEY`, with optional `ARTICULATE_MODEL`; text goes
  to Anthropic's Messages API. The default model is `claude-sonnet-5`.
- `claude-cli`: an installed, authenticated Claude CLI, with optional absolute
  `ARTICULATE_CLAUDE_CLI` path; text goes to its provider.
- `openai`: `ARTICULATE_OPENAI_BASE_URL`, `ARTICULATE_OPENAI_API_KEY` and
  `ARTICULATE_MODEL`; text goes to the configured compatible endpoint.
- `ollama`: `ARTICULATE_OLLAMA_URL` and `ARTICULATE_LOCAL_MODEL`; text goes to
  the configured Ollama server.
- `none`: no account or model needed; no model or network call.

In MCP, `auto` uses sampling when advertised, otherwise returning a host edit
plan before trying a separately billed backend. The calling model can complete
that plan with `edit_submit`. In the plain CLI, automatic selection tries
configured Anthropic, the Claude CLI, configured OpenAI-compatible endpoints,
Ollama and `none`, recording failures before continuing. Explicit backend
selection tries the requested route first, then the automatic fallback chain.
Use local-only mode to constrain where fallback can send text.

`OPENAI_API_KEY` is accepted for the default OpenAI address. A custom compatible
endpoint, including vLLM or LM Studio, uses `ARTICULATE_OPENAI_API_KEY`; an
unrelated OpenAI key is not forwarded to it. `ARTICULATE_MODEL` is required
for every OpenAI-compatible endpoint, including the default OpenAI address.

Ollama defaults to `http://127.0.0.1:11434`. With `ARTICULATE_LOCAL_MODEL` unset,
it inspects installed models through `/api/tags`, preferring `qwen3:8b`,
`qwen2.5:7b`, `llama3.2:3b`, then `gemma3:4b`, then the first installed model.
It never pulls a model.

Set `ARTICULATE_LOCAL_ONLY=1` to restrict editor backend selection to Ollama on a
loopback address and `none`. Hosted backends, the `host` selection and sampling
are refused before a connection. Direct `plan` and `submit` remain available:
they perform local preparation and validation without a model or network call.
The switch cannot control how a calling host uses the text or chooses its model.
For deterministic editing alone, use `--backend none`.

For the Claude CLI, `ARTICULATE_CLAUDE_CLI` must be an absolute executable path;
otherwise Articulate searches absolute PATH entries and skips the current
folder. Authentication is checked before the model call. A credit, login or
rate-limit failure records a reason and allows automatic selection to continue.
To repair an account failure, use `claude login` with the intended subscription
account, configure `ANTHROPIC_API_KEY`, or choose Ollama or `none`.

The CLI child runs in a private empty temporary folder with user settings only,
using `--setting-sources user --strict-mcp-config --tools ""`. Document-folder
settings do not load. On Windows, `NoDefaultCurrentDirectoryInExePath=1` keeps
the npm shim's `node` lookup on PATH. An older CLI that rejects these flags is
reported as unavailable. This isolation does not make a hosted call local.

## Exit codes

- `check --gate`: 1 if any file is blocked or unscreenable, else 0.
- `verify`: 0 Match, 1 Drift, 2 Unverifiable.
- `audit --reverify --gate`: 1 on a real integrity break, else 0.
- `desk`: 0 whenever the run completes, 2 on unreadable or binary input.
- `disclose`: 2 when the statement is refused.
- `process verify`: 0 when intact, 1 when broken, 3 when missing.
- `desk`: 2 on an unknown `--venue`.
- `python -m articulate.editor`: 2 when the file is missing or cannot be read.
  Local-only mode selects loopback Ollama or deterministic editing.
- `python -m articulate.fairness --release-check`: 0 when the ruleset is
  unchanged since the published one or every gate passes; 1 when a gate fails
  and no accepted override names the current ruleset, or a receipt is missing
  or malformed.
- `articulate.bench`: the number of failed expectations, so 0 means every one held.
