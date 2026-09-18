# Getting started

Articulate reads prose and tells you where it reads as machine-written or breaks
a plain-writing standard, with a line number for each finding. It runs on your
machine with no network call. This page takes you from install to a first check,
a first receipt, and an editor squiggle in about five minutes.

## Install

The core detector needs only Python 3.9 or newer and the standard library.

From PyPI (once published):

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

You get a one-line verdict per file, then a line for each finding:

```
[articulate] notes.md [flavored]: 2 high, 1 medium (blocked)  texture 41/100
  L3 [HIGH antithesis] not X but Y: This is not a tool, but a force.
  L7 [HIGH em-dash] em-dash: a long, winding sentence — you know the kind.
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

## Where to next

- [Walkthrough](walkthrough.md): a full pass over a real document, from screening
  to a rewrite to a committed audit record.
- [Features](features.md): every capability, what it gives you, and how to reach it.
- [CLI reference](cli.md): each command and flag.
- [Boundaries](boundaries.md): what a verdict and a receipt mean, and what they
  never claim. Read this before you rely on a receipt for anything.
