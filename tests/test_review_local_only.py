"""Correctness review of the local-only switch and the editor command line (C1, C7a).

C1 says a writer who sets ARTICULATE_LOCAL_ONLY keeps every text on the
machine. A switch that guards private text should fail closed: a value the
writer meant as "on" must never send the text. C7a moved the editor command
line to editor_cli; the old command answered an empty file argument with
"no such file" and exit 2.

These tests need no ruleset change. They say nothing about what a hosted model
does with a text.
"""
import subprocess

import pytest

from articulate import claude_cli, editor_cli
from articulate import local_only as lo


@pytest.fixture()
def no_subprocess(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("a subprocess started under local-only")
    monkeypatch.setattr(subprocess, "Popen", boom)
    monkeypatch.setattr(subprocess, "run", boom)
    monkeypatch.setattr(claude_cli, "_bounded_run", boom)


# --- C-7: the switch fails open on a value it does not list ----------------- #

@pytest.mark.parametrize("value", ["y", "Y", "2", "enabled", "local"])
def test_an_unlisted_value_refuses_rather_than_sends(monkeypatch, no_subprocess, value):
    monkeypatch.setenv(lo.LOCAL_ONLY_VAR, value)
    with pytest.raises(claude_cli.LocalOnly):
        claude_cli.run("prompt", "text")


@pytest.mark.parametrize("value", ["", "0", "false", "no", "off"])
def test_control_the_explicit_off_values_still_allow_a_hosted_call(monkeypatch, value):
    monkeypatch.setenv(lo.LOCAL_ONLY_VAR, value)
    assert not lo.local_only()


# --- C-12: an empty file argument raises StopIteration ---------------------- #

def test_an_empty_file_argument_exits_with_no_such_file(monkeypatch, capsys):
    monkeypatch.delenv(lo.LOCAL_ONLY_VAR, raising=False)
    assert editor_cli.main(["--judge", ""]) == 2


def test_an_empty_file_argument_is_refused_under_local_only(monkeypatch, no_subprocess):
    monkeypatch.setenv(lo.LOCAL_ONLY_VAR, "1")
    assert editor_cli.main(["--judge", ""]) == lo.LOCAL_ONLY_EXIT
