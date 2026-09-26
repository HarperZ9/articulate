"""The harness statistics on synthetic counts with known answers.

These tests guard the arithmetic against regression. They measure nothing
about fairness: the numbers here are made up or come from textbook examples.
"""
import math
import random

from articulate import fairness_stats as S


def test_wilson_matches_a_textbook_value():
    lo, hi = S.wilson(38, 91)
    assert round(100 * lo, 1) == 32.2 and round(100 * hi, 1) == 52.0


def test_newcombe_reproduces_the_audit_default_profile_gap():
    # The research audit's figure for 38/91 against 21/70: +11.8 [-3.3, +25.7].
    d, (lo, hi) = S.newcombe(38, 91, 21, 70)
    assert (round(100 * d, 1), round(100 * lo, 1), round(100 * hi, 1)) == (11.8, -3.3, 25.7)


def test_newcombe_is_antisymmetric():
    d, (lo, hi) = S.newcombe(10, 50, 20, 60)
    d2, (lo2, hi2) = S.newcombe(20, 60, 10, 50)
    assert math.isclose(d, -d2) and math.isclose(lo, -hi2) and math.isclose(hi, -lo2)


def test_poisson_exact_known_values():
    assert S.poisson_exact(0)[0] == 0.0
    assert math.isclose(S.poisson_exact(0)[1], 3.689, abs_tol=1e-3)
    lo, hi = S.poisson_exact(5)
    assert math.isclose(lo, 1.6235, abs_tol=1e-3) and math.isclose(hi, 11.668, abs_tol=1e-3)


def test_mcnemar_exact_small_cases():
    assert S.mcnemar_exact(0, 0) == 1.0
    assert math.isclose(S.mcnemar_exact(0, 6), 2 / 64)
    assert S.mcnemar_exact(3, 3) == 1.0


def test_bootstrap_draw_uses_random_only():
    # Python guarantees the random() sequence for a seed across versions, not
    # randrange. The draw must come from random() so intervals re-derive.
    rng = random.Random(1)
    expected = [int(random.Random(1).random() * 7) for _ in range(1)]
    assert S._draw(rng, list(range(7)))[:1] == expected


def test_boot2_is_deterministic_and_brackets_the_estimate():
    xs = [0, 1] * 20
    ys = [0, 0, 0, 1] * 10
    est, (lo, hi) = S.boot2(xs, ys, lambda a, b: sum(a) / len(a) - sum(b) / len(b), b=500)
    again = S.boot2(xs, ys, lambda a, b: sum(a) / len(a) - sum(b) / len(b), b=500)
    assert (est, (lo, hi)) == again
    assert lo <= est <= hi


def test_stratified_difference_equals_raw_with_one_stratum():
    d, _ci = S.stratified_diff([(10, 50, 5, 50)])
    assert math.isclose(d, 0.1)
    assert S.stratified_diff([(1, 0, 2, 3)]) is None


def test_stratified_difference_can_differ_from_raw():
    # A group mix that differs across bands: the raw gap and the within-band gap
    # disagree, which is why the harness publishes both.
    strata = [(9, 10, 45, 50), (5, 50, 1, 10)]
    raw = (9 + 5) / 60 - (45 + 1) / 60
    d, _ = S.stratified_diff(strata)
    assert abs(d - raw) > 0.1


def test_min_detectable_shrinks_with_size():
    assert S.min_detectable(91, 70) > S.min_detectable(900, 700)
