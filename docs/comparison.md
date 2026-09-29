# Compare a proposed rewrite

The Python comparison API reports changes to selected surface features before
a caller accepts an edit. It runs locally and uses only the standard library.
This API is on the unreleased main branch; it is not part of the 0.5.2 package.

```python
from articulate.meaning import compare

report = compare("The limit is 10 ms.", "The limit is 20 ms.")
assert report["verdict"] == "changed"
```

The report uses schema `articulate/meaning/v1`. Each item has a kind, a status
(`kept`, `dropped`, `added`, or `changed`), and before/after text with offsets.
Offsets use Python string positions, with an exclusive end. Line and column
numbers start at one. A missing side is `None`.

The screen covers numbers, units, dates, times, versions, modal strength,
scope, negation, names, citations, URLs, code, math and quoted material.
Pass `freeze=("project name",)` to compare exact terms, `tex=True` for TeX
containers, or `quotes=False` to read quoted material as editable prose.
Freeze terms use Unicode normalization and whole-word matching.

A `preserved` verdict means these features match. It does not establish
semantic equivalence or factual truth. Reordering numbers or moving a negation
between clauses can preserve the extracted features while changing meaning.
A name used only at the start of a sentence may go unreported. A reported
change can also be harmless. Every report includes a `does_not_prove` field.

Reports contain source text. They are not content-free receipts. This explicit
API does not change the editor's default acceptance checks, the detector, or
the default profile. The held ruleset on main still blocks package publication.
