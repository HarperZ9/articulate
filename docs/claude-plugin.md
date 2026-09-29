# Claude plugin

Articulate Writing is the Claude plugin form of Articulate. It gives Claude Code
local checks, the `edit_plan`/`edit_submit` host-edit protocol, offline editor
entrypoints, status and doctor tools. Its `prose-review` and `prose-edit` skills
explain how to use those tools. The checker runs on your computer and sends the
text nowhere; Claude reads the text as part of your conversation. The server has
automated Windows and Linux test coverage. The plugin's own README, which is
also its listing text,
covers install, example prompts, the privacy policy and troubleshooting: see
`claude-plugin/README.md`.

## Install

This plugin targets the 0.5.2 package on the maintenance release line. It bundles
the package source. Build from the matching package tag for release use; use
`--dev` for a local test build before that tag exists.

The plugin needs Python 3.9 or later, runnable as `python3`, and nothing else:
it carries its own copy of the package source, which uses only the standard
library. Restart Claude Code after the install, then run `/mcp`; the
`articulate` server shows as connected.

To install a local build of this repository, build it as
[Build the plugin from this repository](#build-the-plugin-from-this-repository)
shows, then add the build folder as a marketplace:

```bash
claude plugin marketplace add ./build/claude-plugin
claude plugin install articulate-writing@articulate-writing
```

## What it runs

Claude Code starts one process for the session:

```text
python3 -I -S -B -X utf8 ${CLAUDE_PLUGIN_ROOT}/server/serve.py
```

`-I` keeps Python from reading `PYTHONPATH` and the user site-packages folder,
and from putting the working folder on the module path. `-S` skips the site
module, so no site-packages folder is searched and no `.pth` file there runs,
including one in an activated virtual environment: the server runs on the
standard library and the plugin's own copy of Articulate, which `serve.py` puts
first on the path. `-B` stops Python from writing bytecode into the plugin
folder. `-X utf8`
makes the standard streams UTF-8, and the server switches them to UTF-8 itself
as well, because Windows reads a pipe in the console code page by default.

The plugin sets two variables for that process only:

| Variable | Value | Effect |
|:-|:-|:-|
| `ARTICULATE_MCP_TOOLS` | `local` | Lists the local tool set and restricts editor tools to host plans or deterministic work. Explicit external backends return a named refusal. |
| `ARTICULATE_LOCAL_ONLY` | `1` | Refuses network, subprocess and sampling backends before execution. Host planning/submission still works. |

The server opens no network connection, starts no other program, opens none of
your files and writes no file. The test suite runs every tool marked local with
sockets, process creation and file access made to fail, and checks that no
module keeps a copy of the text after a call. It also starts the built server
with the declared command under Python's audit hooks and calls every tool,
listed and hidden: the session fails on any file opened for writing or outside
the plugin folder and the Python installation, and on any process, network or
file-change event.

## Host editing and offline editor tools

`edit_plan` returns `masked_text`, instructions, findings, protected spans and a
`plan_id`. The calling model follows those instructions and writes a masked
rewrite. `edit_submit` takes the exact original `text`, that `rewrite` and
`plan_id`; it restores masks, checks protected spans and returns accepted `text`,
`refused` changes, before/after gates, rule deltas and a receipt with backend
`host`. A refusal can restore the original paragraph while `ok` remains true,
so callers must inspect `refused` and use the returned text.

Both tools work with `ARTICULATE_LOCAL_ONLY=1`. They add no separate network
exposure: the text is already in the calling model's conversation. The guard is
lexical, not proof of semantic equivalence, quality or factual correctness. The
plan token binds content and settings through a checksum. It provides no
signature or proof of authority.

In the plugin, `fix`, `judge` and `polish` accept `auto` or `host` to prepare a
host plan, or `none` for deterministic checks and edits. They refuse explicit
external backends, including negotiated sampling, before execution. Outside the
plugin, the package can use optional backends under its own configuration.

`check` retains the 0.5.1 `clean`, `verdict`, `texture_score`, HIGH/MEDIUM hits,
LOW advisory count and cadence fields, with the plugin's bounded hit output.
`score` returns the 0.5.1 heuristic score and structural rates. Neither exposes
the unreleased density or fairness outputs.

## Tool titles and hints

Tools declare titles and all four MCP behavior hints. In the plugin environment,
they are read-only, not destructive, idempotent and closed-world: the plugin
edits no file and invokes no external backend. Hints describe behavior; they do
not prove the truth or semantic quality of an edit. `src/articulate/tool_meta.py`
holds the metadata shared by both servers.

## Build the plugin from this repository

```bash
python scripts/build_claude_plugin.py build/claude-plugin --dev
python scripts/smoke_claude_plugin.py build/claude-plugin
```

The build copies the files git tracks in `claude-plugin/`, the package modules
the server can import, the package's files that are not Python source, and
`LICENSE` into the output folder. The modules the server can import are every
module reachable from `local_mcp` and the package `__init__` through any import
statement, one inside a function included, so the command line, the LSP server
and unrelated tools stay out. An untracked or ignored file, such as a
`.env`, never ships. The build then
checks the result: file count and sizes, text-only files, names that work on
Windows and macOS, no file named or shaped like a credential, the manifest
fields, a single server variable, a README of at least 40 words with a Privacy
Policy section that matches `PRIVACY.md`, and the skill front matter. It exits 1
and lists each problem when a check fails.

Use `--dev` when testing changes before their package tag exists. Do not publish
a development build as a package release.

Without `--dev` the build is a release build. Before it writes anything, it
refuses untracked or changed files in the folders it copies, and it refuses
package code that differs from the release its version names (the tag
`v<version>`), because Claude Code keeps a user on a plugin until the version
string changes. The version tag must be present locally and resolve to a commit;
fetch that tag before a release build. Use `--dev` only for a local test build.
It prints the source commit it built from.

The smoke script starts the built server with the command and arguments in
`.mcp.json` and prints one line for each check, so it is the quick test on a new
machine. It looks `python3` up on absolute `PATH` entries outside the working
folder and the plugin folder; `--command` names another interpreter.

To check the manifest with Claude Code itself:

```bash
claude plugin validate --strict build/claude-plugin/.claude-plugin/plugin.json
```

Set `CLAUDE_CONFIG_DIR` to an empty folder first if you want the check to leave
your own Claude Code configuration alone.

## Future publication

Publication is outside this development handoff. After review and a matching
package release, the maintainer can follow this sequence:

1. Release the package version first. The plugin's `version` must equal the
   package version, and a test holds the two equal. A release build refuses
   package code that differs from that release.
2. From a clean checkout of the release commit, build into a clone of the plugin
   repository with `--replace`, which rewrites every file the build owns and
   keeps `.git`.
3. Run the smoke script on the build, commit with the source commit the build
   printed in the message, and push.

Each user's Claude Code starts whatever the plugin repository's default branch
holds at their next session after an update, so that branch needs protection
with a required review.

The plugin folder is the root of its own repository. Claude's directory holds a
Python server in a plugin that sits in a subfolder of a larger repository for a
reviewer, and a plugin at a repository root avoids that.
