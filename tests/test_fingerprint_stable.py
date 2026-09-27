"""The ruleset fingerprint is the same in every process.

A receipt pins the fingerprint, and verify recomputes it in a new process. A
set's repr follows the per-process hash seed, so a fingerprint that hashed one
would move between runs and a fresh receipt could read Unverifiable. Each run
below uses a different PYTHONHASHSEED.
"""
import os
import subprocess
import sys

CODE = "from articulate.fingerprint import ruleset_fingerprint as f; print(f())"


def _fingerprint(seed):
    env = dict(os.environ, PYTHONHASHSEED=str(seed))
    out = subprocess.run([sys.executable, "-c", CODE], env=env, capture_output=True,
                         text=True, check=True)
    return out.stdout.strip()


def test_the_fingerprint_does_not_depend_on_the_hash_seed():
    seen = {_fingerprint(seed) for seed in (0, 1, 2, 3, 4, 5)}
    assert len(seen) == 1, seen
    assert next(iter(seen)).startswith("sha256:")
