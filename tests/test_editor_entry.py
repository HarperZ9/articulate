"""C7a: the documented editor command runs.

`python -m articulate.editor` is the only documented entry to the editor
(README, docs/cli.md, docs/walkthrough.md). On this branch it failed with a
circular import between editor.py and polish.py, while v0.5.0 worked. This
smoke test runs the documented command the way a writer would.
"""
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _run(*args):
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    return subprocess.run([sys.executable, "-m", "articulate.editor", *args],
                          capture_output=True, text=True, env=env, cwd=str(ROOT),
                          timeout=60)


def test_the_documented_editor_command_prints_its_help():
    r = _run("--help")
    assert r.returncode == 0, r.stderr
    for flag in ("--judge", "--fix", "--polish", "--review", "--local-only"):
        assert flag in r.stdout, flag


def test_the_documented_editor_command_runs_without_a_model_under_local_only(tmp_path):
    p = tmp_path / "draft.md"
    p.write_text("The team met on Tuesday.\n", encoding="utf-8")
    r = _run("--local-only", "--backend", "none", "--judge", str(p))
    assert r.returncode == 0, (r.returncode, r.stdout, r.stderr)
    assert "backend: none" in r.stdout
    assert "Traceback" not in r.stderr
