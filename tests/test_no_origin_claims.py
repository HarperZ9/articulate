"""No tool-authored text claims to know who or what wrote a text.

Scanned: every rule id and label, every reader-cost reason, every comment,
docstring and string literal in the package (CLI help, MCP descriptions, SARIF
rule text, editor prompts and templates among them), and the key names of every
machine-readable output. Regex patterns are skipped: a pattern that matches a
chat tool's self-identification must spell it. Text a writer supplied and the
tool echoes back is never scanned.

A line that states what Articulate does not claim may carry the marker
`origin-negation`. The count of such lines is pinned below, so growth needs a
reviewed change. Text a writer declares about their own process (the IPTC
labels and disclosure verbs in provenance.py) is exempt through one table, and so
is the table of retired names in aliases.py, which is read and never emitted.

A pattern list misses paraphrase. The pull request template asks a reviewer to
read every new output string against the boundaries page.
"""
import ast
import pathlib
import re

import articulate
from articulate import detector, rule_reasons

PKG = pathlib.Path(articulate.__file__).parent
MARKER = "origin-negation"
MARKER_CEILING = 0

# The research audit's wording count, recorded so it re-derives at any commit:
#   git grep -n -i -E '<this pattern>'
ORIGIN_WORDING_AUDIT = (r"authorship|AI-tell|AI tell|machine texture|machine-texture|"
                        r"human writing|human-written|AI-authored|Pangram|detect AI")

CLAIMS = re.compile(
    r"(?i)\bassistants?\b|\bslop\b|\bmodel prose\b|\bmachine[- ]written\b"
    r"|\bmachine[- ]texture\b|\breads as generated\b|\bhuman writing\b"
    r"|\bhuman[- ]written\b|\bai[- ]generated\b|\bai[- ]authored\b|\bpercent ai\b"
    r"|\blikely ai\b|\bdetect(?:s|ing)? ai\b|\bhumani[sz]e|\bundetectable\b"
    r"|\bauthorship\b|\bpangram\b"
    r"|\btells?\b(?!\s+(?:the|a|an|you|them|us|me|him|her|it|who|what|how|whether|"
    r"which|apart|anyone|readers?|writers?|reviewers?|nothing|each|every|if|when|from))")
# "AI" followed by a hyphen or a space, in an id or a label.
ID_CLAIM = re.compile(r"(?i)\bai[- ]|\bassistant|\bslop\b|\btells?\b")
BANNED_KEYS = {"ai_score", "human_score", "origin", "probability", "likelihood",
               "verdict", "texture_score", "elevated"}
# Modules whose job is to hold text a writer declares about their own process.
DECLARED = {"provenance.py", "aliases.py"}


def _is_pattern(node, parents):
    p = parents.get(node)
    while p is not None and not isinstance(p, ast.Call):
        if isinstance(p, (ast.JoinedStr, ast.BinOp, ast.Tuple, ast.List)):
            p = parents.get(p)
            continue
        return False
    if p is None:
        return False
    fn = p.func
    name = getattr(fn, "attr", None) or getattr(fn, "id", None)
    return name in ("compile", "search", "match", "sub", "finditer", "findall", "fullmatch")


def _strings(path):
    """(line, text) for every comment and every non-pattern string literal."""
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    parents = {c: p for p in ast.walk(tree) for c in ast.iter_child_nodes(p)}
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if not _is_pattern(node, parents):
                yield node.lineno, node.value
    import io
    import tokenize
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == tokenize.COMMENT:
            yield tok.start[0], tok.string


def _hits():
    out, markers = [], 0
    for path in sorted(PKG.glob("*.py")):
        if path.name in DECLARED:
            continue
        for line, text in _strings(path):
            for sub_line in text.splitlines():
                if MARKER in sub_line:
                    markers += 1
                    continue
                m = CLAIMS.search(sub_line)
                if m and "ORIGIN_WORDS" not in sub_line:
                    out.append(f"{path.name}:{line}: {m.group(0)!r} in {sub_line.strip()[:80]!r}")
    return out, markers


def test_no_origin_claim_in_package_text():
    hits, _markers = _hits()
    assert not hits, "\n".join(hits)


def test_negation_markers_stay_under_the_ceiling():
    _hits_, markers = _hits()
    assert markers <= MARKER_CEILING, markers


def test_no_origin_word_in_rule_ids_or_labels():
    tables = (detector.HIGH, detector.MEDIUM, detector.REGISTER_JARGON, detector.LOW,
              detector.FICTION_SLOP, detector.INJECTION)
    for table in tables:
        for cat, label, _rx in table:
            assert not ID_CLAIM.search(cat), cat
            assert not ID_CLAIM.search(label), label
    for cat in detector.known_categories():
        assert not ID_CLAIM.search(cat), cat


def test_no_reason_names_an_origin():
    for cat, (reason, source) in rule_reasons.REASONS.items():
        assert not CLAIMS.search(reason), cat


def _keys(obj, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.add(k)
            _keys(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _keys(v, out)
    return out


def test_no_output_key_is_an_origin_score():
    from articulate import cli, mcp_server, receipt
    text = "We delve into it. As an AI language model, I cannot help.\n\nMore text here.\n"
    outputs = [articulate.check_text(text), mcp_server.do_check(text),
               mcp_server.do_score(text), receipt.make_receipt(text, "flavored", per_span=True),
               cli.to_sarif([dict(articulate.check_text(text), file="a.md", profile="flavored")]),
               {"blocks": detector.analyze_blocks(text)}]
    keys = set()
    for o in outputs:
        _keys(o, keys)
    assert not (keys & BANNED_KEYS), keys & BANNED_KEYS


def test_every_machine_output_carries_does_not_prove():
    from articulate import mcp_server, receipt, tool_text
    text = "The rain fell for three days.\n"
    for o in (articulate.check_text(text), mcp_server.do_check(text),
              mcp_server.do_score(text), receipt.make_receipt(text, "flavored")):
        assert o["does_not_prove"] == tool_text.DOES_NOT_PROVE


def test_sarif_rules_carry_does_not_prove_in_help():
    from articulate import cli, tool_text
    r = dict(articulate.check_text("We delve into it.\n"), file="a.md", profile="flavored")
    sarif = cli.to_sarif([r])
    rules = sarif["runs"][0]["tool"]["driver"]["rules"]
    assert rules
    for rule in rules:
        assert tool_text.DOES_NOT_PROVE in rule["help"]["text"]
        assert tool_text.DOES_NOT_PROVE in rule["help"]["markdown"]
    for res in sarif["runs"][0]["results"]:
        assert res["properties"]["profile"] == "flavored"


def test_the_audit_regex_is_recorded():
    assert re.compile(ORIGIN_WORDING_AUDIT, re.I).search("Pangram")
