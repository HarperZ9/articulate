"""The editor finds the claude CLI through ARTICULATE_CLAUDE_CLI or the PATH.

A bundled child process can start with a PATH that holds only System32, and
subprocess without a shell does not turn "claude" into claude.cmd on Windows. So
the editor resolves the CLI itself: the environment variable first, then
shutil.which, then a closed error that names the variable. No test here starts
a model; a fake runner records what would run.
"""
import os
import pathlib
import re
import shutil
import sys

import pytest

from articulate import claude_cli, editor

_SRC = pathlib.Path(__file__).resolve().parents[1] / "src" / "articulate"
_TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_tmp_cli")
_SECRET = "value-that-must-not-leak-7f3a"


class _Runner:
    def __init__(self, result=None, raises=None):
        self.calls, self.result, self.raises = [], result, raises
        self.prompt_file_text = None

    def __call__(self, argv, **kwargs):
        self.calls.append((list(argv), kwargs))
        if "--append-system-prompt-file" in argv:
            path = argv[argv.index("--append-system-prompt-file") + 1]
            with open(path, encoding="utf-8") as fh:
                self.prompt_file_text = fh.read()
        if self.raises is not None:
            raise self.raises
        return self.result


def _which(table):
    return lambda name: table.get(name)


@pytest.fixture()
def work():
    os.makedirs(_TMP, exist_ok=True)
    yield _TMP
    shutil.rmtree(_TMP, ignore_errors=True)


def test_the_environment_variable_wins_over_the_path():
    which = _which({"/opt/tools/claude": "/opt/tools/claude", "claude": "/usr/bin/claude"})
    env = {claude_cli.ENV_VAR: "/opt/tools/claude"}
    assert claude_cli.resolve(environ=env, which=which) == "/opt/tools/claude"


def test_the_path_is_searched_when_the_variable_is_unset_or_blank():
    which = _which({"claude": r"C:\npm\claude.CMD"})
    assert claude_cli.resolve(environ={}, which=which) == r"C:\npm\claude.CMD"
    blank = {claude_cli.ENV_VAR: "   "}
    assert claude_cli.resolve(environ=blank, which=which) == r"C:\npm\claude.CMD"


def test_a_missing_cli_is_a_closed_error_naming_the_variable():
    with pytest.raises(claude_cli.ClaudeUnavailable) as info:
        claude_cli.resolve(environ={}, which=_which({}))
    msg = str(info.value)
    assert claude_cli.ENV_VAR in msg
    assert "installed" in msg and "logged in" in msg
    # The call sites catch RuntimeError, so the error stays closed there too.
    assert isinstance(info.value, RuntimeError)


def test_an_unresolvable_variable_fails_closed_without_echoing_its_value():
    env = {claude_cli.ENV_VAR: _SECRET}
    with pytest.raises(claude_cli.ClaudeUnavailable) as info:
        claude_cli.resolve(environ=env, which=_which({"claude": "/usr/bin/claude"}))
    assert claude_cli.ENV_VAR in str(info.value)
    assert _SECRET not in str(info.value)


def test_run_uses_the_resolved_path_and_never_a_shell():
    runner = _Runner(result="done")
    env = {claude_cli.ENV_VAR: "/opt/tools/claude"}
    out = claude_cli.run("line one\nline two", "doc", timeout=5, environ=env,
                         which=_which({"/opt/tools/claude": "/opt/tools/claude"}),
                         runner=runner, windows=False)
    assert out == "done"
    (argv, kwargs), = runner.calls
    assert argv == ["/opt/tools/claude", "-p", "line one\nline two"]
    assert kwargs.get("shell", False) is False
    assert kwargs["input"] == "doc" and kwargs["timeout"] == 5


def test_no_source_module_runs_a_shell():
    for path in _SRC.glob("*.py"):
        assert not re.search(r"shell\s*=\s*True", path.read_text(encoding="utf-8")), path.name


def test_a_start_failure_is_a_closed_error_without_the_path():
    err = FileNotFoundError(2, "The system cannot find the file specified", _SECRET)
    runner = _Runner(raises=err)
    with pytest.raises(claude_cli.ClaudeUnavailable) as info:
        claude_cli.run("p", "t", environ={}, which=_which({"claude": _SECRET}),
                       runner=runner, windows=False)
    assert _SECRET not in str(info.value)
    assert claude_cli.ENV_VAR in str(info.value)


def test_a_batch_shim_gets_the_prompt_through_a_file(work):
    # cmd.exe re-parses a .cmd file's arguments and cuts one at its first
    # newline, so a multi-line prompt must not travel in argv.
    prompt = 'first line\nsecond "line" with %PATH% & ^ | < > !'
    runner = _Runner(result="done")
    claude_cli.run(prompt, "doc", environ={}, which=_which({"claude": r"C:\npm\claude.cmd"}),
                   runner=runner, windows=True, tmpdir=work)
    (argv, _), = runner.calls
    assert argv[:3] == [r"C:\npm\claude.cmd", "-p", claude_cli.BATCH_PROMPT]
    assert argv[3] == "--append-system-prompt-file"
    assert runner.prompt_file_text == prompt
    assert not any(set(a) & claude_cli.CMD_UNSAFE for a in argv[1:])
    assert not os.path.exists(argv[4]), "the prompt file outlives the call"


def test_a_batch_shim_with_an_unsafe_path_fails_closed(work):
    runner = _Runner(result="done")
    with pytest.raises(claude_cli.ClaudeUnavailable) as info:
        claude_cli.run("p", "t", environ={}, which=_which({"claude": r"C:\a&b\claude.cmd"}),
                       runner=runner, windows=True, tmpdir=work)
    assert runner.calls == []
    assert claude_cli.ENV_VAR in str(info.value)
    assert os.listdir(work) == [], "the prompt file outlives the refusal"


def test_editor_reports_a_missing_cli_through_its_closed_error(monkeypatch, capsys, work):
    monkeypatch.delenv(claude_cli.ENV_VAR, raising=False)
    monkeypatch.setattr(claude_cli.shutil, "which", lambda name, **kw: None)
    assert editor.ClaudeUnavailable is claude_cli.ClaudeUnavailable
    monkeypatch.setattr(claude_cli.subprocess, "run", _Runner(raises=AssertionError("started")))
    with pytest.raises(editor.ClaudeUnavailable) as info:
        editor.claude_call("instructions", "text")
    assert claude_cli.ENV_VAR in str(info.value)
    doc = os.path.join(work, "d.md")
    with open(doc, "w", encoding="utf-8") as fh:
        fh.write("Some prose.\n")
    editor.judge(doc)
    out = capsys.readouterr().out
    assert "model layer unavailable" in out and claude_cli.ENV_VAR in out


@pytest.mark.skipif(os.name != "nt", reason="cmd.exe batch parsing exists only on Windows")
def test_a_real_cmd_shim_receives_the_whole_prompt(monkeypatch, work):
    # End to end through cmd.exe: a stand-in claude.cmd that echoes back the
    # prompt file and stdin it received.
    echo = os.path.join(work, "echo.py")
    with open(echo, "w", encoding="utf-8") as fh:
        fh.write("import sys\na = sys.argv[1:]\n"
                 "p = open(a[a.index('--append-system-prompt-file') + 1], encoding='utf-8').read()\n"
                 "sys.stdout.write(p + '|' + sys.stdin.read())\n")
    shim = os.path.join(work, "claude.cmd")
    with open(shim, "w", encoding="utf-8") as fh:
        fh.write(f'@echo off\r\n"{sys.executable}" "%~dp0echo.py" %*\r\n')
    monkeypatch.setenv(claude_cli.ENV_VAR, shim)
    prompt = 'one\ntwo "three" %PATH% & four'
    r = claude_cli.run(prompt, "the document", timeout=60)
    assert r.returncode == 0, r.stderr
    assert r.stdout == prompt + "|the document"
