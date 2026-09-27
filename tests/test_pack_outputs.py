"""A domain pack's label can carry the matched words or their counts
(`bcp14-mixed-case` quotes "SHOULD not"; `plain-long-sentence` names a word
count), and a rule id is built from its label. Every content-free output, and a
fairness receipt, keys those findings by category, as it does the two notes
whose ids quote the text. A full receipt keeps the full rule id (the control).
"""
import json

import articulate
from articulate import cli, content_free, fairness, profiles, receipt, rules_ext

TEXT = "Clients SHOULD not retry a request after the first timeout.\n"


def test_every_pack_category_is_keyed_by_category():
    for cat in rules_ext.categories():
        assert content_free.rule_id({"category": cat, "rule_id": cat + "/x"}) == cat
    # Control: a rule from the fixed tables keeps its rule id.
    assert content_free.rule_id({"category": "wordiness", "rule_id": "wordiness/x"}) \
        == "wordiness/x"


def test_a_content_free_receipt_carries_no_pack_label_text():
    full = receipt.make_receipt(TEXT, "normative-spec")
    ids = {f["rule_id"] for f in full["findings"]}
    assert any(i.startswith("bcp14-mixed-case/") and "should-not" in i for i in ids)
    free = receipt.make_receipt(TEXT, "normative-spec", redact="drop")
    ids = {f["rule_id"] for f in free["findings"]}
    assert "bcp14-mixed-case" in ids and not any("should" in i for i in ids)
    assert receipt.verify_receipt(free, TEXT)[0] == "Match"


def test_check_content_free_carries_no_pack_label_text(tmp_path, capsys):
    doc = tmp_path / "spec.md"
    doc.write_text(TEXT, encoding="utf-8")
    cli.main(["check", str(doc), "--profile", "normative-spec", "--json", "--content-free"])
    out = json.loads(capsys.readouterr().out)["results"][0]
    assert out["rule_counts"].get("bcp14-mixed-case") == 1
    assert not any("should" in k for k in out["rule_counts"])


def test_a_fairness_receipt_keys_a_pack_finding_by_category():
    r = articulate.check_text(TEXT, profile=profiles.load("normative-spec"))
    found = [f for t in ("high", "medium", "low") for f in r[t]
             if f["category"] == "bcp14-mixed-case"]
    assert found
    assert {fairness.rule_key(f) for f in found} == {"HIGH|bcp14-mixed-case"}


def test_the_harness_groups_a_profile_with_packs_apart():
    # Profiles with the same config key are measured once, so a pack must split
    # the key; a profile with no pack keeps the key it had before packs existed.
    spec = profiles.load("normative-spec")
    bare = {k: v for k, v in spec.items() if k != "rule_packs"}
    assert fairness.config_key(spec) != fairness.config_key(bare)
    keys = ("gate_level", "keep", "gate_promote", "unit", "structural_classify",
            "dialogue_exempt", "quote_exempt_all", "fiction_slop", "suppress_categories",
            "house")
    before = json.dumps({k: bare.get(k) for k in keys}, sort_keys=True, default=list)
    assert fairness.config_key(bare) == before
