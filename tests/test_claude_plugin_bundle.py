"""The Claude plugin build: what it writes, and the rules it is held to.

scripts/build_claude_plugin.py copies claude-plugin/, the package source and
LICENSE into a folder that becomes the root of the plugin's own repository.
These tests build it, check it against scripts/claude_plugin_rules.py, and
confirm the bundled source is the package byte for byte. Each rule has a planted
break below, so a clean build is a finding and not a rule that never fires.
The documents a plugin user reads are held to the house profile and the origin
wording rules that the rest of the docs follow.
"""
import json
import pathlib
import subprocess

import pytest

import articulate
from articulate import local_mcp, mcp_server, profiles
from claude_plugin_helpers import (PLUGIN_ENV, ROOT, SERVER, SKILL, TEMPLATE,
                                   callable_name, load)
from test_no_origin_claims import SURFACE_CLAIM

build = load("build_claude_plugin")
rules = load("claude_plugin_rules")
PKG = pathlib.Path(articulate.__file__).parent


@pytest.fixture(scope="module")
def plugin(tmp_path_factory):
    out = tmp_path_factory.mktemp("built") / "articulate-writing"
    build.build(out)
    return out


def test_the_build_passes_every_rule(plugin):
    assert rules.check_bundle(plugin) == []


def _shipping_package_files():
    """Package files git would commit (tracked plus new, minus ignored), or None."""
    try:
        run = subprocess.run(["git", "ls-files", "-z", "--cached", "--others",
                              "--exclude-standard", "src/articulate"],
                             cwd=ROOT, capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if run.returncode != 0:
        return None
    names = [n.decode("utf-8") for n in run.stdout.split(b"\0") if n]
    return sorted(n[len("src/articulate/"):] for n in names
                  if (ROOT / n).is_file())


def test_the_bundled_source_is_the_package_byte_for_byte(plugin):
    bundled = plugin / "src" / "articulate"
    shipped = sorted(p.relative_to(bundled).as_posix()
                     for p in bundled.rglob("*") if p.is_file())
    expected = _shipping_package_files()
    if expected is not None:
        assert shipped == expected
    assert "local_mcp.py" in shipped and "py.typed" in shipped
    for rel in shipped:
        assert (bundled / rel).read_bytes() == (PKG / rel).read_bytes(), rel


def test_every_template_file_lands_unchanged(plugin):
    for path in TEMPLATE.rglob("*"):
        if path.is_file():
            rel = path.relative_to(TEMPLATE)
            assert (plugin / rel).read_bytes() == path.read_bytes(), rel
    assert (plugin / "LICENSE").read_bytes() == (ROOT / "LICENSE").read_bytes()


def test_the_build_refuses_a_folder_holding_other_files(tmp_path):
    (tmp_path / "notes.txt").write_text("keep me\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        build.build(tmp_path, replace=True)
    assert (tmp_path / "notes.txt").is_file()


def test_the_build_refuses_to_overwrite_without_replace(tmp_path):
    build.build(tmp_path / "out")
    with pytest.raises(SystemExit):
        build.build(tmp_path / "out")


def test_replace_rebuilds_in_place_and_keeps_git(tmp_path):
    out = tmp_path / "out"
    build.build(out)
    (out / ".git").mkdir()
    (out / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (out / "server" / "stale.py").write_text("x = 1\n", encoding="utf-8")
    build.build(out, replace=True)
    assert (out / ".git" / "HEAD").is_file()
    assert not (out / "server" / "stale.py").exists()
    assert rules.check_bundle(out) == []


def _edit(path, old, new):
    text = path.read_text(encoding="utf-8")
    assert old in text, old
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _edit_json(path, change):
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(json.dumps(data), encoding="utf-8")


def _server(data):
    return data["mcpServers"]["articulate"]


BREAKS = {
    "large-file": (lambda p: (p / "server" / "big.txt").write_text("x" * 262144),
                   "256 KiB"),
    "binary-file": (lambda p: (p / "server" / "blob.txt").write_bytes(b"\x00\xff"),
                    "not a text file"),
    "bin-folder": (lambda p: (p / "bin").mkdir(), "bin must not"),
    "claude-md": (lambda p: (p / "CLAUDE.md").write_text("x\n"), "CLAUDE.md must not"),
    "gitattributes": (lambda p: (p / ".gitattributes").write_text("* text=auto\n"),
                      ".gitattributes must not"),
    "bytecode": (lambda p: ((p / "src" / "articulate" / "__pycache__").mkdir(),
                            (p / "src" / "articulate" / "__pycache__" / "x.txt")
                            .write_text("x")), "cache file"),
    "em-dash": (lambda p: _edit(p / "README.md", "before you ship it.",
                                "before you ship it \u2014 fast."), "em dash"),
    "open-source": (lambda p: _edit(p / "SECURITY.md", "# Security",
                                    "# Security\n\nAn open-source plugin."), "open source"),
    "local-path": (lambda p: _edit(p / "README.md", "## Limits",
                                   "Saved in C:\\Users\\me\\notes.\n\n## Limits"),
                   "local file path"),
    "policy-topic": (lambda p: _edit(p / "README.md", "**Retention.**", "**Keeping.**"),
                     "does not cover Retention"),
    "policy-drift": (lambda p: _edit(p / "PRIVACY.md", "Last updated", "Updated"),
                     "PRIVACY.md differs"),
    "version": (lambda p: _edit_json(p / ".claude-plugin" / "plugin.json",
                                     lambda d: d.update(version="9.9.9")),
                "version differs"),
    "marketplace-version": (lambda p: _edit_json(
        p / ".claude-plugin" / "marketplace.json",
        lambda d: d["plugins"][0].update(version="0.5.0")), "plugin.json only"),
    "interpreter": (lambda p: _edit_json(p / ".mcp.json",
                                         lambda d: _server(d).update(command="python")),
                    "command must be python3"),
    "second-variable": (lambda p: _edit_json(p / ".mcp.json", lambda d: _server(d)[
        "args"].append("${CLAUDE_PLUGIN_DATA}/log")), "the only variable"),
    "skill-name": (lambda p: _edit(p / "skills" / "prose-review" / "SKILL.md",
                                   "name: prose-review", "name: review-prose"),
                   "equal the folder"),
    "skill-tool": (lambda p: _edit(p / "skills" / "prose-review" / "SKILL.md",
                                   "allowed-tools: ", "allowed-tools: Bash, "),
                   "allowed tool Bash"),
    "short-readme": (lambda p: (p / "README.md").write_text(
        "# Articulate\n\n## Privacy Policy\n\nNone.\n", encoding="utf-8"),
        "fewer than 40 words"),
}


@pytest.mark.parametrize("name", sorted(BREAKS))
def test_each_rule_catches_its_planted_break(tmp_path, name):
    out = tmp_path / "out"
    build.build(out)
    mutate, expected = BREAKS[name]
    mutate(out)
    problems = rules.check_bundle(out)
    assert any(expected in p for p in problems), problems


PLUGIN_DOCS = sorted(TEMPLATE.rglob("*.md")) + [ROOT / "docs" / "claude-plugin.md"]


@pytest.mark.parametrize("path", PLUGIN_DOCS, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_plugin_docs_pass_the_house_profile(path):
    result = articulate.check_text(path.read_text(encoding="utf-8"),
                                   profile=profiles.load("house"))
    hits = [f"L{f['line']} {f['match']!r}" for f in result["high"] + result["medium"]]
    assert result["gate"] == "ok", hits


@pytest.mark.parametrize("path", PLUGIN_DOCS, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_plugin_docs_name_no_origin(path):
    text = path.read_text(encoding="utf-8")
    assert not SURFACE_CLAIM.search(text), SURFACE_CLAIM.search(text).group(0)


def test_the_skill_allows_only_local_tools_the_plugin_lists():
    allowed = {t.strip() for t in rules.skill_front_matter(
        SKILL.read_text(encoding="utf-8"))["allowed-tools"].split(",")}
    listed = {callable_name(t["name"]): t for t in local_mcp.listed_tools(PLUGIN_ENV)}
    assert allowed <= set(listed), allowed - set(listed)
    assert all(listed[a]["annotations"]["readOnlyHint"] for a in allowed)
    assert {"check", "score"} <= {listed[a]["name"] for a in allowed}


def test_every_callable_tool_name_fits_in_64_characters():
    for tool in local_mcp.listed_tools(PLUGIN_ENV):
        assert len(callable_name(tool["name"])) <= 64, callable_name(tool["name"])


def test_the_result_fields_the_skill_names_exist():
    text = SKILL.read_text(encoding="utf-8")
    long = "By leveraging cutting-edge technology, teams move faster.\n\n" * 80
    result = mcp_server.do_check(long, 50)
    for field in ("gate", "rule_counts", "hits_omitted", "does_not_prove"):
        assert f"`{field}`" in text and field in result, field
    assert "`reason`" in text and "reason" in result["hits"][0]
    check = next(t for t in local_mcp.TOOLS if t["name"] == "check")
    assert "`max_hits`" in text and "max_hits" in check["inputSchema"]["properties"]


def _section(text, heading):
    return text.split(f"\n## {heading}\n", 1)[1].split("\n## ", 1)[0]


def test_the_readme_describes_the_launch_the_plugin_declares():
    readme = (TEMPLATE / "README.md").read_text(encoding="utf-8")
    runs = _section(readme, "What it runs")
    assert " ".join([SERVER["command"]] + SERVER["args"][:-1]) in runs
    for name, value in PLUGIN_ENV.items():
        assert f"{name}={value}" in runs


def test_the_readme_offers_at_least_three_example_prompts():
    readme = (TEMPLATE / "README.md").read_text(encoding="utf-8")
    prompts = [ln for ln in _section(readme, "Try it").splitlines() if ln.startswith("- \"")]
    assert len(prompts) >= 3, prompts
