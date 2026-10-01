# Getting started

Articulate reads prose and tells you where it reads as machine-written or breaks
a plain-writing standard, with a line number for each finding. The detector runs on your
machine with no network call. Model editing follows the selected backend's
privacy policy. Install the package, run a check, create a receipt and connect
your editor with the commands below.

## Install

Version 0.7.0 is prepared for release. Its Windows x64 native ZIP and binary MCPB
packages include a Python runtime; see the [native package guide](native-local-package.md).
They include no model. A connected client supplies rewritten text through
`edit_plan` and `edit_submit`, using its own model account and permissions.

The Python package and source plugin need Python 3.9 or newer and the standard
library. The following commands select 0.7.0 after publication.

From PyPI:

```bash
pip install articulate-writing==0.7.0
```

From source:

```bash
git clone --branch v0.7.0 https://github.com/HarperZ9/articulate
cd articulate
pip install -e .
```

Three console commands are installed: `articulate` (the CLI), `articulate-lsp`
(the language server) and `articulate-mcp` (the stdio MCP server). They work from
a bare install. The optional FastMCP surface, `python -m articulate.mcp_server`,
uses the `mcp` extra:

```bash
pip install "articulate-writing[mcp]==0.7.0"
```

## Your first check

Point it at a Markdown or text file:

```bash
articulate check notes.md
```

You get a one-line verdict per file, then a line for each finding:

```
[articulate] notes.md [flavored]: 2 high, 1 medium (blocked)  texture 41/100
  L3 [HIGH antithesis] not X but Y: This is not a tool, but a force.
  L7 [HIGH em-dash] em-dash: a clause break using an em dash.
  L9 [MEDIUM register-word] AI-register vocabulary: we leverage synergy here.
```

Read it this way:

- The verdict is `clean`, `flagged`, or `unverifiable`. A `flagged` verdict means
  a HIGH or MEDIUM finding is present. An `unverifiable` verdict means the text is
  under the 30-word floor, where there are too few words to call it clean.
- Each finding carries a tier. HIGH marks the banned devices and named register
  words. MEDIUM marks strong frontier-model tells. LOW is an advisory that can fire
  on innocent prose, so it never blocks and shows only with `--verbose`.
- The texture score is a graded 0 to 100 read of machine texture. It is a signal,
  and it never changes the clean or flagged verdict.

## Gate a commit or a build

`--gate` sets the exit code, so a checker can block a change:

```bash
articulate check docs/*.md --gate
```

The command exits 1 when any file is blocked under its profile, and 0 otherwise.
A profile decides which tiers block. The default profile blocks HIGH only; an
essay or a procedure profile blocks HIGH and MEDIUM. See
[Features](features.md#register-profiles) for the profile list.

## Your first receipt

A receipt is a re-derivable record of a verdict. Anyone with the same text and
the same ruleset recomputes the same findings, with no network and no trust in
whoever issued it first:

```bash
articulate receipt notes.md > notes.receipt.json
articulate verify notes.receipt.json notes.md
```

`verify` prints one of three words and sets the exit code:

- `Match` (exit 0): the same text under the same ruleset re-derives identically.
- `Drift` (exit 1): the re-derived findings differ from the receipt.
- `Unverifiable` (exit 2): the ruleset moved, the text hash mismatches, or the
  text is below the signal floor, so nothing is asserted.

## An editor squiggle

The language server speaks standard LSP over stdio, so any LSP client drives it.
A minimal Neovim registration:

```lua
vim.lsp.start({ name = "articulate", cmd = { "articulate-lsp" },
  filetypes = { "markdown", "text", "tex" } })
```

For VS Code, a thin client that launches the same command is in
`editors/vscode/`. See [Features](features.md#surfaces) for every surface.

## From an MCP host

`articulate-mcp` serves the tools over stdio from a bare install. Register it
in your host's MCP configuration:

```json
{
  "mcpServers": {
    "articulate": { "command": "articulate-mcp" }
  }
}
```

Ask the host to call `fix`, `judge` or `polish`. If the client advertised MCP
sampling, Articulate can request the host's model. Otherwise it returns a plan:
the calling model follows its instructions and calls `edit_submit` with the
original text, rewrite and plan ID. Articulate checks protected spans, retains
refused spans and returns the accepted text with a gate and host receipt. The
same pair is available directly as `edit_plan` and `edit_submit`.

This path needs no second model account. The host can still send text to a
remote model under its own policy. Plans and edit results contain source text;
keep them private when the source is private.

## Edit without a model

Mechanical editing works with no account, model or network:

```bash
articulate fix notes.md --backend none --out edited.md
articulate judge notes.md --backend none --json
```

The deterministic backend fixes only conservative mechanical cases and reports
remaining findings. It does not provide model quality scores or establish that
a document is accurate. Inspect the gate and refusal list before accepting it.

## Use an installed local model

With Ollama running and a model already installed:

```bash
articulate fix notes.md --backend ollama --out edited.md
```

Set `ARTICULATE_LOCAL_MODEL` to choose the installed model. Articulate never
downloads one. Set `ARTICULATE_LOCAL_ONLY=1` to restrict editor selection to
loopback Ollama and deterministic editing. This refuses host and hosted editor
paths before a connection. It does not control the calling host's conversation.

The CLI also supports Anthropic, the Claude CLI and OpenAI-compatible endpoints.
Automatic selection records unavailable backends and continues to a usable path,
ending with deterministic editing. See the [backend configuration reference](cli.md#backend-configuration)
for selection order, credentials and privacy.

## Where to next

- [Walkthrough](walkthrough.md): a full pass over a real document, from screening
  to a rewrite to a committed audit record.
- [Features](features.md): every capability, what it gives you, and how to reach it.
- [CLI reference](cli.md): each command and flag.
- [Boundaries](boundaries.md): what a verdict and a receipt mean, and what they
  never claim. Read this before you rely on a receipt for anything.
