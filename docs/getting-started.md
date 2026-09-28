# Getting started

Articulate reads prose and names the patterns that cost a reader something,
with a line number for each finding. The checks run on your machine with no
network call. Model editing follows the selected backend's privacy policy.
Install the package, run a check, create a receipt and connect your editor with
the commands below.

## Install

The core checks need only Python 3.9 or newer and the standard library.

From PyPI:

```bash
pip install articulate-writing
```

From source:

```bash
git clone https://github.com/HarperZ9/articulate
cd articulate
pip install -e .
```

Three console commands are installed: `articulate` (the CLI), `articulate-lsp`
(the editor language server) and `articulate-mcp` (a standard-library MCP
server). A second MCP server, `articulate.mcp_server`, uses the MCP Python SDK
and needs one extra package:

```bash
pip install "articulate-writing[mcp]"
```

## Your first check

Point it at a Markdown or text file. The repository's `examples/notes.md` is a
four-line note:

```bash
articulate check notes.md
```

You get one line per file, a line for each HIGH or MEDIUM finding, and a closing
line on what the findings do not show:

```
[articulate] notes.md [flavored]: 0 high, 1 medium, 4 low, gate ok
  L3 [MEDIUM unsupported-authority] authority appeal, no citation in the sentence: It is important to note that studies show the second run was cleaner, and we need more data in orde
[articulate] These findings name prose patterns and where they occur. They do not show who or what wrote the text, and no finding or count is a basis for an accusation.
```

Read it this way:

- The gate, `ok` or `blocked`, is the only pass-or-block signal. It depends on
  the profile shown in brackets. Under the strict `essay` profile the same file
  is blocked by the MEDIUM finding, and by the reply opener on line 1, which
  `essay` promotes. "It is important to note that" is a LOW note under every
  profile, and "in order to" is another.
- Each finding carries a tier. HIGH is a narrow tier, such as an interface
  markup token or a hidden character inside Latin text. MEDIUM rules carry a
  cited reader cost and block under a strict profile. LOW notes never block
  unless a profile promotes one, and show only with `--verbose`. The house style
  blocks only under a house profile you choose and shows elsewhere only with
  `--house-notes`.
- `articulate score` adds per-rule counts and, at 250 words or more, density per
  1,000 words with an interval. No output scores the text as a whole.

## Gate a commit or a build

`--gate` sets the exit code, so a checker can block a change:

```bash
articulate check docs/*.md --gate
```

The command exits 1 when any file is blocked under its profile, and 0 otherwise.
A profile decides which tiers block. The default profile blocks HIGH only; an
essay or a procedure profile blocks HIGH and MEDIUM; `house` and `house-essay`
add the house style. See [Features](features.md#profiles) for the list.

## Your first receipt

A receipt is a re-derivable record of a check. Anyone with the same text and
the same ruleset recomputes the same findings, with no network and no trust in
whoever issued it first:

```bash
articulate receipt notes.md > notes.receipt.json
articulate verify notes.receipt.json notes.md
```

`verify` prints one of three words and sets the exit code:

- `Match` (exit 0): the same text under the same ruleset re-derives identically.
- `Drift` (exit 1): the re-derived findings differ from the receipt.
- `Unverifiable` (exit 2): the ruleset moved or the text hash mismatches, so
  nothing is asserted.

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
loopback Ollama and deterministic editing. Direct plan and submit calls still
perform local preparation and validation. The switch cannot control the calling
host's conversation or model.

The CLI also supports Anthropic, the Claude CLI and OpenAI-compatible endpoints.
Automatic selection records unavailable backends and continues to a usable path,
ending with deterministic editing. See the [backend configuration reference](cli.md#backend-configuration)
for selection order, credentials and privacy.

## Where to next

- [Walkthrough](walkthrough.md): a full pass over a real document, from screening
  to a rewrite to a committed audit record.
- [Features](features.md): every capability, what it gives you, and how to reach it.
- [CLI reference](cli.md): each command and flag.
- [Fairness audit](fairness-audit.md): how the rules treat different writers.
- [Boundaries](boundaries.md): what each output means and never means. Read this
  before you rely on any of them.
