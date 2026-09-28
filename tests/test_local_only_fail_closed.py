"""The local-only switch fails closed, and the editor command line reports a bad
file argument instead of crashing.

A writer who sets ARTICULATE_LOCAL_ONLY to keep a manuscript on the machine must
not send it because the value was spelled differently: any value other than an
explicit off value counts as on. An MCP caller refused under the switch is told
so, not told that the backend is missing. The editor command line answers an
empty file argument as it answers a missing file: "no such file", exit 2, or
exit 3 under the switch.

These tests need no ruleset change and say nothing about what a hosted model
does with a text.
"""
import subprocess

import pytest

from articulate import backends, claude_cli, editor_cli, mcp_server
from articulate import local_only as lo


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


@pytest.mark.parametrize("value", ["y", "Y", "2", "enabled", "local", " TRUE "])
def test_an_unlisted_value_refuses_rather_than_sends(monkeypatch, no_subprocess, value):
    monkeypatch.setenv(lo.LOCAL_ONLY_VAR, value)
    with pytest.raises(claude_cli.LocalOnly) as err:
        claude_cli.run("prompt", "text")
    assert repr(value) in str(err.value)


@pytest.mark.parametrize("value", ["", "0", "false", "no", "off", " Off "])
def test_control_the_explicit_off_values_still_allow_a_hosted_call(monkeypatch, value):
    monkeypatch.setenv(lo.LOCAL_ONLY_VAR, value)
    assert not lo.local_only()


def test_control_an_unset_switch_allows_a_hosted_call(monkeypatch):
    monkeypatch.delenv(lo.LOCAL_ONLY_VAR, raising=False)
    assert not lo.local_only()


def test_an_empty_file_argument_exits_with_no_such_file(monkeypatch, capsys):
    monkeypatch.delenv(lo.LOCAL_ONLY_VAR, raising=False)
    assert editor_cli.main(["--judge", ""]) == 2
    assert "no such file" in capsys.readouterr().out


def test_an_empty_file_argument_is_refused_under_local_only(monkeypatch, no_subprocess):
    monkeypatch.setenv(lo.LOCAL_ONLY_VAR, "1")
    assert editor_cli.main(["--judge", ""]) == 2


@pytest.mark.parametrize("call", [lambda: mcp_server.do_judge("A draft.", backend="claude-cli"),
                                  lambda: mcp_server.do_fix("A draft.", backend="claude-cli"),
                                  lambda: mcp_server.do_polish("A draft.", passes=1, backend="claude-cli")])
def test_an_mcp_refusal_names_the_switch_not_the_backend(monkeypatch, no_subprocess, call):
    monkeypatch.setenv(lo.LOCAL_ONLY_VAR, "1")
    out = call()
    assert out["ok"] is True and out["backend"] == "none"
    assert out["attempts"][0] == {"backend": "claude-cli", "reason": "refused by ARTICULATE_LOCAL_ONLY"}
