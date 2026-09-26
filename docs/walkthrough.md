# Walkthrough

This is a full pass over one document: a first check, the house style, where the
findings sit, a rewrite, a receipt, a process record, a statement of tool use and
a reviewer's questions. Every step except the rewrite runs locally. The example
file is a short blog draft, `post.md`.

## 1. Check the document

```bash
articulate check post.md --verbose
```

```
[articulate] post.md [flavored]: 0 high, 4 medium, 5 low, gate ok
  L3 [MEDIUM marketing] marketing superlative: We leverage cutting-edge tools ...
  L4 [MEDIUM throat-clearing] throat-clearing opener: ... It is important to note that ...
  L5 [MEDIUM unsupported-authority] authority appeal, no citation nearby: ... studies show ...
  L4 [MEDIUM throat-clearing] worth-noting preamble: ... It is important to note that ...
  L4 [LOW antithesis] not X but Y: ... This is not a feature, but a philosophy ...
  L3 [LOW corporate-verb] leverage / underscore (as corporate verb): We leverage ...
  L5 [LOW stock-transition] stock connective: ... Moreover, the results speak ...
```

The gate reads `ok`: the default profile blocks only the narrow HIGH tier, and
nothing here is in it. The MEDIUM findings carry a reader-cost reason each, and a
strict profile such as `essay` would block on them. The LOW notes are house style
and report without blocking.

## 2. Hold it to the house style, if you chose one

```bash
articulate check post.md --profile house
```

```
[articulate] post.md [house]: 2 high, 5 medium, 2 low, gate blocked
  L4 [HIGH antithesis] not X but Y: ... This is not a feature, but a philosophy ...
  L3 [HIGH corporate-verb] leverage / underscore (as corporate verb): We leverage ...
```

Under `house` the house pack keeps its table tier and blocks. No path selects a
house profile for you; this repository opts in for its own docs.

## 3. See where the findings sit

```bash
articulate check post.md --spans
```

```
[articulate] post.md [flavored]: 4 paragraph(s)
  L1-1 (0H/0M/0L): no findings
  L3-6 (0H/4M/5L): antithesis/not-x-but-y x1, corporate-verb/... x1, ...
  L8-8 (0H/0M/0L): no findings
  L10-10 (0H/0M/0L): no findings
```

Every finding sits in the paragraph on lines 3 to 6. The view counts findings by
rule, in document order. It gives no paragraph a gate, a label or a score, and it
says nothing about who wrote any paragraph; see
[Boundaries](boundaries.md#no-output-is-an-authorship-finding).

## 4. Rewrite for the reader

The editor layer runs through the `claude` CLI, which sends the document to a
hosted Anthropic model.

```bash
python -m articulate.editor --judge post.md
python -m articulate.editor --fix post.md --out post.fixed.md
python -m articulate.editor --polish post.md --mode marketing/persuade
```

`judge` quotes each weak passage and says what a skilled writer would do. `fix`
rewrites so the intended reader can follow the text on one read and re-checks the
result under the same profile. `polish` keeps a pass only when no quality score
falls and the gate stays ok. The house writing standard reaches the model only
under a house profile, and no instruction names an outside score. The rewrite is
a suggestion; read it against the original.

## 5. Record a re-derivable receipt

```bash
articulate receipt post.md > post.receipt.json
articulate verify post.receipt.json post.md
```

```
[articulate] Match: re-derived 9 findings, gate ok
```

The receipt pins the text hash and a fingerprint of the whole ruleset. A change
to a rule or a scanner constant moves the fingerprint, and an old receipt then
reads `Unverifiable`. A content-free receipt (`--redact drop`) keeps no matched
text, and `articulate audit receipts/ --reverify --gate` re-checks a directory of
them in CI.

## 6. Keep your own process record

```bash
articulate process init post.md
articulate process draft post.md
articulate process assist post.md --tool claude --verb edited --sections "paragraph 2"
```

The log lives in `.articulate/process/` beside the document, with a `.gitignore`
of its own. A draft entry holds a salted commitment, its sequence and the day,
and nothing else unless you opted in:

```
{"schema": "articulate/process/v1", "seq": 2, "kind": "draft", "day": "2026-09-26",
 "commitment": "sha256:cdd1...", "prev": "sha256:a911...", "hash": "sha256:936b..."}
```

`articulate process export post.md --reveal 2` writes a process summary with
draft 2's text and salt attached, so a reader can check them against the
commitment. What the summary shows, and what it cannot, is in
[Boundaries](boundaries.md#a-process-summary-is-declared-provenance).

## 7. Write the statement of tool use

```bash
articulate disclose post.md
```

```
Statement of tool use and authorship

Assistance
- Edited with claude: paragraph 2.

Responsibility
The writer takes responsibility for every line of this text.
```

The verb comes from the recorded task. With a `contributions.json`, the statement
adds CRediT roles for people, and it refuses to list a model as an author.

## 8. Prepare a reviewer's questions

```bash
articulate desk post.md --venue paper
```

```
Inside the document
  [missing-section] The venue asks for a limitations section. Where are the limits stated?
  [missing-tool-statement] The venue asks for a statement of tool use. Is one attached?
  L4 [unsupported-authority] Which sources does 'studies show' refer to?
  L5 [number-without-source] Where does 38% in paragraph 2 come from?

Across the field
  What does this work let us learn that we did not know before?
  ...
```

The desk prints questions, never a score or a ranking. The across-the-field
questions always appear, even when every inside check passes.

## 9. Wire it into continuous integration

```bash
articulate check "**/*.md" --sarif > articulate.sarif
```

GitHub code scanning, Azure DevOps and reviewdog render SARIF inline. Each rule's
help text carries its reader-cost reason and the does-not-prove line. The
repository ships a GitHub Action and a pre-commit hook; see
[Features](features.md#surfaces).
