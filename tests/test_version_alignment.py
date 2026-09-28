"""The declared version must agree everywhere it is written down.

articulate writes its version in three places: ``pyproject.toml`` for the built
distribution, ``articulate.__version__`` for anything that asks the running
package, and the README line that names the prepared or published release. The MCP
server reports the module value in its ``serverInfo``, so a client asking which
version it is talking to gets that one rather than the wheel's.

Nothing tied them together. A release could ship 0.4.0 while the module and
every MCP client reported 0.3.0, and the suite would stay green. The publish
workflow reads ``pyproject.toml`` and never the module, so it could not catch it
either.

The version is read with a regex rather than ``tomllib``. ``requires-python`` is
``>=3.9`` and ``tomllib`` arrived in 3.11, so importing it here would make this
guard the reason the 3.9 and 3.10 jobs fail.
"""
import pathlib
import re

import articulate
from articulate import local_mcp

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_PROJECT_VERSION = re.compile(
    r"^\[project\]$.*?^version\s*=\s*[\"']([^\"']+)[\"']",
    re.MULTILINE | re.DOTALL,
)


def _declared_version():
    text = (_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = _PROJECT_VERSION.search(text)
    assert match is not None, "pyproject.toml has no [project] version"
    return match.group(1)


def test_the_declared_version_is_readable():
    # Guards the guard. A regex that silently stopped matching would make every
    # assertion below vacuous rather than failing.
    assert re.fullmatch(r"\d+\.\d+\.\d+", _declared_version())


def test_module_version_matches_the_declared_distribution_version():
    assert articulate.__version__ == _declared_version()


def test_the_mcp_server_reports_the_declared_version():
    # The value a client actually receives, not just the constant behind it.
    response = local_mcp.handle(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert response["result"]["serverInfo"]["version"] == _declared_version()


def test_the_changelog_has_an_entry_for_the_declared_version():
    changelog = (_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    version = _declared_version()
    assert f"## {version}" in changelog, (
        f"CHANGELOG.md has no '## {version}' heading, so the release would ship "
        "without saying what changed")


def test_the_readme_names_the_release_version():
    readme = (_ROOT / "README.md").read_text(encoding="utf-8")
    version = _declared_version()
    stated = re.findall(
        r"Version (\d+\.\d+\.\d+) is (?:on PyPI|prepared for release)", readme)
    assert stated, "README no longer states the published or prepared version"
    assert set(stated) == {version}, (
        f"README names release {stated} while the package declares {version}")


def _triple(version):
    return tuple(int(x) for x in re.findall(r"\d+", version)[:3])


def test_the_published_ruleset_record_never_names_a_later_package():
    # fairness/published-ruleset.json names the last package that published.
    # A commit after each release updates it, so between releases it names the
    # declared version and during a release an earlier one. A record naming a
    # later package than the one declared was written ahead of a release, and
    # the release check would read it as vouching for rules it never published.
    import json
    record = json.loads((_ROOT / "fairness" / "published-ruleset.json").read_text(
        encoding="utf-8"))
    assert _triple(record["package_version"]) <= _triple(_declared_version())
