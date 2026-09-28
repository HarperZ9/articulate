# Claude plugin

Articulate Writing is the Claude plugin form of Articulate. It gives Claude Code
the local `check` and `score` tools, a status and a doctor tool, and a
`prose-review` skill that tells Claude when to run the checks and how to report
them. The checker runs on your computer and sends the text nowhere; Claude reads
the text as part of your conversation. The plugin is tested in Claude Code on
Windows and Linux. The plugin's own README, which is also its listing text,
covers install, example prompts, the privacy policy and troubleshooting: see
`claude-plugin/README.md`.

## Install

```bash
claude plugin marketplace add HarperZ9/articulate-writing
claude plugin install articulate-writing@articulate-writing
```

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
| `ARTICULATE_MCP_TOOLS` | `local` | Lists only the tools that read the text and nothing else. A hidden tool called by name returns an error that names this variable. |
| `ARTICULATE_LOCAL_ONLY` | `1` | Makes a hosted tool refuse before any network call, even if one were listed. |

The server opens no network connection, starts no other program, opens none of
your files and writes no file. The test suite runs every tool marked local with
sockets, process creation and file access made to fail, and checks that no
module keeps a copy of the text after a call. It also starts the built server
with the declared command under Python's audit hooks and calls every tool,
listed and hidden: the session fails on any file opened for writing or outside
the plugin folder and the Python installation, and on any process, network or
file-change event.

## Why the editor tools stay out

The Python package's `judge`, `fix` and `polish` tools send the text to a hosted
model through the `claude` command line, under your own Claude login. Inside
Claude Code the model you are talking to can already rewrite a passage, so the
plugin gives it the checker and leaves the rewriting to it. That keeps the
plugin's surface to one local process with no network path. To use the editor
tools, install the package with `pip install articulate-writing` and register
`articulate-mcp` as [Getting started](getting-started.md#from-an-mcp-host)
describes.

## Tool titles and hints

Every tool in both MCP servers declares a title and all four behavior hints.
The local tools are read-only, not destructive, idempotent and closed-world.
The hosted tools are open-world and marked as not read-only, so a host asks
before each call: the text leaves the machine and the call spends your quota.
They edit none of your files. The `claude` command line saves its own record of
each session on disk unless it is started with `--no-session-persistence`, and
the package does not pass that option yet. `src/articulate/tool_meta.py` holds
the one table both servers read.

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
and the fairness and desk tools stay out. An untracked or ignored file, such as a
`.env`, never ships. The build then
checks the result: file count and sizes, text-only files, names that work on
Windows and macOS, no file named or shaped like a credential, the manifest
fields, a single server variable, a README of at least 40 words with a Privacy
Policy section that matches `PRIVACY.md`, and the skill front matter. It exits 1
and lists each problem when a check fails.

Without `--dev` the build is a release build. Before it writes anything, it
refuses untracked or changed files in the folders it copies, and it refuses
package code that differs from the release its version names (the tag
`v<version>`), because Claude Code keeps a user on a plugin until the version
string changes. It prints the source commit it built from.

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

## Publish a new version

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
