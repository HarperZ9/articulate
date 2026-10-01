"""Synthetic model replies for the house-voice tests.

Every reply below was written for these tests. None is taken from a person's
writing, and none comes from a private corpus.
"""

RESIDUE_REPLY = """Great question!

The cache misses because the key includes the request time. I changed `make_key` in cache.py:41 so it drops the timestamp, and the hit rate on the test run rose from 12 of 200 to 187 of 200.

I hope this helps! Let me know if you have any other questions."""

RESIDUE_CLEAN = """The cache misses because the key includes the request time. I changed `make_key` in cache.py:41 so it drops the timestamp, and the hit rate on the test run rose from 12 of 200 to 187 of 200."""

DASH_REPLY = """The build failed twice — both times on the Windows runner.

```python
x = 1  # keep — this dash is inside code
```

> A quoted line keeps its dash — exactly as written.

See https://example.com/a—b for the log."""

DISCLOSURE_REPLY = """Drafted with help from Claude and edited by the author.

Great question!

The report covers 14 sites — all in one county."""

HUMAN_CLAIM_REPLY = """When I was a kid I learned to read maps on long drives.

The route in routes.json:12 takes 41 minutes at the posted limits."""

ACTION_REPLY = """I read routes.json and ran the planner twice. Both runs chose the coast road, 41 minutes at the posted limits.

I did not check live traffic."""

CONTENT_OFFER = "Let me know if you want me to run the migration on staging tonight."

LONG_REPLY = ("The parser reads each line once and keeps a running count of open "
              "brackets, so a file of 2,000 lines costs one pass. " * 60).strip()
