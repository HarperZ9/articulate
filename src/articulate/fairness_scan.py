#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.fairness_scan -- document scanning for the fairness harness,
in one process or several.

`python -m articulate.fairness MANIFEST --jobs N` measures documents in N
worker processes. Each worker loads the same profiles by name, in the same
order, and measures whole documents under every configuration. The parent
reads the results back in document order and computes every statistic itself,
as a single-process run does, so the receipt is byte-identical. A test pins
that on a synthetic corpus.

Only the per-document measurements cross a process boundary. They hold
counts, rule keys and flags, never text.

Standard library only.
"""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor

from . import fairness as F

_WORKER = []


def scan_document(text, profs):
    """[(measurement, layout changed)] for one document, one entry per profile
    in `profs`, in order."""
    out = []
    for prof in profs:
        m = F.measure(text, prof)
        out.append((m, F._layout_applies(prof) and F._layout_changed(text, m, prof)))
    return out


def _init(names):
    _WORKER[:] = [F.load_any(n) for n in names]


def _scan(text):
    return scan_document(text, _WORKER)


def scan(docs, configs, members, jobs=1, chunksize=4):
    """Yield (doc_row, [(measurement, layout changed)]) per document, in the
    order `docs` gives, one entry per configuration in the order of `configs`.

    A worker loads the first profile named for each configuration, which is the
    profile `configs` holds (fairness.configs_for). It does not rebuild the
    configuration keys, so nothing depends on a key string being the same in
    two processes."""
    profs = list(configs.values())
    if jobs <= 1:
        for row, text in docs:
            yield row, scan_document(text, profs)
        return
    docs = list(docs)
    first = [members[k][0] for k in configs]
    with ProcessPoolExecutor(max_workers=jobs, initializer=_init,
                             initargs=(first,)) as ex:
        texts = [text for _row, text in docs]
        for (row, _text), per in zip(docs, ex.map(_scan, texts, chunksize=chunksize)):
            yield row, per
