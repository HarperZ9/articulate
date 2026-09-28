"""The stdio server behavior the Claude plugin relies on.

The plugin starts the server with ARTICULATE_MCP_TOOLS=local and
ARTICULATE_LOCAL_ONLY=1. The first lists only the tools that read the text and
nothing else; the second makes a hosted tool refuse before any network call even
if the listing were wrong. These tests pin both, and the protocol details a host
depends on: ping, a failed call marked as an error, a check result that stays
inside a host's output cap, and a doctor report a user can paste into an issue.
"""
import io
import json
import re
import subprocess

import pytest

from articulate import local_mcp, mcp_server, tool_meta

HOSTED = set(local_mcp.NEEDS_BACKEND)
# Enough repeated findings to pass the default cap of 50 span records.
LONG = "By leveraging cutting-edge technology, teams move faster.\n\n" * 300


def _request(method, params=None):
    req = {"jsonrpc": "2.0", "id": 7, "method": method}
    if params is not None:
        req["params"] = params
    return local_mcp.handle(req)


def _call(name, arguments=None):
    return _request("tools/call", {"name": name, "arguments": arguments or {}})["result"]


def _payload(result):
    return json.loads(result["content"][0]["text"])


@pytest.fixture
def no_process(monkeypatch):
    """Any attempt to start the claude CLI fails the test."""
    def refuse(*args, **kwargs):
        raise AssertionError("a refused hosted call started a process")
    monkeypatch.setattr(subprocess, "Popen", refuse)
    monkeypatch.setattr(subprocess, "run", refuse)


def test_the_hosted_set_is_written_down_once():
    assert tool_meta.HOSTED == HOSTED


@pytest.mark.parametrize("value,expected", [
    (None, "all"), ("", "all"), ("all", "all"), (" ALL ", "all"),
    ("local", "local"), ("lcoal", "local"), ("everything", "local"),
])
def test_the_tool_set_fails_toward_fewer_tools(value, expected):
    environ = {} if value is None else {local_mcp.TOOLS_VAR: value}
    assert local_mcp.tool_set(environ) == expected


def test_every_tool_is_listed_by_default(monkeypatch):
    monkeypatch.delenv(local_mcp.TOOLS_VAR, raising=False)
    names = [t["name"] for t in _request("tools/list")["result"]["tools"]]
    assert names == [t["name"] for t in local_mcp.TOOLS]


def test_the_local_set_lists_no_tool_that_sends_the_text(monkeypatch):
    monkeypatch.setenv(local_mcp.TOOLS_VAR, "local")
    names = {t["name"] for t in _request("tools/list")["result"]["tools"]}
    assert names == {t["name"] for t in local_mcp.TOOLS} - HOSTED
    assert names, "the local set listed nothing"


@pytest.mark.parametrize("name", sorted(HOSTED))
def test_a_hidden_tool_refuses_by_name_and_starts_nothing(monkeypatch, no_process, name):
    monkeypatch.setenv(local_mcp.TOOLS_VAR, "local")
    # The listing alone must hold, without the local-only switch behind it.
    monkeypatch.delenv("ARTICULATE_LOCAL_ONLY", raising=False)
    result = _call(name, {"text": "A short passage."})
    assert result["isError"] is True
    message = result["content"][0]["text"]
    assert local_mcp.TOOLS_VAR + "=all" in message


@pytest.mark.parametrize("name", sorted(HOSTED))
def test_the_plugin_refusal_points_to_no_switch(monkeypatch, no_process, name):
    """Under the plugin's settings a hidden tool says only that this server runs
    the local checks. A how-to for listing the hosted tools would steer Claude
    toward editing the plugin's settings, which the plugin cannot honor."""
    monkeypatch.setenv(local_mcp.TOOLS_VAR, "local")
    monkeypatch.setenv("ARTICULATE_LOCAL_ONLY", "1")
    result = _call(name, {"text": "A short passage."})
    assert result["isError"] is True
    message = result["content"][0]["text"]
    assert "local checks only" in message, message
    assert "=all" not in message and local_mcp.TOOLS_VAR not in message, message


def test_a_failed_hosted_call_is_marked_as_an_error(monkeypatch, no_process):
    monkeypatch.delenv(local_mcp.TOOLS_VAR, raising=False)
    monkeypatch.setenv("ARTICULATE_LOCAL_ONLY", "1")
    result = _call("judge", {"text": "A short passage."})
    assert result["isError"] is True
    payload = _payload(result)
    assert payload["ok"] is False
    assert "local-only" in payload["note"]


def test_a_successful_call_is_not_marked_as_an_error():
    assert "isError" not in _call("check", {"text": "The cat sat on the mat."})


def test_ping_gets_an_empty_result():
    assert _request("ping") == {"jsonrpc": "2.0", "id": 7, "result": {}}


def test_a_long_check_fits_inside_the_host_output_cap():
    result = _call("check", {"text": LONG})
    text = result["content"][0]["text"]
    payload = json.loads(text)
    full = mcp_server.do_check(LONG)
    assert len(full["hits"]) > 50, "the case no longer reaches the cap"
    assert len(payload["hits"]) == 50
    assert payload["hits"] == full["hits"][:50]
    assert payload["hits_omitted"] == len(full["hits"]) - 50
    assert payload["rule_counts"] == full["rule_counts"]
    assert payload["gate"] == full["gate"]
    # Claude Code warns above 10,000 tokens in one tool result. At roughly four
    # characters a token, 40,000 characters stays under that line.
    assert len(text) < 40_000, len(text)


@pytest.mark.parametrize("max_hits", [100, 1000])
def test_a_check_at_any_allowed_max_hits_fits_inside_the_host_output_cap(max_hits):
    text = _call("check", {"text": LONG, "max_hits": max_hits})["content"][0]["text"]
    payload = json.loads(text)
    full = mcp_server.do_check(LONG)
    assert len(text) < 40_000, len(text)
    shown = len(payload["hits"])
    assert shown >= 50, "the budget cut below the default"
    assert payload["hits"] == full["hits"][:shown]
    assert payload["hits_omitted"] == len(full["hits"]) - shown
    assert payload["rule_counts"] == full["rule_counts"]


def test_max_hits_zero_returns_the_counts_only():
    payload = _payload(_call("check", {"text": LONG, "max_hits": 0}))
    assert payload["hits"] == []
    assert payload["hits_omitted"] == len(mcp_server.do_check(LONG)["hits"])
    assert payload["rule_counts"]


def test_a_short_check_has_no_omitted_count():
    assert "hits_omitted" not in _payload(_call("check", {"text": "The cat sat."}))


@pytest.mark.parametrize("value", [-1, 1001, "5", 2.5, True])
def test_an_out_of_range_max_hits_is_a_tool_error(value):
    result = _call("check", {"text": "The cat sat.", "max_hits": value})
    assert result["isError"] is True
    assert "max_hits" in result["content"][0]["text"]


def test_a_null_max_hits_means_the_default():
    # Some clients send null for an optional argument they leave unset.
    payload = _payload(_call("check", {"text": LONG, "max_hits": None}))
    assert len(payload["hits"]) == 50


def test_non_ascii_text_stays_readable_in_the_result():
    result = _call("check", {"text": "Our résumé service is cutting-edge."})
    text = result["content"][0]["text"]
    assert "résumé" in text, "the snippet was escaped or lost"
    assert "\\u00e9" not in text


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def test_doctor_reports_the_plugin_setup_without_a_path(monkeypatch):
    monkeypatch.setenv(local_mcp.TOOLS_VAR, "local")
    monkeypatch.setenv("ARTICULATE_LOCAL_ONLY", "1")
    doctor = _payload(_call("articulate.doctor"))
    assert doctor["tool_set"] == "local"
    assert set(doctor["hidden"]) == HOSTED
    assert not set(doctor["tools"]) & HOSTED
    assert doctor["local_only_switch"] is True
    assert re.fullmatch(r"\d+\.\d+\.\d+", doctor["python"])
    # The local set never looks the claude CLI up on the PATH.
    assert "backend_cli_found" not in doctor
    for value in _strings(doctor):
        assert "/" not in value and "\\" not in value, value


def test_doctor_says_whether_the_backend_cli_is_found_when_hosted_tools_list(monkeypatch):
    monkeypatch.delenv(local_mcp.TOOLS_VAR, raising=False)
    monkeypatch.delenv("ARTICULATE_LOCAL_ONLY", raising=False)
    doctor = _payload(_call("articulate.doctor"))
    assert doctor["tool_set"] == "all"
    assert doctor["hidden"] == []
    assert type(doctor["backend_cli_found"]) is bool


def test_a_listed_hosted_tool_under_the_switch_never_reaches_its_body(monkeypatch):
    """With the local-only switch on, the stdio server refuses a hosted tool before
    its body runs, whatever the body does first."""
    monkeypatch.setenv(local_mcp.TOOLS_VAR, "all")
    monkeypatch.setenv("ARTICULATE_LOCAL_ONLY", "1")
    reached = []
    for name in sorted(HOSTED):
        monkeypatch.setattr(local_mcp, "do_" + name, lambda *a, **k: reached.append(a))
        result = _call(name, {"text": "A short passage."})
        assert result["isError"] is True and "local-only" in _payload(result)["note"]
    assert reached == []


def _serve(lines):
    out = io.StringIO()
    assert local_mcp.serve(io.StringIO("".join(line + "\n" for line in lines)), out) == 0
    return [json.loads(line) for line in out.getvalue().splitlines() if line.strip()]


PING = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "ping"})


def test_a_deeply_nested_request_is_a_parse_error_and_the_server_keeps_serving():
    deep = ('{"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": '
            '"check", "arguments": {"text": "x", "extra": ' + "[" * 10_000
            + "]" * 10_000 + "}}}")
    answers = _serve([deep, PING])
    assert answers[0]["error"]["code"] == -32700, answers[0]
    assert answers[-1] == {"jsonrpc": "2.0", "id": 2, "result": {}}


def test_an_unexpected_failure_is_an_internal_error_and_the_server_keeps_serving(
        monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("planted failure")
    monkeypatch.setattr(local_mcp, "listed_tools", boom)
    answers = _serve([json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}),
                      PING])
    assert answers[0]["id"] == 1 and answers[0]["error"]["code"] == -32603, answers[0]
    assert "planted failure" not in json.dumps(answers[0])
    assert answers[-1] == {"jsonrpc": "2.0", "id": 2, "result": {}}
