#!/usr/bin/env python
"""Build the Articulate Writing plugin for Claude from this repository.

    python scripts/build_claude_plugin.py OUT_DIR [--replace]

The plugin carries the articulate package source unchanged, so the MCP server it
runs is the package's own code, started from the plugin folder with no install
step. OUT_DIR is meant to be the root of its own repository: Claude's directory
holds a Python server in a subfolder plugin for review, and a plugin at the root
of its repository avoids that hold.

What lands in OUT_DIR:

    claude-plugin/*            manifest, server launcher, skill and documents
    src/articulate/            every package file except caches and bytecode
    LICENSE

OUT_DIR must be absent or empty, or hold only a .git entry. With --replace, the
entries this script writes are removed first and .git is kept; any other entry
stops the build, so nothing stale ships. The result is then checked against
scripts/claude_plugin_rules.py, and the build exits 1 when a check fails.
"""
import argparse
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

import claude_plugin_rules as rules  # noqa: E402  (the path is set just above)

TEMPLATE = REPO / "claude-plugin"
PACKAGE = REPO / "src" / "articulate"
SKIP_DIRS = {"__pycache__"}
SKIP_SUFFIXES = {".pyc", ".pyo", ".pyd"}
SKIP_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}


def _files(base):
    """Every file under base that ships, as paths relative to base."""
    for path in sorted(base.rglob("*")):
        rel = path.relative_to(base)
        if (path.is_file() and not SKIP_DIRS & set(rel.parts)
                and path.suffix not in SKIP_SUFFIXES and path.name not in SKIP_NAMES):
            yield rel


def managed_entries():
    """The top-level names this script writes into OUT_DIR."""
    return sorted({p.name for p in TEMPLATE.iterdir()} | {"src", "LICENSE"})


def _prepare(out, replace):
    out.mkdir(parents=True, exist_ok=True)
    managed = set(managed_entries())
    present = {p.name for p in out.iterdir()} - {".git"}
    unknown = present - managed
    if unknown:
        raise SystemExit(f"{out} holds entries this build does not write: "
                         f"{sorted(unknown)}; remove them or pick another folder")
    if present and not replace:
        raise SystemExit(f"{out} is not empty; pass --replace to rebuild it in place")
    for name in present:
        target = out / name
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        else:
            target.unlink()


def build(out, replace=False):
    """Write the plugin into out and return the list of relative paths written."""
    out = Path(out)
    _prepare(out, replace)
    written = []
    for base, dest in ((TEMPLATE, out), (PACKAGE, out / "src" / "articulate")):
        for rel in _files(base):
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((base / rel).read_bytes())
            written.append(target.relative_to(out).as_posix())
    (out / "LICENSE").write_bytes((REPO / "LICENSE").read_bytes())
    written.append("LICENSE")
    return sorted(written)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out", help="the folder to write the plugin into")
    parser.add_argument("--replace", action="store_true",
                        help="rebuild a folder this script wrote before, keeping .git")
    args = parser.parse_args(argv)
    out = Path(args.out).resolve()
    if REPO == out or (REPO in out.parents
                       and "build" not in out.relative_to(REPO).parts):
        raise SystemExit("write the plugin outside this repository, or under build/")
    written = build(out, args.replace)
    problems = rules.check_bundle(out)
    size = sum((out / rel).stat().st_size for rel in written)
    print(f"articulate-writing {rules.bundled_version(out)}: {len(written)} files, "
          f"{size} bytes in {out}")
    for problem in problems:
        print(f"  problem: {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
