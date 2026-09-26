"""Real processes through claude_cli: stand-in shims, a planted file, a timeout.

Each stand-in writes back what it received, so a test can check that the prompt
file, the fixed flags and the document arrive intact. No test here reaches a
model. The Windows tests go through cmd.exe and run in the windows-latest CI job.
"""
import ast
import os
import pathlib
import shutil
import stat
import subprocess
import sys
import time

import pytest

from articulate import claude_cli

_SRC = pathlib.Path(__file__).resolve().parents[1] / "src" / "articulate"
_TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_tmp_cli_proc")
_WINDOWS = os.name == "nt"
_ECHO = ("import sys\na = sys.argv[1:]\n"
         "p = open(a[a.index('--append-system-prompt-file') + 1], encoding='utf-8').read()\n"
         "sys.stdout.write(repr(a[a.index('--strict-mcp-config'):]) + '|' + p + '|' + sys.stdin.read())\n")
_SLEEP = "import time\ntime.sleep(30)\n"


@pytest.fixture()
def work():
    os.makedirs(_TMP, exist_ok=True)
    yield _TMP
    shutil.rmtree(_TMP, ignore_errors=True)


def _write(path, text, newline=None):
    with open(path, "w", encoding="utf-8", newline=newline) as fh:
        fh.write(text)
    return path


def _stand_in(folder, script, name="claude"):
    """A claude stand-in that runs `script` under this Python, as a child."""
    os.makedirs(folder, exist_ok=True)
    body = _write(os.path.join(folder, "body.py"), script)
    if _WINDOWS:
        return _write(os.path.join(folder, name + ".cmd"),
                      f'@echo off\r\n"{sys.executable}" "{body}" %*\r\n', newline="")
    # Not exec: the shell stays the parent, so a timeout has a grandchild to stop.
    shim = _write(os.path.join(folder, name), f'#!/bin/sh\n"{sys.executable}" "{body}" "$@"\necho\n')
    os.chmod(shim, os.stat(shim).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return shim


def _decoy(folder):
    """A file named like the CLI that must never be picked or run."""
    os.makedirs(folder, exist_ok=True)
    name = "claude.cmd" if _WINDOWS else "claude"
    path = _write(os.path.join(folder, name), "@echo PLANTED\r\n" if _WINDOWS else "#!/bin/sh\necho PLANTED\n")
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)
    return path


def test_a_claude_planted_in_the_current_directory_never_wins(monkeypatch, work):
    # Windows searches the current directory ahead of PATH unless
    # NoDefaultCurrentDirectoryInExePath is set, and Windows does not set it.
    repo = os.path.join(work, "repo")
    _decoy(repo)
    real = _stand_in(os.path.join(work, "bin"), _ECHO)
    monkeypatch.delenv("NoDefaultCurrentDirectoryInExePath", raising=False)
    monkeypatch.delenv(claude_cli.ENV_VAR, raising=False)
    monkeypatch.chdir(repo)
    monkeypatch.setenv("PATH", os.pathsep.join([".", "", os.path.dirname(real)]))
    assert os.path.normcase(claude_cli.resolve()) == os.path.normcase(real)
    r = claude_cli.run("the prompt", "the document", timeout=60)
    assert "PLANTED" not in r.stdout
    assert r.stdout.rstrip("\n").endswith("|the prompt|the document")
    monkeypatch.setenv("PATH", os.pathsep.join([".", ""]))
    with pytest.raises(claude_cli.ClaudeUnavailable):
        claude_cli.resolve()


def test_a_stand_in_receives_the_long_prompt_the_flags_and_the_document(monkeypatch, work):
    cli = _stand_in(os.path.join(work, "bin"), _ECHO)
    monkeypatch.setenv(claude_cli.ENV_VAR, cli)
    prompt = 'one\ntwo "three" %PATH% & four ^ | < > !\n' + "x" * 40000
    r = claude_cli.run(prompt, "the document", timeout=60)
    assert r.returncode == 0, r.stderr
    flags = repr(["--strict-mcp-config", "--tools", ""])
    assert r.stdout.rstrip("\n") == flags + "|" + prompt + "|the document"


@pytest.mark.skipif(not _WINDOWS, reason="cmd.exe batch parsing exists only on Windows")
def test_a_bat_shim_is_handled_like_a_cmd_shim(monkeypatch, work):
    cmd = _stand_in(os.path.join(work, "bin"), _ECHO)
    bat = cmd[:-4] + ".bat"
    os.replace(cmd, bat)
    monkeypatch.setenv(claude_cli.ENV_VAR, bat)
    r = claude_cli.run("a\nb & c", "doc", timeout=60)
    assert r.stdout.rstrip("\n").endswith("|a\nb & c|doc")


def test_the_timeout_stops_the_whole_process_tree(monkeypatch, work):
    # A batch shim runs the CLI as a grandchild. Killing only the direct child
    # leaves the grandchild holding the pipes, and the call then waits for it.
    cli = _stand_in(os.path.join(work, "bin"), _SLEEP)
    monkeypatch.setenv(claude_cli.ENV_VAR, cli)
    start = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired) as info:
        claude_cli.run("p", "doc", timeout=1)
    assert time.monotonic() - start < 5
    assert work not in str(info.value), "the timeout message names the CLI path"


class _ShellCalls(ast.NodeVisitor):
    """Call sites that ask for a command shell."""
    SHELL_FUNCS = {"system", "popen", "startfile", "getoutput", "getstatusoutput",
                   "create_subprocess_shell"}

    def __init__(self):
        self.found = []

    def visit_Call(self, node):
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
        if name in self.SHELL_FUNCS or name.startswith(("spawn", "exec")) and name != "exec_module":
            self.found.append(f"{name}() at line {node.lineno}")
        for kw in node.keywords:
            if kw.arg == "shell" and not (isinstance(kw.value, ast.Constant) and kw.value.value is False):
                self.found.append(f"shell= at line {node.lineno}")
        self.generic_visit(node)


def test_no_source_call_asks_for_a_shell():
    # The batch path does run cmd.exe, because Windows starts every .cmd file
    # that way. That path is guarded by the fixed argv above. This test checks
    # that no call asks for a shell on its own.
    for path in sorted(_SRC.rglob("*.py")):
        visitor = _ShellCalls()
        visitor.visit(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
        assert visitor.found == [], f"{path.name}: {visitor.found}"


def test_the_shell_check_catches_what_it_claims():
    samples = ["os.system('x')", "os.popen('x')", "subprocess.run(a, shell=True)",
               "subprocess.run(a, shell=flag)", "os.spawnl(0, 'x')", "os.execv('x', [])"]
    for sample in samples:
        visitor = _ShellCalls()
        visitor.visit(ast.parse(sample))
        assert visitor.found, sample
    visitor = _ShellCalls()
    visitor.visit(ast.parse("subprocess.run(a, shell=False)"))
    assert visitor.found == []
