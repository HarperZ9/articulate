"""The privacy claim, enforced: no module in the package imports a network
library, and only the editor starts a subprocess (the model backend CLI).

The README and Boundaries say the core makes no network call and has no
telemetry. This test reads every module's imports, so a change that adds a
network path fails here before the claim goes stale.
"""
import ast
import pathlib

import articulate

PKG = pathlib.Path(articulate.__file__).parent
NETWORK = {"socket", "ssl", "http", "urllib.request", "urllib.error", "requests",
           "httpx", "aiohttp", "ftplib", "smtplib", "poplib", "imaplib", "xmlrpc",
           "telnetlib", "asyncio", "websocket", "websockets"}
SUBPROCESS_ALLOWED = {"editor.py"}


def _imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            yield node.module


def _hits(names, banned):
    return sorted(n for n in names if any(n == b or n.startswith(b + ".") for b in banned))


def test_no_module_imports_a_network_library():
    found = {p.name: _hits(set(_imports(p)), NETWORK) for p in PKG.glob("*.py")}
    assert not {k: v for k, v in found.items() if v}


def test_only_the_editor_starts_a_subprocess():
    users = {p.name for p in PKG.glob("*.py") if _hits(set(_imports(p)), {"subprocess"})}
    assert users <= SUBPROCESS_ALLOWED, users - SUBPROCESS_ALLOWED


def test_the_scan_sees_real_imports():
    """Control: the import reader finds the stdlib imports that are there, so an
    empty result above is not a reader that finds nothing."""
    assert "subprocess" in set(_imports(PKG / "editor.py"))
    assert _hits({"urllib.parse", "urllib.request"}, NETWORK) == ["urllib.request"]
