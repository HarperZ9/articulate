"""Find and start the claude CLI for the editor layer.

The judge, fix and polish commands run the model through the local `claude` CLI
in headless mode. Two things break a bare "claude" on Windows. A process that
a bundler or an MCP host starts can inherit a PATH that holds only System32.
And subprocess without a shell asks CreateProcess for the name, which appends
.exe and never finds the claude.cmd shim that an npm install puts on the PATH.

So the CLI path comes from ARTICULATE_CLAUDE_CLI when that variable is set.
Otherwise shutil.which searches the PATH, and on Windows it tries each PATHEXT
suffix, so it finds claude.cmd. When neither gives a runnable file, the caller
gets ClaudeUnavailable, whose message names the variable. No message here
prints the value of the variable or the resolved path.

A .cmd or .bat file runs under cmd.exe, which parses its arguments a second
time. It cuts an argument at the first newline and reads % ^ & | < > ! as
commands, so a prompt in argv would arrive cut short, and text taken from the
document could run as a command. For a batch file the prompt goes into a
temporary file passed with --append-system-prompt-file, and argv holds only a
fixed line and that file path. Every argument is checked before the start, and
a path that holds one of those characters is refused.
"""
import os
import shutil
import subprocess
import sys
import tempfile

ENV_VAR = "ARTICULATE_CLAUDE_CLI"
DEFAULT_NAME = "claude"
BATCH_SUFFIXES = (".cmd", ".bat")
CMD_UNSAFE = frozenset('"%^&|<>!\r\n')
BATCH_PROMPT = ("Apply the instructions in your system prompt to the document "
                "on standard input.")

_MISSING = (f"claude CLI not found. The claude CLI must be installed and logged in "
            f"(run `claude login`). Put it on PATH, or set {ENV_VAR} to the full "
            f"path of the claude executable.")
_BAD_VAR = (f"{ENV_VAR} is set, but it does not name a runnable file. Set it to "
            f"the full path of the claude executable, which must be installed and "
            f"logged in.")
_UNSAFE_BATCH = (f"the claude CLI resolves to a Windows batch file, and its path or "
                 f"arguments hold characters that cmd.exe would reinterpret. Set "
                 f"{ENV_VAR} to the full path of a native claude executable.")


class ClaudeUnavailable(RuntimeError):
    """The model backend could not be reached (missing CLI, credits, auth, rate limit)."""


def resolve(environ=None, which=None):
    """Return the path of the claude CLI, or raise ClaudeUnavailable."""
    env = os.environ if environ is None else environ
    which = shutil.which if which is None else which
    configured = (env.get(ENV_VAR) or "").strip()
    if configured:
        found = which(configured)
        if not found:
            raise ClaudeUnavailable(_BAD_VAR)
        return found
    found = which(DEFAULT_NAME)
    if not found:
        raise ClaudeUnavailable(_MISSING)
    return found


def is_batch(path, windows=None):
    """True when Windows would start this file through cmd.exe."""
    windows = os.name == "nt" if windows is None else windows
    return windows and os.path.splitext(path)[1].lower() in BATCH_SUFFIXES


def _write_prompt_file(prompt, tmpdir):
    fd, path = tempfile.mkstemp(prefix="articulate-prompt-", suffix=".txt", dir=tmpdir)
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
        fh.write(prompt)
    return path


def _remove_quietly(path):
    try:
        os.remove(path)
    except OSError as exc:
        # A leftover temp file is not worth failing a finished model call. Say so,
        # since the file holds the prompt.
        print(f"[editor] could not remove a temporary prompt file ({exc.strerror})",
              file=sys.stderr)


def run(prompt, text, timeout=600, environ=None, which=None,
        runner=None, windows=None, tmpdir=None):
    """Run `claude -p` with the prompt and the document on stdin.

    Returns the CompletedProcess. Raises ClaudeUnavailable when the CLI cannot
    be found or started, and lets subprocess.TimeoutExpired through.
    """
    cli = resolve(environ, which)
    runner = subprocess.run if runner is None else runner
    prompt_file = None
    try:
        if is_batch(cli, windows):
            prompt_file = _write_prompt_file(prompt, tmpdir)
            argv = [cli, "-p", BATCH_PROMPT, "--append-system-prompt-file", prompt_file]
            if any(CMD_UNSAFE.intersection(arg) for arg in argv):
                raise ClaudeUnavailable(_UNSAFE_BATCH)
        else:
            argv = [cli, "-p", prompt]
        try:
            return runner(argv, input=text, capture_output=True, text=True,
                          encoding="utf-8", timeout=timeout)
        except OSError as exc:
            # strerror carries the reason; the filename, which is the path, stays out.
            reason = exc.strerror or type(exc).__name__
            raise ClaudeUnavailable(
                f"the claude CLI could not be started ({reason}). It must be "
                f"installed and logged in; {ENV_VAR} can name its full path.") from exc
    finally:
        if prompt_file is not None:
            _remove_quietly(prompt_file)
