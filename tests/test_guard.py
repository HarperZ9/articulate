"""The rewrite guard: a rewrite that changes an invariant is refused and the
previous text kept, in the library, in polish and fix, on the CLI, and over MCP.

Every refusal test has a paired control where a faithful rewrite goes through
the same path and lands, so a pass cannot come from the path refusing everything.
No LLM runs: the rewrite and judge functions are injected or monkeypatched. Uses
a project-local temp dir (tmp_path symlinks are denied on the Windows host).
"""
import json
import os
import shutil

import pytest

from articulate import cli, editor, guard, local_mcp

_TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_tmp_guard")
ORIGINAL = "Clients must retry 3 times. The cache is not shared.\n"
FAITHFUL = "Clients must retry 3 times. Nobody else reads the cache.\n"
BROKEN = "Clients should retry 5 times. The cache is shared.\n"


@pytest.fixture()
def work():
    os.makedirs(_TMP, exist_ok=True)
    yield _TMP
    shutil.rmtree(_TMP, ignore_errors=True)


def _write(work, name, text):
    p = os.path.join(work, name)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)
    return p


def _read(p):
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def _scores(v):
    return {k: v for k in editor.QUALITIES}


def test_guard_refuses_and_names_the_invariants():
    g = guard.RewriteGuard()
    with pytest.raises(guard.RewriteRefused) as info:
        g.run(lambda t: BROKEN, ORIGINAL)
    kinds = {r["kind"] for r in info.value.blocking}
    assert {"modal", "number", "negation"} <= kinds
    assert "number" in str(info.value) and g.refusals()


def test_guard_accepts_a_faithful_rewrite():
    g = guard.RewriteGuard()
    assert g.run(lambda t: FAITHFUL, ORIGINAL) == FAITHFUL
    assert g.log[-1]["accepted"] is True


def test_allowed_kinds_let_a_change_through():
    g = guard.RewriteGuard(allow="number")
    assert g.run(lambda t: "Retry 5 times.", "Retry 3 times.") == "Retry 5 times."
    assert guard.RewriteGuard(allow="all").run(lambda t: BROKEN, ORIGINAL) == BROKEN


def test_unknown_allowed_kind_fails_loudly():
    with pytest.raises(ValueError):
        guard.parse_allow("numbers")


def test_polish_keeps_the_best_text_when_a_rewrite_is_refused(work):
    src = _write(work, "p.md", ORIGINAL)
    out = os.path.join(work, "p.polished.md")
    editor.polish(src, out, passes=2, bar=5, rewrite_fn=lambda t, m, w: BROKEN,
                  judge_fn=lambda t: _scores(2 if t == ORIGINAL else 5))
    assert _read(out) == ORIGINAL


def test_polish_control_faithful_rewrite_lands(work):
    src = _write(work, "q.md", ORIGINAL)
    out = os.path.join(work, "q.polished.md")
    editor.polish(src, out, passes=2, bar=5, rewrite_fn=lambda t, m, w: FAITHFUL,
                  judge_fn=lambda t: _scores(2 if t == ORIGINAL else 5))
    assert _read(out) == FAITHFUL


@pytest.mark.parametrize("allow,expected", [("", ORIGINAL), ("all", BROKEN)])
def test_fix_refuses_unless_allowed(work, monkeypatch, allow, expected):
    src = _write(work, "f.md", ORIGINAL)
    out = os.path.join(work, "f.fixed.md")
    monkeypatch.setattr(editor, "claude_call", lambda instr, text: BROKEN)
    editor.fix(src, out, passes=1, guard=guard.RewriteGuard(allow=allow))
    assert _read(out) == expected


def test_compare_cli_gate_and_json(work, capsys):
    a = _write(work, "a.md", ORIGINAL)
    b = _write(work, "b.md", BROKEN)
    same = _write(work, "c.md", FAITHFUL)
    assert cli.main(["compare", a, b]) == 0                # report only
    assert cli.main(["compare", a, b, "--gate"]) == 1      # a change fails the gate
    assert cli.main(["compare", a, same, "--gate"]) == 0   # control: faithful passes
    capsys.readouterr()
    assert cli.main(["compare", a, b, "--json", "--allow-change", "all", "--gate"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == "changed" and payload["blocking"] == 0
    assert cli.main(["compare", a, os.path.join(work, "missing.md")]) == 2


def test_compare_over_mcp_is_local():
    result = local_mcp.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                               "params": {"name": "compare", "arguments": {
                                   "original": ORIGINAL, "rewrite": BROKEN}}})["result"]
    payload = json.loads(result["content"][0]["text"])
    assert payload["verdict"] == "changed" and payload["blocking"] > 0
    assert "compare" in local_mcp.LOCAL_ONLY
