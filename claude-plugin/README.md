# Articulate Writing

Articulate Writing checks prose on your computer before you ship it. It names
writing patterns such as filler openers, stacked hedges and unsupported
superlatives, shows the line and the words where each one occurs, and gives the
reason each one costs a reader. Use it on documentation, READMEs, release notes,
commit messages and drafts. The checker runs on your computer and sends the text
nowhere; Claude still reads the text as part of your conversation.

## What you get

- `check` returns each HIGH and MEDIUM finding with its rule, tier, line, span
  and reason, a count of LOW advisories (`advisory_count`), and a gate (`ok` or
  `blocked`) under the default profile with the count of blocking findings. A
  long document returns the first 50 span records by default and never more
  than about 30,000 characters of them; the gate and the per-rule counts always
  cover every finding.
- `score` returns per-rule counts, density per 1,000 words with an interval at
  250 words or more, and the passive-voice and adverb rates.
- `articulate.status` reports the server version, and `articulate.doctor`
  reports a setup summary you can paste into an issue.
- The `prose-review` skill tells Claude when to run the checks, how to report
  them, and to propose an edit only where you want one.

## Requirements

- Claude Code. The plugin is tested in Claude Code on Windows and Linux. Cowork
  also loads plugins, and this plugin has not been tested there. Chat on
  claude.ai loads the skill and does not start the local checker.
- Python 3.9 or later, runnable as `python3`. Nothing else to install: the
  plugin carries its own copy of the checker, which uses only the Python
  standard library.

## Install

```bash
claude plugin marketplace add HarperZ9/articulate-writing
claude plugin install articulate-writing@articulate-writing
```

Restart Claude Code, then run `/mcp`. The `articulate` server shows as
connected.

## Try it

- "Check the prose in docs/guide.md and explain each blocking finding with its
  reason."
- "Score this release note and tell me which rules fire most often." (Paste the
  note after the request.)
- "Review my commit message draft for filler and hedging, and suggest edits only
  for the blocking findings." (Paste the draft after the request.)

## What it runs

| What | Detail |
|:-|:-|
| Processes | One: `python3 -I -S -B -X utf8` running the plugin's `server/serve.py`. Claude Code starts it with the session and stops it at the end. It runs the first `python3` on your PATH, which is a virtual environment's Python when you have one activated. |
| Files | It loads its own source from the plugin folder and the Python standard library, and no installed package: `-S` skips every site-packages folder. It opens none of your files and writes no file: no log, no cache, no bytecode. |
| Network | None. It opens no connection. |
| Other programs | None. |
| Settings | It sets `ARTICULATE_MCP_TOOLS=local` and `ARTICULATE_LOCAL_ONLY=1` for its own process and changes no Claude setting. |

The `articulate-writing` Python package also has editor tools (`judge`, `fix`
and `polish`) that send text to a hosted model through the `claude` command
line. The plugin does not list them, and the two settings above turn them off.

## Privacy Policy

Last updated: 2026-09-27. This policy covers the Articulate Writing plugin for
Claude. It is also published at
https://github.com/HarperZ9/articulate/blob/main/claude-plugin/PRIVACY.md.

**Data collected.** The plugin reads only the text Claude passes to one of its
tools in a call. It does not read your files, your conversation history or
Claude's memory. It collects no account details, usage statistics or telemetry.

**Use and storage.** The plugin checks the text in memory on your computer and
returns the result to Claude. It writes nothing to disk: no log, no cache and no
copy of the text.

**Third-party sharing.** None. The plugin opens no network connection and starts
no other program, so it sends the text to no one, the plugin's author included.
Claude sends your conversation to Anthropic under your Claude account's terms,
and that conversation includes any text you ask Claude to check. Anthropic's
privacy policy and your account settings govern that data.

**Retention.** The plugin keeps nothing after a call returns. The text and the
result remain in your Claude conversation, which your Claude account settings
govern. Claude Code also saves a copy of the conversation on your computer, tool
calls and results included, and its own settings govern that copy.

**Contact.** Ask a question about this policy or the plugin at
https://github.com/HarperZ9/articulate/issues. Report a security problem
privately as SECURITY.md describes.

**Changes.** A change to this policy ships in a new plugin version with a new
date above, and the changelog at
https://github.com/HarperZ9/articulate/blob/main/CHANGELOG.md lists it.

## Troubleshooting

**The `articulate` server shows as failed in `/mcp`.** Claude Code could not
start `python3`, or the Python it found is too old. Check with `python3
--version` in a terminal.

- Windows, "Python was not found" or a Microsoft Store window: install the
  Python install manager, which provides `python3`. The traditional python.org
  installer provides `python` and no `python3`. Restart Claude Code afterwards.
- macOS, a prompt to install the command line developer tools: accept it, or
  install Python from python.org or Homebrew. The plugin has not been tested on
  macOS yet.
- Linux: install the `python3` package with your distribution's package
  manager.
- "needs Python 3.9 or later": install a newer Python 3 and restart Claude
  Code.

**The tools are listed and a call fails.** Ask Claude to run the Articulate
doctor tool. It reports the plugin version, the Python version and which tools
are listed, with no file paths. Paste that report into an issue.

## Limits

- The rules are written for English prose. Text in other languages gets few or
  no findings, and a clean result there says nothing about the writing.
- These findings name prose patterns and where they occur. They do not show who
  or what wrote the text, and no finding or count is a basis for an accusation.

## Support and license

Report a problem or ask a question at
https://github.com/HarperZ9/articulate/issues.

Articulate Writing is source-available under the Functional Source License 1.1
with the MIT future license (`FSL-1.1-MIT`): each release becomes available
under the MIT license on the second anniversary of its release. See `LICENSE`.
