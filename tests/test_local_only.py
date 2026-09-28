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

from articulate import backends, claude_cli, cli, editor, mcp_server
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
    monkeypatch.setattr(backends, "_ollama", lambda *a, **k: (_ for _ in ()).throw(
        backends.BackendUnavailable("no local model")))
    for name in ("_anthropic", "_openai", "_claude"):
        monkeypatch.setattr(backends, name, boom)


@pytest.fixture()
def doc(tmp_path):
    p = tmp_path / "draft.md"
    p.write_text("The team met on Tuesday.\n", encoding="utf-8")
    return str(p)


def _main(monkeypatch, argv):
    monkeypatch.setattr("sys.argv", ["articulate.editor", *argv])
    return editor.main()


@pytest.mark.parametrize("flag", HOSTED)
def test_the_environment_switch_keeps_editor_commands_local(monkeypatch, capsys,
                                                             no_subprocess, doc, flag):
    monkeypatch.setenv(lo.LOCAL_ONLY_VAR, "1")
    assert _main(monkeypatch, [flag, doc, "--backend", "claude-cli"]) == 0
    assert "ARTICULATE_LOCAL_ONLY" in capsys.readouterr().out


@pytest.mark.parametrize("flag", HOSTED)
def test_the_flag_keeps_editor_commands_local(monkeypatch, capsys, no_subprocess, doc, flag):
    monkeypatch.delenv(lo.LOCAL_ONLY_VAR, raising=False)
    assert _main(monkeypatch, ["--local-only", flag, doc, "--backend", "claude-cli"]) == 0


def test_the_guard_holds_below_the_command_line(monkeypatch, no_subprocess):
    # A caller that skips main still cannot send: the backend refuses first.
    monkeypatch.setenv(lo.LOCAL_ONLY_VAR, "1")
    with pytest.raises(claude_cli.LocalOnly):
        claude_cli.run("prompt", "text")


@pytest.mark.parametrize("call", [lambda: mcp_server.do_judge("A draft.", backend="claude-cli"),
                                  lambda: mcp_server.do_fix("A draft.", backend="claude-cli"),
                                  lambda: mcp_server.do_polish("A draft.", passes=1, backend="claude-cli")])
def test_the_mcp_hosted_tools_refuse(monkeypatch, no_subprocess, call):
    monkeypatch.setenv(lo.LOCAL_ONLY_VAR, "1")
    out = call()
    assert out["ok"] is True and out["backend"] == "none"
    assert out["attempts"][0] == {"backend": "claude-cli", "reason": "refused by ARTICULATE_LOCAL_ONLY"}


def test_cli_passes_the_explicit_backend(monkeypatch, capsys, doc):
    monkeypatch.delenv(lo.LOCAL_ONLY_VAR, raising=False)
    seen = []
    monkeypatch.setattr(editor, "judge", lambda *a, **k: seen.append(k))
    assert _main(monkeypatch, ["--judge", doc, "--backend", "anthropic"]) == 0
    assert seen == [{"backend": "anthropic"}]


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
