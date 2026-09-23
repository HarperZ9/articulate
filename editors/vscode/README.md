# Articulate for VS Code

Inline writing-quality and AI-tell diagnostics, powered by the Articulate
language server. The server runs locally with no network call; this extension is
a thin client that launches it.

## Requirements

The `articulate` Python package must be importable by the interpreter in
`articulate.pythonPath` (default `python`):

```bash
pip install articulate-writing   # or: pip install -e /path/to/articulate
```

## Settings

- `articulate.enable`: turn the server on or off.
- `articulate.pythonPath`: the Python interpreter that has `articulate`.
- `articulate.profile`: force a register profile (e.g. `essay`, `research`,
  `procedure`). Empty auto-detects from a `writing-profile:` tag, a glob in the
  project's `.articulate.json`, or the file path.

The server reads the nearest `.articulate.json` above each open file, so project
terminology rules and domain profiles show inline too. A malformed config shows
as one diagnostic on the first line, naming the file and the reason.

## Build

```bash
npm install
npm run compile      # tsc -> out/extension.js
npx vsce package     # optional: produce a .vsix
```

Diagnostics map HIGH tells to warnings, MEDIUM to information, and LOW advisories
to hints, each carrying its rule id.
