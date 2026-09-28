"""G2 when one arm has no hit of a rule (ruleset 0.9.0 harness).

The percentile bootstrap of a rate ratio cannot resample a hit that never
occurred: with no hit in the lower arm every resample gives an infinite ratio
and the interval reads [inf, inf], so a rule with a handful of hits read as
skewed; with no hit in the numerator arm the interval read [0, 0], so a rare
rule read as not skewed (fairness review 8). The interval now comes from the
exact conditional method: given all hits, the empty arm's count is binomial with
that arm's share of hits, and the Clopper-Pearson limit on the share bounds the
ratio. The G2 states and thresholds do not change. This reading changes a gate's
method and can turn a failing row into a passing one, so it is its own commit.
The counts are made up and measure nothing about fairness to any group.
"""
from articulate import fairness_gates

MANY = [{"words": 100, "rules": {"R": 3}} for _ in range(40)]
NONE = [{"words": 100, "rules": {}} for _ in range(100)]


def test_an_empty_lower_arm_gets_an_exact_conditional_lower_limit():
    row = fairness_gates.g2_state(MANY, NONE, "R")
    q = 1 - 0.025 ** (1 / 120)                   # Clopper-Pearson upper, 0 of 120
    lower = (1 - q) / q * (100 * 100) / (40 * 100)
    assert row["ratio"] == "inf"
    assert row["ci"] == [round(lower, 2), "inf"]
    assert row["ci_method"] == "exact conditional"
    assert row["state"] == "skewed"


def test_an_empty_numerator_arm_gets_an_exact_conditional_upper_limit():
    row = fairness_gates.g2_state(NONE, MANY, "R")
    q = 1 - 0.025 ** (1 / 120)                   # share of hits in the empty arm
    upper = q / (1 - q) * (40 * 100) / (100 * 100)
    assert row["ratio"] == 0.0
    assert row["ci"] == [0.0, round(upper, 2)]
    assert row["state"] == "not skewed"


def test_a_rare_rule_with_an_empty_arm_reads_bounded_not_skewed():
    # 23 hits in 23 of 2,000 reference texts and none in 100 protected ones:
    # equal rates would put about 1.2 hits in the protected arm, so an empty arm
    # is not evidence of a ratio above 1.
    ref = [{"words": 100, "rules": {"R": 1}} for _ in range(23)] + \
          [{"words": 100, "rules": {}} for _ in range(1977)]
    prot = [{"words": 100, "rules": {}} for _ in range(100)]
    row = fairness_gates.g2_state(ref, prot, "R")
    assert row["ci"][0] < 1
    assert row["state"] == "bounded"


def test_a_rare_rule_with_an_empty_numerator_is_not_called_not_skewed():
    # Three hits in three of 100 texts and none in 100: equal rates are well
    # inside the interval, so "not skewed" (an upper limit below 2) does not
    # hold, and 3% of texts is above the bounded share.
    few = [{"words": 100, "rules": {"R": 1}} for _ in range(3)] + \
          [{"words": 100, "rules": {}} for _ in range(97)]
    row = fairness_gates.g2_state(NONE, few, "R")
    assert row["ci"][1] >= 2
    assert row["state"] == "inconclusive"


def test_both_arms_with_hits_keep_the_bootstrap():
    row = fairness_gates.g2_state(MANY, MANY, "R")
    assert "ci_method" not in row
    assert row["state"] == "not skewed"


def test_both_arms_empty_stay_bounded():
    row = fairness_gates.g2_state(NONE, NONE, "R")
    assert "ci_method" not in row
    assert row["state"] == "bounded"
