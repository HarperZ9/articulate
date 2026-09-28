#!/usr/bin/env python
"""Build the Articulate Writing plugin for Claude from this repository.

    python scripts/build_claude_plugin.py OUT_DIR [--replace] [--dev]

The plugin carries the articulate package source unchanged, so the MCP server it
runs is the package's own code, started from the plugin folder with no install
step. OUT_DIR is meant to be the root of its own repository: Claude's directory
holds a Python server in a subfolder plugin for review, and a plugin at the root
of its repository avoids that hold.

What lands in OUT_DIR, taken from the files git tracks:

    claude-plugin/*            manifest, server launcher, skill and documents
    src/articulate/            every tracked package file except caches and bytecode
    LICENSE

An untracked or git-ignored file in those folders, such as a .env, never ships.

A release build, the default, first checks the source: no untracked or changed
file in the folders it copies, and, when the tag v<version> exists, package code
equal to that release, since Claude Code keeps a user on a plugin until the
version string changes. It prints the source commit to name in the plugin
repository's commit message. --dev skips these checks for a local test build.

OUT_DIR must be absent or empty, or hold only a .git entry. With --replace, the
entries this script writes are removed first and .git is kept; any other entry
stops the build, so nothing stale ships. The result is then checked against
scripts/claude_plugin_rules.py, and the build exits 1 when a check fails.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

import claude_plugin_rules as rules  # noqa: E402  (the path is set just above)
from find_program import find_program  # noqa: E402

SOURCES = (("claude-plugin", ""), ("src/articulate", "src/articulate"))
SKIP_DIRS = {"__pycache__"}
SKIP_SUFFIXES = {".pyc", ".pyo", ".pyd"}
SKIP_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}


def _git(repo, *args):
    git = find_program("git", avoid=[repo, Path.cwd()])
    if git is None:
        raise SystemExit("git was not found on the PATH; the build reads the files git "
                         "tracks, so it needs git")
    return subprocess.run([git, *args], cwd=repo, capture_output=True, timeout=120)


def _tracked(repo, folder):
    """The files git tracks under folder that exist, as paths relative to folder."""
    run = _git(repo, "ls-files", "-z", "--", folder)
    if run.returncode != 0:
        raise SystemExit(f"build from a git checkout: git ls-files failed in {repo} "
                         f"({run.stderr.decode('utf-8', 'replace').strip()})")
    base = Path(repo) / folder
    for name in sorted(n.decode("utf-8") for n in run.stdout.split(b"\0") if n):
        rel = (Path(repo) / name).relative_to(base)
        if ((base / rel).is_file() and not SKIP_DIRS & set(rel.parts)
                and rel.suffix not in SKIP_SUFFIXES and rel.name not in SKIP_NAMES):
            yield rel


def managed_entries(repo=REPO):
    """The top-level names this script writes into OUT_DIR."""
    return sorted({rel.parts[0] for rel in _tracked(repo, "claude-plugin")}
                  | {"src", "LICENSE"})


def _prepare(out, replace, repo):
    out.mkdir(parents=True, exist_ok=True)
    managed = set(managed_entries(repo))
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


def build(out, replace=False, repo=REPO):
    """Write the plugin into out and return the list of relative paths written."""
    out, repo = Path(out), Path(repo)
    _prepare(out, replace, repo)
    written = []
    for folder, dest in SOURCES:
        for rel in _tracked(repo, folder):
            target = out / dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((repo / folder / rel).read_bytes())
            written.append(target.relative_to(out).as_posix())
    (out / "LICENSE").write_bytes((repo / "LICENSE").read_bytes())
    written.append("LICENSE")
    return sorted(written)


def release_problems(repo=REPO):
    """Why the source at repo must not ship as a plugin release; empty when it may."""
    repo = Path(repo)
    problems = []
    status = _git(repo, "status", "--porcelain", "--untracked-files=all", "--",
                  "claude-plugin", "src/articulate", "LICENSE")
    changed = [line[3:] for line in status.stdout.decode("utf-8").splitlines() if line]
    if status.returncode != 0 or changed:
        problems.append("commit or remove these before a release build: "
                        + (", ".join(changed[:10]) or "git status failed")
                        + (f" and {len(changed) - 10} more" if len(changed) > 10 else ""))
    tag = "v" + (rules.bundled_version(repo) or "")
    if _git(repo, "rev-parse", "-q", "--verify", f"refs/tags/{tag}").returncode == 0:
        if _git(repo, "diff", "--quiet", tag, "--", "src/articulate").returncode != 0:
            problems.append(f"src/articulate differs from the {tag} release, so a plugin "
                            f"built here must not ship as {tag[1:]}; release the next "
                            "package version first")
    return problems


def source_commit(repo=REPO):
    run = _git(Path(repo), "rev-parse", "HEAD")
    return run.stdout.decode("utf-8").strip() if run.returncode == 0 else "unknown"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out", help="the folder to write the plugin into")
    parser.add_argument("--replace", action="store_true",
                        help="rebuild a folder this script wrote before, keeping .git")
    parser.add_argument("--dev", action="store_true",
                        help="a local test build: skip the release checks")
    args = parser.parse_args(argv)
    out = Path(args.out).resolve()
    if REPO == out or (REPO in out.parents
                       and "build" not in out.relative_to(REPO).parts):
        raise SystemExit("write the plugin outside this repository, or under build/")
    if not args.dev:
        refused = release_problems(REPO)
        for problem in refused:
            print(f"  release check: {problem}")
        if refused:
            print("no plugin written; fix the source, or pass --dev for a test build")
            return 1
    written = build(out, args.replace)
    problems = rules.check_bundle(out)
    size = sum((out / rel).stat().st_size for rel in written)
    print(f"articulate-writing {rules.bundled_version(out)}: {len(written)} files, "
          f"{size} bytes in {out}")
    print(f"source commit {source_commit(REPO)}"
          + (" (dev build: release checks skipped)" if args.dev else ""))
    for problem in problems:
        print(f"  problem: {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
