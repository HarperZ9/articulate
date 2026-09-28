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

## modes

List the available writing modes.

```bash
articulate modes
```

## Editor commands

The main CLI exposes model editing and deterministic fixes:

```bash
articulate judge FILE --backend auto --json
articulate fix FILE --backend none --out edited.md
articulate polish FILE --backend ollama --json
```

All three accept `--backend auto|host|sampling|anthropic|claude-cli|openai|ollama|none`,
`--mode M`, `--profile P`, `--out OUT` and `--json`. Sampling requires an MCP
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
python -m articulate.editor --review FILE
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

Set `ARTICULATE_LOCAL_ONLY=1` to permit only Ollama on a loopback address and
`none`. The editor backend selector refuses hosted routes, host and sampling
before a connection. Direct `plan` and `submit` calls perform local checks only;
they do not control the calling host's handling of a document already in its
conversation. For deterministic editing alone,
use `--backend none`.

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
- `articulate.bench`: the number of misclassified files, so 0 is a perfect run.
