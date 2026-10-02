"""The house transform and the SessionStart hook stay within five times their
budgets (docs/house-voice.md). The measured numbers come from
`python -m articulate.bench house`; five times the budget keeps timing noise
on a shared CI runner from failing a build while still catching a regression
of an order of magnitude."""
import json
import os
import subprocess
import sys
import time

from articulate import bench, house

CEILING = 5


def _p95(samples):
    s = sorted(samples)
    return s[max(0, int(round(0.95 * len(s))) - 1)]


def test_bench_text_has_the_requested_length():
    assert len(bench.house_text(300).split()) == 300
    assert len(bench.house_text(2000).split()) == 2000


def test_warm_transform_within_budget():
    for words, budget in ((300, bench.HOUSE_BUDGET_MS["transform_300"]),
                          (2000, bench.HOUSE_BUDGET_MS["transform_2000"])):
        text = bench.house_text(words)
        house.transform(text)
        times = []
        for _ in range(7):
            t0 = time.perf_counter()
            house.transform(text)
            times.append((time.perf_counter() - t0) * 1000)
        assert _p95(times) <= CEILING * budget, (words, times)


def test_session_start_hook_cold_within_budget(tmp_path):
    from articulate import bench_house
    shim = bench_house.shim_bundle(tmp_path / "plugin")
    env = dict(os.environ, ARTICULATE_CONFIG_DIR=str(tmp_path / "cfg"))
    env["ARTICULATE_HOUSE_VOICE"] = "on"
    event = json.dumps({"hook_event_name": "SessionStart", "source": "startup"}).encode()
    times = []
    for _ in range(5):
        t0 = time.perf_counter()
        run = subprocess.run([sys.executable, "-I", "-S", "-B", "-X", "utf8", str(shim)],
                             input=event, capture_output=True, env=env, timeout=30)
        times.append((time.perf_counter() - t0) * 1000)
        assert run.returncode == 0 and b"additionalContext" in run.stdout
    assert _p95(times) <= CEILING * bench.HOUSE_BUDGET_MS["session_start"], times


def test_transform_reports_its_own_timing():
    rec = house.transform(bench.house_text(300))["receipt"]
    assert 0 <= rec["timing_ms"] < 60_000


def test_start_up_note_names_a_slow_interpreter_and_stays_quiet_otherwise():
    from articulate import bench_house
    slow = {"python_start": {"median": 160.0}}
    note = bench_house.start_up_note(slow)
    assert note and "160 ms" in note and "apply_cold_2000_no_site" in note
    assert bench_house.start_up_note({"python_start": {"median": 30.0}}) is None
