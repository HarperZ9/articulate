"""articulate.code.testdiff -- did this change make the tests check less? (B2 + B4)

Compares each Python test file before and after a change, test by test. B2
findings: a check deleted or replaced by a weaker form, a tolerance widened, a
new skip or xfail, a broad `except` that swallows the act step, an expected
exception widened, a test deleted while its feature stays, a test renamed so it
no longer collects. B4 findings (see tautology.py) apply to every test the change
adds or edits; untouched tests are not re-reported.

A finding is "declared" instead of a plain finding when the change states its
reason: an entry in the caller's declared test changes, a comment on the changed
line or the line above it, or a skip conditioned on a platform or a missing
dependency. Comments can be written by whoever wrote the weakening, so a declared
finding is a reviewer prompt with a stated reason, not a clearance.

Report-only by design. Static: nothing is imported or run.
"""
from __future__ import annotations

import ast
import re
from collections import Counter
from dataclasses import dataclass

from .pytests import inventory
from .tautology import tautologies

_REASON = re.compile(
    r"platform|win32|windows|linux|darwin|macos|posix|os\.name|version_info|"
    r"python ?3|importorskip|find_spec|which\(|not installed|missing|unavailable|"
    r"requires?|optional|has_|_available|available|no module|import", re.I)


_MODULE_SKIP = re.compile(r"pytest\.(skip|xfail|importorskip)\(")


@dataclass
class Finding:
    check: str     # B2 or B4
    rule: str
    path: str
    test: str
    line: int
    detail: str
    tier: str = "finding"   # finding | declared


def is_test_path(path: str) -> bool:
    parts = path.replace("\\", "/").split("/")
    name = parts[-1]
    if not name.endswith(".py"):
        return False
    return (name.startswith("test_") or name.endswith("_test.py")
            or any(p in ("tests", "test", "testing") for p in parts[:-1]))


def _cumulative(facts, helpers) -> list:
    checks = list(facts.checks)
    for name in facts.helper_calls:
        checks += helpers.get(name, [])
    return [sum(1 for c in checks if c.strength >= s) for s in (1, 2, 3)]


def _file_texts(inv) -> Counter:
    out = Counter()
    for facts in inv.functions.values():
        out.update(c.text for c in facts.checks)
    return out


def _commented(source_lines, line) -> bool:
    for ln in (line, line - 1):
        if 1 <= ln <= len(source_lines) and "#" in source_lines[ln - 1]:
            comment = source_lines[ln - 1].split("#", 1)[1].strip()
            if len(comment.split()) >= 2:
                return True
    return False


def _compare_checks(name, t0, t1, inv0, inv1, path) -> list:
    out = []
    c0, c1 = _cumulative(t0, inv0.helpers), _cumulative(t1, inv1.helpers)
    removed = Counter(c.text for c in t0.checks) - Counter(c.text for c in t1.checks)
    file0, file1 = _file_texts(inv0), _file_texts(inv1)
    by_text = {c.text: c for c in t0.checks}
    for text, n in removed.items():
        if file1[text] >= file0[text]:       # moved to another test or helper
            strength = by_text[text].strength
            for i in range(3):
                if strength >= i + 1:
                    c1[i] += n
    line = t1.node.lineno
    if c1[0] < c0[0]:
        out.append(Finding("B2", "assertion-deleted", path, name, line,
                           f"checks {c0[0]} -> {c1[0]}"))
    elif c1[2] < c0[2] or c1[1] < c0[1]:
        out.append(Finding("B2", _weak_rule(t0, t1), path, name, line,
                           f"strong checks {c0[2]} -> {c1[2]}, narrowing {c0[1]} -> {c1[1]}"))
    else:
        out += _subject_downgrades(name, t0, t1, path)
    return out


def _weak_rule(t0, t1) -> str:
    raises0 = max((c.strength for c in t0.checks if c.kind == "raises"), default=0)
    raises1 = max((c.strength for c in t1.checks if c.kind == "raises"), default=0)
    if raises1 and raises1 < raises0:
        return "raises-widened"
    return "assertion-weakened"


def _subject_downgrades(name, t0, t1, path) -> list:
    """Same count, but a subject's check got weaker: `x == 1` became `x is not None`."""
    best0, best1 = {}, {}
    for facts, best in ((t0, best0), (t1, best1)):
        for c in facts.checks:
            if c.subject:
                best[c.subject] = max(best.get(c.subject, 0), c.strength)
    for subject, s0 in best0.items():
        s1 = best1.get(subject)
        if s1 is not None and s1 < s0:
            return [Finding("B2", "assertion-weakened", path, name, t1.node.lineno,
                            f"check on {subject[:60]} strength {s0} -> {s1}")]
    return []


def _markers(name, t0, t1, path, lines1) -> list:
    out = []
    old = Counter((m[0], m[3]) for m in t0.markers)
    for kind, line, conditional, text in t1.markers:
        if old[(kind, text)] > 0:
            old[(kind, text)] -= 1
            continue
        rule = "xfail-added" if "xfail" in kind.lower() or kind == "expectedFailure" \
            else "skip-added"
        reason = (conditional and _REASON.search(text)) or kind == "importorskip"
        tier = "declared" if reason or _commented(lines1, line) else "finding"
        out.append(Finding("B2", rule, path, name, line, text[:120], tier))
    return out


def _tolerances(name, t0, t1, path, lines1) -> list:
    out = []
    old = {}
    for func, kw, value, _ in t0.tolerances:
        old.setdefault((func, kw), []).append(value)
    seen = Counter()
    for func, kw, value, line in t1.tolerances:
        key = (func, kw)
        values = old.get(key, [])
        index = seen[key]
        seen[key] += 1
        if index >= len(values):
            continue
        before = values[index]
        widened = value < before if kw == "places" else value > before
        if widened:
            tier = "declared" if _commented(lines1, line) else "finding"
            out.append(Finding("B2", "tolerance-widened", path, name, line,
                               f"{func} {kw} {before:g} -> {value:g}", tier))
    return out


def _swallows(name, t0, t1, path) -> list:
    if len(t1.swallows) > len(t0.swallows):
        return [Finding("B2", "exception-swallowed", path, name, t1.swallows[-1],
                        "a broad except that does nothing was added")]
    return []


def _names_used(node) -> set:
    out = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name):
            out.add(sub.id)
        elif isinstance(sub, ast.Attribute):
            out.add(sub.attr)
    return out


def _unmatched(inv0, inv1, path, removed_symbols) -> tuple:
    """Pair renamed tests; report deleted and no-longer-collected ones."""
    tests0, tests1 = inv0.tests(), inv1.tests()
    gone = [n for n in tests0 if n not in tests1]
    new = [n for n in tests1 if n not in tests0]
    pairs, out = [], []
    file1 = _file_texts(inv1)
    for name in gone:
        t0 = tests0[name]
        twin = next((f for f in inv1.functions.values()
                     if f.body_dump == t0.body_dump and f.name not in tests0), None)
        if twin is not None and not twin.collects:
            out.append(Finding("B2", "test-uncollected", path, name, twin.node.lineno,
                               f"renamed to {twin.name}, which pytest does not collect"))
            continue
        texts = Counter(c.text for c in t0.checks)
        partner = next((n for n in new if tests1[n].body_dump == t0.body_dump), None) \
            or next((n for n in new if texts and
                     Counter(c.text for c in tests1[n].checks) == texts), None)
        if partner is not None:
            new.remove(partner)
            pairs.append((name, partner))
            continue
        if texts and all(file1[t] >= n for t, n in texts.items()):
            continue                               # its checks live on elsewhere
        tier = "declared" if _names_used(t0.node) & removed_symbols else "finding"
        out.append(Finding("B2", "test-deleted", path, name, t0.node.lineno,
                           f"{len(t0.checks)} checks removed with the test", tier))
    return pairs, new, out


def compare_file(path, before, after, removed_symbols=frozenset()) -> "list | None":
    """Findings for one test file. `before` or `after` may be None (added or
    deleted file). Returns None when a side does not parse."""
    inv0 = inventory(before) if before is not None else inventory("")
    inv1 = inventory(after) if after is not None else inventory("")
    if inv0 is None or inv1 is None:
        return None
    lines1 = (after or "").splitlines()
    tests0, tests1 = inv0.tests(), inv1.tests()
    pairs, new, out = _unmatched(inv0, inv1, path, set(removed_symbols))
    pairs += [(n, n) for n in tests0 if n in tests1]
    for old_name, new_name in pairs:
        t0, t1 = tests0[old_name], tests1[new_name]
        out += _compare_checks(new_name, t0, t1, inv0, inv1, path)
        out += _markers(new_name, t0, t1, path, lines1)
        out += _tolerances(new_name, t0, t1, path, lines1)
        out += _swallows(new_name, t0, t1, path)
        if t0.body_dump != t1.body_dump:
            out += _b4(new_name, t1, inv1, path)
    for name in new:
        out += _b4(name, tests1[name], inv1, path)
    out += _module_skips(before or "", after or "", path, lines1)
    return out


def _b4(name, facts, inv, path) -> list:
    return [Finding("B4", rule, path, name, line, detail)
            for rule, line, detail in tautologies(facts, inv.helpers)]


def _module_level(source) -> list:
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return []
    out = []
    for stmt in tree.body:
        text = " ".join(ast.unparse(stmt).split())
        targets = [t.id for t in getattr(stmt, "targets", []) if isinstance(t, ast.Name)]
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if "pytestmark" in targets or _MODULE_SKIP.search(text):
            out.append((text, stmt.lineno))
    return out


def _module_skips(before, after, path, lines1) -> list:
    """A whole file skipped: `pytestmark = ...skip` or a module-level skip call."""
    old = Counter(t for t, _ in _module_level(before))
    out = []
    for text, line in _module_level(after):
        if old[text] > 0:
            old[text] -= 1
            continue
        if "skip" not in text and "xfail" not in text:
            continue
        reason = _REASON.search(text) and ("skipif" in text or "importorskip" in text
                                           or text.startswith("if "))
        tier = "declared" if reason or _commented(lines1, line) else "finding"
        out.append(Finding("B2", "skip-added", path, "<module>", line, text[:120], tier))
    return out


def defined_symbols(source) -> set:
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return set()
    return {n.name for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
