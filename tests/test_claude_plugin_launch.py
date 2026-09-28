"""The built plugin's server, started the way Claude Code starts it.

Each case builds the plugin, then runs scripts/smoke_claude_plugin.py against it
with this test run's Python in place of python3, so every Python in the CI
matrix starts the bundled server through the launcher and the exact arguments in
.mcp.json. Claude Code reads the server's stdin as UTF-8 bytes; the cases here
also force a legacy code page on stdin, which is how Windows reads it by
default, and put a decoy on PYTHONPATH that the launcher flags must keep out.
"""
import subprocess
import sys

import pytest

from claude_plugin_helpers import load

build = load("build_claude_plugin")
smoke = load("smoke_claude_plugin")

QUOTED = "a quoted line is not a finding (UTF-8 input)"
ACCENTED = "accented text round-trips"


@pytest.fixture(scope="module")
def plugin(tmp_path_factory):
    out = tmp_path_factory.mktemp("launch") / "articulate-writing"
    build.build(out)
    return out


def _failures(results):
    return [(check, detail) for check, passed, detail in results if not passed]


def test_the_declared_launch_passes_every_smoke_check(plugin):
    results, stderr = smoke.smoke(plugin, command=sys.executable)
    assert len(results) >= 10
    assert not _failures(results), (_failures(results), stderr)


def test_utf8_input_survives_a_legacy_code_page(plugin):
    """Without -I and -X utf8, PYTHONIOENCODING=cp1252 makes the child read stdin
    as cp1252 on every system. The server must switch it back to UTF-8 itself,
    which is what a pip install started by hand relies on."""
    results, stderr = smoke.smoke(plugin, command=sys.executable, drop=("-X", "-I"),
                                  extra_env={"PYTHONIOENCODING": "cp1252",
                                             "PYTHONUTF8": "0"})
    by_check = {check: (passed, detail) for check, passed, detail in results}
    assert by_check[QUOTED][0], (by_check[QUOTED], stderr)
    assert by_check[ACCENTED][0], (by_check[ACCENTED], stderr)


def test_the_code_page_case_does_misread_utf8_when_nothing_switches_it():
    """Control: the environment above does make a plain child misread UTF-8, so
    the passing case is the server's own switch at work. The closing quote's
    last byte has no cp1252 character, so a strict read may fail outright."""
    run = subprocess.run(
        [sys.executable, "-c", "import sys; sys.stdout.write(ascii(sys.stdin.readline()))"],
        input="“quoted”\n".encode("utf-8"), capture_output=True, timeout=60,
        env={**_base_env(), "PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"})
    crashed = run.returncode != 0 and b"UnicodeDecodeError" in run.stderr
    misread = run.returncode == 0 and "\\u201c" not in run.stdout.decode("ascii")
    assert crashed or misread, (run.returncode, run.stdout, run.stderr)


def _base_env():
    import os
    return {k: v for k, v in os.environ.items()
            if k not in ("PYTHONIOENCODING", "PYTHONUTF8", "PYTHONPATH")}


def _decoy(tmp_path):
    """A PYTHONPATH folder whose sitecustomize stops any Python that reads it."""
    decoy = tmp_path / "decoy"
    decoy.mkdir()
    (decoy / "sitecustomize.py").write_text(
        "import sys\nsys.stderr.write('DECOY LOADED\\n')\nsys.exit(7)\n", encoding="utf-8")
    return {"PYTHONPATH": str(decoy)}


def test_the_launch_flags_keep_other_python_code_out(plugin, tmp_path):
    results, stderr = smoke.smoke(plugin, command=sys.executable,
                                  extra_env=_decoy(tmp_path))
    assert not _failures(results), (_failures(results), stderr)
    assert "DECOY LOADED" not in stderr


def test_the_decoy_loads_when_the_isolation_flag_is_dropped(plugin, tmp_path):
    """Control: without -I the same decoy runs, so the case above tests -I."""
    results, stderr = smoke.smoke(plugin, command=sys.executable, drop=("-I",),
                                  extra_env=_decoy(tmp_path))
    assert "DECOY LOADED" in stderr
    assert _failures(results)


def _run_launcher(path, prelude=""):
    code = (prelude + "p = %r\nexec(compile(open(p).read(), p, 'exec'), "
            "{'__file__': p, '__name__': '__main__'})\n" % str(path))
    return subprocess.run([sys.executable, "-I", "-B", "-c", code], capture_output=True,
                          text=True, timeout=60, input="")


def test_the_launcher_names_the_python_it_needs(plugin):
    run = _run_launcher(plugin / "server" / "serve.py",
                        "import sys\nsys.version_info = (3, 8, 18, 'final', 0)\n")
    assert run.returncode == 1
    assert "needs Python 3.9 or later" in run.stderr and "Python 3.8" in run.stderr


def test_the_launcher_says_when_the_bundled_source_is_missing(plugin, tmp_path):
    lonely = tmp_path / "plugin" / "server"
    lonely.mkdir(parents=True)
    (lonely / "serve.py").write_bytes((plugin / "server" / "serve.py").read_bytes())
    run = _run_launcher(lonely / "serve.py")
    assert run.returncode == 1
    assert "bundled source is missing" in run.stderr
