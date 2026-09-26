"""The editor's objective is the reader, never an outside score.

`fix`, `polish` and `judge` target the deliverable: the reader the mode names and
the job the text must do. A rewrite is accepted on the quality scores, the gate
under the chosen profile and the required advisories. These tests pin that:

  static      the prompt templates name no detector, score or evasion term
  captured    every instruction a model call receives, on a fixture run, is free
              of the same terms
  metamorphic density and cadence are replaced by random values and every accept
              or reject decision in polish stays the same
  signature   accept() takes quality scores, gate state, required advisories and
              a guard result, and no pattern score
  imports     no module imports a detector client or a network library
  house       a writer who did not choose the house style is never asked to
              clear house-style patterns
"""
import ast
import inspect
import pathlib
import random
import re

import pytest

import articulate
from articulate import editor, mcp_server, prompts

BANNED = re.compile(
    r"(?i)\bdetector|\bdetection\b|\bai[- ]generated\b|\bhuman[- ]written\b|\btexture\b"
    r"|\bperplexity\b|\bburstiness\b|\bundetectable\b|\bpass as\b|\bhumani[sz]e"
    r"|\bgptzero\b|\bpangram\b|\bturnitin\b|\boriginality\b|\bcopyleaks\b|\bzerogpt\b"
    r"|\bsentence length varies\b|\bvary sentence length\b|\bsounds? human\b"
    r"|\bskilled human writing\b")
PKG = pathlib.Path(articulate.__file__).parent


class Capture:
    def __init__(self, reply):
        self.reply = reply
        self.instructions = []

    def __call__(self, instructions, text, timeout=600):
        self.instructions.append(instructions)
        return self.reply(instructions, text)


def _reply(instructions, text):
    if '"concreteness"' in instructions:
        return ('{"concreteness":4,"commitment":4,"economy":4,"rhythm":4,'
                '"restatable":4,"overall":"excellent","worst":[]}')
    return "The rain fell for three days on the low field behind the barn.\n"


def test_static_prompt_templates_carry_no_banned_term():
    for name in ("STANDARD", "HOUSE_STANDARD", "CONTENT_BOUNDARY", "EXCELLENCE",
                 "QUALITY_INSTRUCTIONS", "JUDGE_TASK", "REWRITE_TASK"):
        text = getattr(prompts, name)
        m = BANNED.search(text)
        assert not m, (name, m and m.group(0))


@pytest.fixture
def work(tmp_path):
    p = tmp_path / "draft.md"
    p.write_text("It is important to note that the rain fell for three days. "
                 "We delve into the data.\n", encoding="utf-8")
    return p


def test_every_captured_instruction_is_clean(work, monkeypatch, capsys):
    cap = Capture(_reply)
    monkeypatch.setattr(editor, "claude_call", cap)
    editor.judge(str(work))
    editor.fix(str(work), str(work) + ".fixed", passes=1)
    editor.polish(str(work), str(work) + ".pol", passes=1, bar=4)
    editor.polish(str(work), str(work) + ".pol2", passes=1, bar=4, mode="memo/explain")
    editor.quality_judge("Some text.\n")
    mcp_server.do_judge("Some text.\n")
    mcp_server.do_fix("Some text.\n")
    mcp_server.do_polish("Some text.\n", passes=1)
    assert len(cap.instructions) >= 8
    for instr in cap.instructions:
        m = BANNED.search(instr)
        assert not m, (m.group(0), instr[:200])


def test_house_patterns_reach_the_model_only_under_a_house_profile(work, monkeypatch):
    work.write_text("We used paper forms rather than tablets, and the — dash stayed.\n",
                    encoding="utf-8")
    cap = Capture(_reply)
    monkeypatch.setattr(editor, "claude_call", cap)
    editor.fix(str(work), str(work) + ".a", passes=1)
    default = cap.instructions[-1]
    editor.fix(str(work), str(work) + ".b", passes=1, profile="house")
    house = cap.instructions[-1]
    assert "substitution" not in default and "Ban these devices" not in default
    assert "substitution" in house and "Ban these devices" in house


def _polish_decisions(work, monkeypatch, scramble):
    texts = iter(["The rain fell for three days.\n", "Rain fell for three days.\n",
                  "It rained for three days on the field.\n"])
    scores = iter([3, 4, 3])

    def rewrite(t, mech, worst):
        return next(texts)

    def judge(t):
        s = next(scores, 4)
        return {k: s for k in editor.QUALITIES}

    if scramble:
        rng = random.Random(7)
        from articulate import gate, scan
        monkeypatch.setattr(gate, "density", lambda r: {
            "count": rng.randint(0, 99), "words": 1, "per_1000": rng.random(),
            "ci": [0, 1], "shown": True, "min_words": 0})
        monkeypatch.setattr(scan, "cadence_stats", lambda text: {
            "sentences": rng.randint(0, 50), "uniform": rng.random() > 0.5,
            "repetitive_openers": rng.random() > 0.5, "cv": rng.random(),
            "mean_len": rng.random() * 30})
    out = work.parent / ("s.md" if scramble else "p.md")
    editor.polish(str(work), str(out), passes=3, bar=5, rewrite_fn=rewrite, judge_fn=judge)
    return out.read_text(encoding="utf-8")


def test_density_and_cadence_never_change_an_accept_decision(work, monkeypatch, capsys):
    plain = _polish_decisions(work, monkeypatch, scramble=False)
    scrambled = _polish_decisions(work, monkeypatch, scramble=True)
    assert plain == scrambled


def test_accept_signature_names_no_pattern_score():
    params = list(inspect.signature(editor.accept).parameters)
    assert params == ["before_scores", "after_scores", "before_gate", "after_gate",
                      "required_open", "guard"]
    for p in params:
        assert not re.search(r"density|cadence|texture|score_pattern|detector", p)


def test_accept_rules():
    good = {k: 4 for k in editor.QUALITIES}
    worse = dict(good, economy=3)
    assert editor.accept(good, good, "ok", "ok", set(), None)[0]
    assert not editor.accept(good, worse, "ok", "ok", set(), None)[0]
    assert not editor.accept(good, good, "ok", "blocked", set(), None)[0]
    assert not editor.accept(good, good, "ok", "ok", set(), {"ok": False})[0]


NETWORK = {"socket", "ssl", "http", "urllib.request", "urllib.error", "requests",
           "httpx", "aiohttp", "ftplib", "smtplib", "websocket", "websockets"}
DETECTOR_CLIENTS = {"gptzero", "pangram", "originality", "copyleaks", "zerogpt",
                    "turnitin", "sapling", "crossplag", "winston", "gltr"}


def _imports(path):
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            for a in node.names:
                yield a.name
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            yield node.module


def test_no_module_imports_a_detector_client_or_a_network_library():
    for p in PKG.glob("*.py"):
        names = set(_imports(p))
        bad = {n for n in names for b in NETWORK | DETECTOR_CLIENTS
               if n == b or n.startswith(b + ".")}
        assert not bad, (p.name, bad)


def test_only_the_model_backend_starts_a_subprocess():
    users = {p.name for p in PKG.glob("*.py") if "subprocess" in set(_imports(p))}
    assert users <= {"editor.py", "claude_cli.py"}, users


def test_rewrite_delta_measures_vocabulary_lift_and_rhythm():
    from articulate import editor_metrics as M
    plain = "The cat sat. The dog ran. We ate. It rained."
    fancy = "The magnificent feline positioned itself comfortably upon the carpet while outside everything was drenched."
    d = M.rewrite_delta(plain, fancy)
    assert d["mean_word_length"] > 0 and d["long_word_share"] > 0
    assert M.rewrite_delta(fancy, plain)["long_word_share"] < 0


def test_no_accept_or_receipt_path_reads_the_editor_metrics():
    for name in ("editor.py", "polish.py", "fix.py", "receipt.py", "gate.py"):
        assert "editor_metrics" not in (PKG / name).read_text(encoding="utf-8"), name
