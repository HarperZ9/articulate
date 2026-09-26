"""The console output shown in the docs is the output the commands print.

Each case reruns a documented command on the shipped example file and compares
its output with the block the page shows after that command. A hand-edited
example that drifts from the real output fails here.
"""
import pathlib
import shutil

import pytest

from articulate.cli import main

ROOT = pathlib.Path(__file__).resolve().parent.parent
CASES = [
    ("getting-started.md", "notes.md", ["check", "notes.md"]),
    ("walkthrough.md", "post.md", ["check", "post.md", "--verbose"]),
    ("walkthrough.md", "post.md", ["check", "post.md", "--profile", "house"]),
    ("walkthrough.md", "post.md", ["check", "post.md", "--spans"]),
    ("walkthrough.md", "post.md", ["desk", "post.md", "--venue", "paper"]),
]


def _shown(page, command):
    text = (ROOT / "docs" / page).read_text(encoding="utf-8")
    i = text.index("articulate " + command + "\n")
    i = text.index("\n```\n", i) + 5
    j = text.index("\n```\n", i) + 5
    return text[j:text.index("\n```", j)]


@pytest.mark.parametrize("page,example,args", CASES)
def test_documented_output_matches_the_command(page, example, args, tmp_path, monkeypatch,
                                               capsys):
    shutil.copy(ROOT / "examples" / example, tmp_path / example)
    monkeypatch.chdir(tmp_path)
    capsys.readouterr()
    main(args)
    out = capsys.readouterr().out.rstrip("\n")
    assert out == _shown(page, " ".join(args))


def test_the_receipt_example_replays(tmp_path, monkeypatch, capsys):
    shutil.copy(ROOT / "examples" / "post.md", tmp_path / "post.md")
    monkeypatch.chdir(tmp_path)
    main(["receipt", "post.md"])
    (tmp_path / "post.receipt.json").write_text(capsys.readouterr().out, encoding="utf-8")
    main(["verify", "post.receipt.json", "post.md"])
    out = capsys.readouterr().out.rstrip("\n")
    assert out == _shown("walkthrough.md", "verify post.receipt.json post.md")
