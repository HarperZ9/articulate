# Getting started

Articulate reads prose and names the patterns that cost a reader something,
with a line number for each finding. It runs on your
machine with no network call. This page takes you from install to a first check,
a first receipt, and an editor squiggle in about five minutes.

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

Two console commands are installed: `articulate` (the CLI) and `articulate-lsp`
(the editor language server). The MCP server surface needs one extra package:

```bash
pip install "articulate-writing[mcp]"
```

## Your first check

Point it at a Markdown or text file:

```bash
articulate check notes.md
```

You get one line per file, then a line for each HIGH or MEDIUM finding:

```
[articulate] notes.md [flavored]: 1 high, 3 medium, 4 low, gate blocked
  L1 [HIGH chat-interface-text] chat reply opener that hands over a deliverable: Certainly! Here is the summary you asked for:
  L3 [MEDIUM throat-clearing] throat-clearing opener: ... It is important to note that ...
  L3 [MEDIUM unsupported-authority] authority appeal, no citation nearby: ... studies show ...
```

Read it this way:

- The gate, `ok` or `blocked`, is the only pass-or-block signal. It depends on
  the profile shown in brackets.
- Each finding carries a tier. HIGH is a narrow tier, such as text left over from
  a chat interface. MEDIUM rules carry a cited reader cost and block under a
  strict profile. LOW notes never block and show only with `--verbose`; they
  include the house style, which blocks only under a house profile you choose.
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
in the host's MCP configuration. The editor tools (`judge`, `fix`, `polish`)
run the `claude` CLI, and a host often starts servers with a short PATH, so
name the CLI by its absolute path:

```json
{
  "mcpServers": {
    "articulate": {
      "command": "articulate-mcp",
      "env": { "ARTICULATE_CLAUDE_CLI": "C:\\Users\\you\\.local\\bin\\claude.exe" }
    }
  }
}
```

On macOS or Linux the value looks like `/home/you/.local/bin/claude`. Without
the variable, the editor searches the absolute PATH entries and never the
current directory. The CLI runs in a private empty folder with your user
settings only, so a document folder's `.claude/settings.json` never loads. The
check tools (`check`, `score`) need no CLI.

## Where to next

- [Walkthrough](walkthrough.md): a full pass over a real document, from screening
  to a rewrite to a committed audit record.
- [Features](features.md): every capability, what it gives you, and how to reach it.
- [CLI reference](cli.md): each command and flag.
- [Fairness audit](fairness-audit.md): how the rules treat different writers.
- [Boundaries](boundaries.md): what each output means and never means. Read this
  before you rely on any of them.
