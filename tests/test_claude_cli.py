"""The editor finds the claude CLI through ARTICULATE_CLAUDE_CLI or the PATH.

A bundled child process can start with a PATH that holds only System32, and
subprocess without a shell does not turn "claude" into claude.cmd on Windows. So
the editor resolves the CLI itself: the environment variable first, which must
be an absolute path, then the absolute PATH entries, with claude.exe ahead of
any batch shim. The current directory is never searched. No test here starts a
process; a fake runner records what would run, and a fake file table stands in
for the disk.
"""
import ntpath
import os
import posixpath

import pytest

from articulate import claude_cli, editor

_TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_tmp_cli")
_SECRET = "value-that-must-not-leak-7f3a"
# Written out by hand so the test does not borrow the implementation's own set.
_CMD_UNSAFE_EXPECTED = frozenset('"%^&|<>!\r\n')


class _Runner:
    def __init__(self, result=None, raises=None):
        self.calls, self.result, self.raises = [], result, raises
        self.prompt_file_text = None

    def __call__(self, argv, **kwargs):
        self.calls.append((list(argv), kwargs))
        path = argv[argv.index("--append-system-prompt-file") + 1]
        with open(path, encoding="utf-8") as fh:
            self.prompt_file_text = fh.read()
        if self.raises is not None:
            raise self.raises
        return self.result


class _Disk:
    """A fake file table that records every path the resolver probes."""

    def __init__(self, *paths):
        self.paths, self.probed = set(paths), []

    def __call__(self, path):
        self.probed.append(path)
        return path in self.paths


def _posix(*paths):
    return _Disk(*paths)


@pytest.fixture()
def work():
    os.makedirs(_TMP, exist_ok=True)
    yield _TMP
    import shutil
    shutil.rmtree(_TMP, ignore_errors=True)


def test_the_environment_variable_wins_over_the_path():
    disk = _posix("/opt/tools/claude", "/usr/bin/claude")
    env = {claude_cli.ENV_VAR: "/opt/tools/claude", "PATH": "/usr/bin"}
    assert claude_cli.resolve(env, disk, windows=False) == "/opt/tools/claude"


@pytest.mark.parametrize("value", ["claude", "./claude", "tools/claude"])
def test_a_relative_variable_is_refused_even_when_the_file_exists(value):
    disk = _posix(value, "/usr/bin/claude")
    with pytest.raises(claude_cli.ClaudeUnavailable) as info:
        claude_cli.resolve({claude_cli.ENV_VAR: value, "PATH": "/usr/bin"}, disk, windows=False)
    assert claude_cli.ENV_VAR in str(info.value)
    assert disk.probed == [], "a relative value must not be looked up at all"


@pytest.mark.parametrize("value", [r"claude.cmd", r".\claude.cmd", r"\tools\claude.exe"])
def test_a_windows_variable_needs_a_drive_or_share(value):
    disk = _Disk(value)
    with pytest.raises(claude_cli.ClaudeUnavailable):
        claude_cli.resolve({claude_cli.ENV_VAR: value}, disk, windows=True)


def test_a_windows_variable_without_a_suffix_gets_a_runnable_one():
    disk = _Disk(r"C:\tools\claude", r"C:\tools\claude.EXE")
    env = {claude_cli.ENV_VAR: r"C:\tools\claude", "PATHEXT": ".COM;.EXE;.BAT;.CMD"}
    assert claude_cli.resolve(env, disk, windows=True) == r"C:\tools\claude.EXE"


def test_the_path_is_searched_when_the_variable_is_unset_or_blank():
    disk = _posix("/usr/local/bin/claude")
    env = {"PATH": "/usr/bin:/usr/local/bin"}
    assert claude_cli.resolve(env, disk, windows=False) == "/usr/local/bin/claude"
    env[claude_cli.ENV_VAR] = "   "
    assert claude_cli.resolve(env, disk, windows=False) == "/usr/local/bin/claude"


def test_relative_and_empty_path_entries_are_never_probed():
    # "." and "" both mean the current directory, where a document repo could
    # plant its own claude. Only absolute entries count.
    disk = _Disk(r"C:\npm\claude.CMD")
    env = {"PATH": r".;;tools;C:\npm", "PATHEXT": ".COM;.EXE;.BAT;.CMD"}
    assert claude_cli.resolve(env, disk, windows=True) == r"C:\npm\claude.CMD"
    assert disk.probed and all(ntpath.isabs(p) and ntpath.splitdrive(p)[0] for p in disk.probed)
    pdisk = _posix("/bin/claude")
    assert claude_cli.resolve({"PATH": ".::bin:/bin"}, pdisk, windows=False) == "/bin/claude"
    assert all(posixpath.isabs(p) for p in pdisk.probed)


def test_claude_exe_later_on_the_path_beats_an_earlier_batch_shim():
    disk = _Disk(r"C:\npm\claude.CMD", r"C:\Users\u\.local\bin\claude.exe")
    env = {"PATH": r"C:\npm;C:\Users\u\.local\bin", "PATHEXT": ".COM;.EXE;.BAT;.CMD"}
    assert claude_cli.resolve(env, disk, windows=True) == r"C:\Users\u\.local\bin\claude.exe"


def test_a_batch_shim_is_the_fallback_and_scripts_are_not_runnable_targets():
    disk = _Disk(r"C:\npm\claude", r"C:\npm\claude.JS", r"C:\npm\claude.CMD")
    env = {"PATH": r"C:\npm", "PATHEXT": ".COM;.EXE;.BAT;.CMD;.JS;.PY"}
    assert claude_cli.resolve(env, disk, windows=True) == r"C:\npm\claude.CMD"


def test_a_missing_cli_is_a_closed_error_naming_the_variable():
    with pytest.raises(claude_cli.ClaudeUnavailable) as info:
        claude_cli.resolve({"PATH": "/usr/bin"}, _posix(), windows=False)
    msg = str(info.value)
    assert claude_cli.ENV_VAR in msg
    assert "installed" in msg and "logged in" in msg
    # The call sites catch RuntimeError, so the error stays closed there too.
    assert isinstance(info.value, RuntimeError)


def test_an_unresolvable_variable_fails_closed_without_echoing_its_value():
    env = {claude_cli.ENV_VAR: "/" + _SECRET, "PATH": "/usr/bin"}
    with pytest.raises(claude_cli.ClaudeUnavailable) as info:
        claude_cli.resolve(env, _posix("/usr/bin/claude"), windows=False)
    assert claude_cli.ENV_VAR in str(info.value)
    assert _SECRET not in str(info.value)


def test_every_call_sends_the_prompt_by_file_with_tools_and_mcp_off(work):
    # A long prompt in argv breaks both limits (about 32K characters for a
    # Windows command line, 128 KiB for one Linux argument), so the prompt
    # always travels in a file. The model gets no built-in tool and no MCP
    # server, since the document is untrusted input.
    prompt = "line one\nline two\n" + "x" * 40000
    runner = _Runner(result="done")
    env = {claude_cli.ENV_VAR: "/opt/tools/claude"}
    out = claude_cli.run(prompt, "doc", timeout=5, environ=env,
                         exists=_posix("/opt/tools/claude"), runner=runner,
                         windows=False, tmpdir=work)
    assert out == "done"
    (argv, kwargs), = runner.calls
    assert argv[:3] == ["/opt/tools/claude", "-p", claude_cli.FIXED_PROMPT]
    assert argv[3] == "--append-system-prompt-file"
    assert argv[5:] == ["--strict-mcp-config", "--tools", ""]
    assert runner.prompt_file_text == prompt
    assert max(len(a) for a in argv) < 1000
    assert kwargs == {"input": "doc", "timeout": 5}
    assert not os.path.exists(argv[4]), "the prompt file outlives the call"


def test_a_start_failure_is_a_closed_error_without_the_path(work):
    err = FileNotFoundError(2, "The system cannot find the file specified", _SECRET)
    runner = _Runner(raises=err)
    with pytest.raises(claude_cli.ClaudeUnavailable) as info:
        claude_cli.run("p", "t", environ={claude_cli.ENV_VAR: "/" + _SECRET},
                       exists=_posix("/" + _SECRET), runner=runner, windows=False,
                       tmpdir=work)
    assert _SECRET not in str(info.value)
    assert claude_cli.ENV_VAR in str(info.value)
    assert os.listdir(work) == [], "the prompt file outlives the start failure"


def test_the_unsafe_set_is_exactly_what_cmd_reinterprets():
    assert claude_cli.CMD_UNSAFE == _CMD_UNSAFE_EXPECTED


@pytest.mark.parametrize("suffix", [".cmd", ".CMD", ".bat", ".Bat"])
def test_batch_suffixes_are_recognised(suffix):
    assert claude_cli.is_batch(r"C:\npm\claude" + suffix, windows=True)
    assert not claude_cli.is_batch(r"C:\npm\claude" + suffix, windows=False)
    assert not claude_cli.is_batch(r"C:\npm\claude.exe", windows=True)


def test_a_batch_shim_gets_a_fixed_argv(work):
    # cmd.exe re-parses a .cmd file's arguments and cuts one at its first
    # newline, so nothing from the prompt may travel in argv.
    prompt = 'first line\nsecond "line" with %PATH% & ^ | < > !'
    runner = _Runner(result="done")
    claude_cli.run(prompt, "doc", environ={"PATH": r"C:\npm"},
                   exists=_Disk(r"C:\npm\claude.CMD"), runner=runner, windows=True,
                   tmpdir=work)
    (argv, _), = runner.calls
    assert argv[0] == r"C:\npm\claude.CMD"
    assert runner.prompt_file_text == prompt
    assert not any(set(a) & _CMD_UNSAFE_EXPECTED for a in argv[1:])


@pytest.mark.parametrize("suffix", [".cmd", ".bat"])
@pytest.mark.parametrize("char", sorted(_CMD_UNSAFE_EXPECTED))
def test_a_batch_shim_with_an_unsafe_path_fails_closed(work, suffix, char):
    runner = _Runner(result="done")
    cli = "C:\\a" + char + "b\\claude" + suffix
    with pytest.raises(claude_cli.ClaudeUnavailable) as info:
        claude_cli.run("p", "t", environ={claude_cli.ENV_VAR: cli}, exists=_Disk(cli),
                       runner=runner, windows=True, tmpdir=work)
    assert runner.calls == []
    assert claude_cli.ENV_VAR in str(info.value)
    assert os.listdir(work) == [], "the prompt file outlives the refusal"


def test_editor_reports_a_missing_cli_through_its_closed_error(monkeypatch, capsys, work):
    monkeypatch.delenv(claude_cli.ENV_VAR, raising=False)
    monkeypatch.setenv("PATH", "")
    assert editor.ClaudeUnavailable is claude_cli.ClaudeUnavailable
    monkeypatch.setattr(claude_cli.subprocess, "Popen", _Runner(raises=AssertionError("started")))
    with pytest.raises(editor.ClaudeUnavailable) as info:
        editor.claude_call("instructions", "text")
    assert claude_cli.ENV_VAR in str(info.value)
    doc = os.path.join(work, "d.md")
    with open(doc, "w", encoding="utf-8") as fh:
        fh.write("Some prose.\n")
    editor.judge(doc)
    out = capsys.readouterr().out
    assert "model layer unavailable" in out and claude_cli.ENV_VAR in out


def test_the_old_editor_hooks_are_gone():
    # editor.CLAUDE and editor.run no longer steer the model call. Keeping either
    # would let a caller patch it and still reach the real CLI.
    assert not hasattr(editor, "CLAUDE")
    assert not hasattr(editor, "run")
