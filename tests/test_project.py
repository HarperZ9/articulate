"""The project config: discovery, profile globs, terminology rules on every
surface, allowed and freeze terms, and loud failure on a malformed file.

Each terminology rule has a positive case, a negative case, and a control
(code spans and URLs are masked; --config none turns the rules off), so a pass
cannot come from a rule that fires everywhere or nowhere.
"""
import json
import os
import shutil

import pytest

import articulate
from articulate import cli, guard, lsp_server, profiles, project, receipt

_TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_tmp_project")
CONFIG = {
    "version": 1,
    "profiles": {"notes/**": "essay", "*.txt": "readme"},
    "terminology": {
        "banned": [{"term": "whitelist", "suggestion": "allowlist",
                    "reason": "inclusive language"}],
        "preferred": [{"use": "sign in", "instead_of": ["log in", "login"]}],
        "allowed": ["leverage"],
    },
    "freeze": ["Articulate"],
    "protect": {"quotes": False},
}
BANNED_TEXT = "Add the host to the whitelist before you deploy.\n"


@pytest.fixture()
def work():
    shutil.rmtree(_TMP, ignore_errors=True)
    os.makedirs(os.path.join(_TMP, "notes", "deep"))
    with open(os.path.join(_TMP, project.CONFIG_NAME), "w", encoding="utf-8") as fh:
        json.dump(CONFIG, fh)
    yield _TMP
    shutil.rmtree(_TMP, ignore_errors=True)


def _write(work, rel, text):
    p = os.path.join(work, rel)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)
    return p


def _rules(result):
    return {f["rule_id"]: f for f in result["high"] + result["medium"] + result["low"]}


def _check(work, text, rel="a.md"):
    path = _write(work, rel, text)
    return articulate.check_text(text, profile=project.resolve(
        path, text, cfg=project.for_path(path))[1])


def test_discovery_walks_up_and_can_be_turned_off(work):
    deep = _write(work, "notes/deep/x.md", "text\n")
    assert project.discover(deep) == os.path.join(work, project.CONFIG_NAME)
    assert project.for_path(deep, "none") is None


def test_glob_profile_sits_between_the_in_file_tag_and_the_path(work):
    cfg = project.for_path(os.path.join(work, "a.md"))
    assert project.resolve(os.path.join(work, "notes/deep/x.md"), "", cfg=cfg)[0] == "essay"
    assert project.resolve(os.path.join(work, "b.txt"), "", cfg=cfg)[0] == "readme"
    tagged = "<!-- writing-profile: chat -->\n"
    assert project.resolve(os.path.join(work, "notes/x.md"), tagged, cfg=cfg)[0] == "chat"
    assert project.resolve(os.path.join(work, "notes/x.md"), tagged, profile="commit",
                           cfg=cfg)[0] == "commit"
    assert project.resolve(os.path.join(work, "a.md"), "", cfg=cfg)[0] == profiles.DEFAULT


def test_banned_term_fires_with_its_suggestion_and_gates(work):
    r = _check(work, BANNED_TEXT)
    f = _rules(r)["terminology/banned/whitelist"]
    assert f["tier"] == "HIGH" and "allowlist" in f["label"] and f["match"] == "whitelist"
    assert r["gate"] == "blocked"
    assert "terminology/banned/whitelist" not in _rules(
        _check(work, "Add the host to the allowlist before you deploy.\n"))


def test_terms_in_code_and_urls_are_masked(work):
    r = _check(work, "Set `whitelist = true` per https://example.com/whitelist today.\n")
    assert not any(k.startswith("terminology/") for k in _rules(r))


def test_preferred_form_fires_on_each_variant(work):
    r = _check(work, "Log in first. Then use the login page.\n")
    hits = [f for f in r["medium"] if f["rule_id"] == "terminology/preferred/sign-in"]
    assert [h["match"] for h in hits] == ["Log in", "login"]
    assert "terminology/preferred/sign-in" not in _rules(_check(work, "Sign in first.\n"))


def test_match_case_is_honored(work):
    term = {"banned": [{"term": "API", "match_case": True}]}
    prof = project.apply_payload(profiles.load("flavored"), {"terminology": term})
    assert "terminology/banned/api" in _rules(articulate.check_text("Call the API.\n", profile=prof))
    assert "terminology/banned/api" not in _rules(articulate.check_text("A rapid api.\n", profile=prof))


def test_allowed_term_clears_a_vocabulary_rule_but_not_a_device(work):
    plain = articulate.check_text("We leverage caching.\n", profile=profiles.load("flavored"))
    assert any(f["category"] == "corporate-verb" for f in plain["high"])
    assert not any(f["category"] == "corporate-verb" for f in _check(work, "We leverage caching.\n")["high"])
    device = _check(work, "This does not leverage caching, but speed.\n")
    assert device["gate"] == "blocked"


@pytest.mark.parametrize("patch,needle", [
    ({"colour": 1}, "unknown key"),
    ({"profiles": {"*.md": "no-such-profile"}}, "no-such-profile"),
    ({"terminology": {"banned": [{"term": "x"}], "allowed": ["x"]}}, "both flagged and allowed"),
    ({"terminology": {"banned": [{"term": "x", "severity": "fatal"}]}}, "severity"),
    ({"options": {"nope": {"a": 1}}}, "no such rule pack"),
    ({"freeze": "Articulate"}, "freeze"),
    ({"version": 2}, "version"),
])
def test_malformed_config_fails_loudly(work, patch, needle):
    path = _write(work, "bad.json", json.dumps(dict(CONFIG, **patch)))
    with pytest.raises(project.ConfigError) as info:
        project.load(path)
    assert needle in str(info.value) and "bad.json" in str(info.value)


def test_cli_check_sarif_and_gate_use_the_config(work, capsys):
    path = _write(work, "a.md", BANNED_TEXT)
    assert cli.main(["check", path, "--gate"]) == 1
    assert cli.main(["check", path, "--gate", "--config", "none"]) == 0
    capsys.readouterr()
    cli.main(["check", path, "--sarif"])
    sarif = json.loads(capsys.readouterr().out)
    assert "terminology/banned/whitelist" in {r["ruleId"] for r in sarif["runs"][0]["results"]}
    bad = _write(work, "broken.json", "{not json")
    assert cli.main(["check", path, "--config", bad]) == 2


def test_lsp_reports_terms_and_a_broken_config(work):
    path = _write(work, "a.md", BANNED_TEXT)
    uri = "file:///" + path.replace("\\", "/").lstrip("/")
    codes = {d["code"] for d in lsp_server.build_diagnostics(BANNED_TEXT, uri)}
    assert "terminology/banned/whitelist" in codes
    bad = _write(work, "broken.json", "{not json")
    diags = lsp_server.build_diagnostics(BANNED_TEXT, uri, config=bad)
    assert diags[0]["code"] == "config" and "broken.json" in diags[0]["message"]


def test_receipt_embeds_the_rules_and_replays_them(work):
    cfg = project.for_path(os.path.join(work, "a.md"))
    rec = receipt.make_receipt(BANNED_TEXT, "flavored", config=cfg)
    assert rec["project_rules"]["terminology"]["banned"][0]["term"] == "whitelist"
    assert "terminology/banned/whitelist" in {f["rule_id"] for f in rec["findings"]}
    assert receipt.verify_receipt(rec, BANNED_TEXT)[0] == "Match"
    edited = json.loads(json.dumps(rec))
    edited["project_rules"]["terminology"]["banned"] = []
    assert receipt.verify_receipt(edited, BANNED_TEXT)[0] == "Unverifiable"
    edited["project_rules_sha256"] = project.payload_sha256(edited["project_rules"])
    assert receipt.verify_receipt(edited, BANNED_TEXT)[0] == "Drift"


def test_editor_guard_takes_freeze_and_protect_from_the_config(work):
    class Args:
        freeze, allow_change, unprotect, config = [], "", "", None
    g = guard.from_args(Args(), os.path.join(work, "a.md"))
    assert g.freeze == ("Articulate",) and g.protect["quotes"] is False


def test_config_command_shows_what_applies(work, capsys):
    assert cli.main(["config", os.path.join(work, "notes", "x.md"), "--json"]) == 0
    info = json.loads(capsys.readouterr().out)
    assert info["profile"] == "essay" and info["banned"] == 1 and info["freeze"] == ["Articulate"]
