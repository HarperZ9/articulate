"""We eat our own dog food: our shipped prose must pass our own checker under
the house profile.

detector.py is deliberately excluded. It is the device catalog: it names every
device it detects ("not X but Y", "instead", em-dash) in its own comments, so it
flags itself by design. Every other module's docstrings and comments, and every
shipped doc, must be clean under our own standard.
"""
import pathlib

import articulate
from articulate import profiles, pysource

ROOT = pathlib.Path(__file__).resolve().parent.parent

DOCS = ["README.md", "editors/vscode/README.md",
        "docs/README.md", "docs/getting-started.md", "docs/walkthrough.md",
        "docs/features.md", "docs/cli.md", "docs/boundaries.md"]
MODULES = ["cli.py", "editor.py", "bench.py", "mcp_server.py", "profiles.py",
           "receipt.py", "lsp_server.py", "pysource.py", "modes.py",
           "genres.py", "masking.py", "claude_cli.py", "__init__.py",
           "fairness.py", "fairness_gates.py", "fairness_stats.py",
           "fairness_corpora.py", "density.py", "logical.py", "rule_reasons.py",
           "cadence.py", "gate.py", "scan.py", "fingerprint.py", "binary.py",
           "prompts.py", "polish.py", "fix.py", "mathmask.py", "editor_metrics.py",
           "tool_text.py", "cli_output.py", "cli_receipts.py", "aliases.py"]


def _gate(path, text):
    # The project holds its own prose to its house style, which a writer who
    # never chose it is not held to.
    prof = profiles.load("house")
    r = articulate.check_text(text, profile=prof)
    return r["gate"], [f"L{f['line']} {f['match']!r}" for f in r["high"] + r["medium"]]


def test_shipped_docs_are_clean():
    for doc in DOCS:
        p = ROOT / doc
        gate, hits = _gate(p, p.read_text(encoding="utf-8"))
        assert gate == "ok", f"{doc} fails our own standard: {hits}"


def test_module_prose_is_clean():
    for mod in MODULES:
        p = ROOT / "src" / "articulate" / mod
        prose = pysource.prose_of(p.read_text(encoding="utf-8"))
        gate, hits = _gate(p, prose)
        assert gate == "ok", f"{mod} docstrings/comments fail our own standard: {hits}"
