"""C1: a map of local and hosted commands, a local-only switch and a send guard.

The checks run offline. `judge`, `fix`, `polish` and `review` (and the MCP
tools of the same names) send the full text to a hosted model through the
claude CLI. A writer under a brief that allows only local tools, or holding a
manuscript under review, sets ARTICULATE_LOCAL_ONLY=1 or passes --local-only,
and every hosted command then exits non-zero before any subprocess starts.

These tests check the refusal and the notice. They say nothing about what a
hosted model does with a text.
"""
import os
import pathlib
import subprocess

import pytest

from articulate import claude_cli, cli, editor, mcp_server
from articulate import local_only as lo

ROOT = pathlib.Path(__file__).resolve().parent.parent
HOSTED = ("--judge", "--fix", "--polish", "--review", "--advise")


@pytest.fixture()
def no_subprocess(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("a subprocess started under local-only")
    monkeypatch.setattr(subprocess, "Popen", boom)
    monkeypatch.setattr(subprocess, "run", boom)
    monkeypatch.setattr(claude_cli, "_bounded_run", boom)


@pytest.fixture()
def doc(tmp_path):
    p = tmp_path / "draft.md"
    p.write_text("The team met on Tuesday.\n", encoding="utf-8")
    return str(p)


def _main(monkeypatch, argv):
    monkeypatch.setattr("sys.argv", ["articulate.editor", *argv])
    return editor.main()


@pytest.mark.parametrize("flag", HOSTED)
def test_the_environment_switch_refuses_every_hosted_command(monkeypatch, capsys,
                                                             no_subprocess, doc, flag):
    monkeypatch.setenv(lo.LOCAL_ONLY_VAR, "1")
    assert _main(monkeypatch, [flag, doc]) == lo.LOCAL_ONLY_EXIT
    assert "local-only" in capsys.readouterr().err


@pytest.mark.parametrize("flag", HOSTED)
def test_the_flag_refuses_every_hosted_command(monkeypatch, capsys, no_subprocess, doc, flag):
    monkeypatch.delenv(lo.LOCAL_ONLY_VAR, raising=False)
    assert _main(monkeypatch, ["--local-only", flag, doc]) == lo.LOCAL_ONLY_EXIT


def test_the_guard_holds_below_the_command_line(monkeypatch, no_subprocess):
    # A caller that skips main still cannot send: the backend refuses first.
    monkeypatch.setenv(lo.LOCAL_ONLY_VAR, "1")
    with pytest.raises(claude_cli.LocalOnly):
        claude_cli.run("prompt", "text")


@pytest.mark.parametrize("call", [lambda: mcp_server.do_judge("A draft."),
                                  lambda: mcp_server.do_fix("A draft."),
                                  lambda: mcp_server.do_polish("A draft.", passes=1)])
def test_the_mcp_hosted_tools_refuse(monkeypatch, no_subprocess, call):
    monkeypatch.setenv(lo.LOCAL_ONLY_VAR, "1")
    out = call()
    assert out["ok"] is False and "local-only" in out["error"]


def test_a_hosted_call_names_the_backend_and_that_the_text_leaves(monkeypatch, capsys, doc):
    monkeypatch.delenv(lo.LOCAL_ONLY_VAR, raising=False)
    monkeypatch.setattr(editor, "judge", lambda *a, **k: None)
    assert _main(monkeypatch, ["--judge", doc]) == 0
    err = capsys.readouterr().err
    assert "claude CLI" in err and "full text" in err and "draft.md" in err


def test_the_local_checks_run_with_the_switch_set(monkeypatch, capsys, no_subprocess, doc):
    monkeypatch.setenv(lo.LOCAL_ONLY_VAR, "1")
    assert cli.main(["check", doc]) == 0


def test_the_command_map_is_in_the_help_and_the_readme(capsys):
    with pytest.raises(SystemExit):
        cli.main(["--help"])
    out = capsys.readouterr().out
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for text in (out, readme):
        assert "ARTICULATE_LOCAL_ONLY" in text
        for cmd in ("check", "score", "receipt", "verify", "audit", "process",
                    "disclose", "desk", "judge", "review", "fix", "polish"):
            assert f"`{cmd}`" in text or f" {cmd}" in text, cmd


def test_review_has_an_alias_that_cannot_be_read_as_peer_review(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["articulate.editor", "--help"])
    with pytest.raises(SystemExit):
        editor.main()
    assert "--advise" in capsys.readouterr().out


def test_the_env_value_must_be_set_to_refuse(monkeypatch):
    for value in ("", "0", "false", "no"):
        monkeypatch.setenv(lo.LOCAL_ONLY_VAR, value)
        assert not claude_cli.local_only()
    for value in ("1", "true", "yes", "on"):
        monkeypatch.setenv(lo.LOCAL_ONLY_VAR, value)
        assert claude_cli.local_only()
    assert os.environ.get(lo.LOCAL_ONLY_VAR) == "on"
