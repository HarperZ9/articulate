# Walkthrough

This is a full pass over one document: a first check, the house style, where the
findings sit, a rewrite, a receipt, a process record, a statement of tool use and
a reviewer's questions. Every step except the rewrite runs locally. The example
file is a short blog draft, `examples/post.md` in the repository, and a test
reruns each command below that shows its full output.

## 1. Check the document

```bash
articulate check post.md --verbose
```

```
[articulate] post.md [flavored]: 0 high, 2 medium, 1 low, gate ok
  L3 [MEDIUM marketing] marketing superlative: We leverage cutting-edge tools to help teams write. It is important to note that this is not a featu
      why: An unsupported superlative claims a comparison the text never makes, so the reader cannot check it.
  L4 [MEDIUM unsupported-authority] authority appeal, no citation in the sentence: a feature, but a philosophy. Studies show that clear docs cut support tickets. Moreover, the result
      why: An appeal to unnamed studies or experts gives the reader no source to check; cite the source, or state the claim as your own view with an example.
  L3 [LOW expletive-opener] empty opener (it is important / worth): ge tools to help teams write. It is important to note that this is not a feature, but a philosophy.
      why: An opening 'It is important to' is metadiscourse that delays the subject; the reader waits for the claim it announces.
[articulate] These findings name prose patterns and where they occur. They do not show who or what wrote the text, and no finding or count is a basis for an accusation.
```

The gate reads `ok`: the default profile blocks only the narrow HIGH tier, and
nothing here is in it. Each finding carries a reader-cost reason, which
`--verbose` prints under it, and a strict profile such as `essay` would block on
the MEDIUM ones. The LOW note reports without
blocking. The house style's patterns (the contrast device and the corporate
verb here) do not show at all outside a house profile unless you pass
`--house-notes`.

## 2. Hold it to the house style, if you chose one

```bash
articulate check post.md --profile house
```

```
[articulate] post.md [house]: 2 high, 3 medium, 1 low, gate blocked
  L4 [HIGH antithesis, house style] not X but Y: mportant to note that this is not a feature, but a philosophy. Studies show that clear docs cut supp
  L3 [HIGH corporate-verb, house style] leverage / underscore (as corporate verb): We leverage cutting-edge tools to help teams write. It is important to note that this is not a featu
  L3 [MEDIUM marketing] marketing superlative: We leverage cutting-edge tools to help teams write. It is important to note that this is not a featu
  L5 [MEDIUM stock-transition, house style] stock connective: ear docs cut support tickets. Moreover, the results speak for themselves: tickets fell 38% in one qu
  L4 [MEDIUM unsupported-authority] authority appeal, no citation in the sentence: a feature, but a philosophy. Studies show that clear docs cut support tickets. Moreover, the result
[articulate] These findings name prose patterns and where they occur. They do not show who or what wrote the text, and no finding or count is a basis for an accusation.
```

Under `house` the house pack keeps its table tier and blocks, and each of its
findings says `house style`. Every result ends with the does-not-prove line.
No path selects a house profile for you; this repository opts in for its own
docs.

Some writing has rules of its own. A file of UI strings, one per line, checks
under `ux-microcopy`:

```
button: Save And Continue To The Next Step
label: Name
error: Something went wrong.
button: Cancel
link: For details, click here.
```

```bash
articulate check strings.txt --profile ux-microcopy --verbose
```

```
[articulate] strings.txt [ux-microcopy]: 0 high, 2 medium, 2 low, gate blocked
  L1 [MEDIUM ux-length] button label has 7 words and 34 characters; the limit is 3 words and 26 characters: button: Save And Continue To The Next Step
      why: A long button, label or error sentence takes longer to scan, can be cut off on a small screen, and hides the action the reader came to take.
  L5 [MEDIUM ux-link-text] link text that names no destination; name where the link goes: link: For details, click here.
      why: Link text such as 'click here' tells a reader who scans the links, or hears them read aloud, nothing about where the link goes.
  L1 [LOW ux-case] title case in a UI string; this project uses sentence case: button: Save And Continue To The Next Step
      why: Mixed capitalization across one interface makes the reader wonder whether the capitals mark a name or a term.
  L3 [LOW ux-vague-error] error text without a cause and a next step: say what happened and what to do: error: Something went wrong.
      why: An error message that names no cause and no next step leaves the reader unable to recover.
[articulate] These findings name prose patterns and where they occur. They do not show who or what wrote the text, and no finding or count is a basis for an accusation.
```

`code-review`, `plain-language`, and `controlled-english` work the same way, and
`normative-spec` checks RFC 2119 keywords. See
[Features](features.md#domain-profiles).

A team sets its own vocabulary in a `.articulate.json` at the repository root:

```json
{
  "version": 1,
  "profiles": {"blog/**": "essay"},
  "terminology": {
    "banned": [{"term": "whitelist", "suggestion": "allowlist"}],
    "preferred": [{"use": "sign in", "instead_of": ["log in", "login"]}]
  },
  "freeze": ["Articulate"]
}
```

Every later check of a file under that root reports a banned term as
`terminology/banned/whitelist` with its suggestion, and every rewrite keeps
"Articulate" verbatim. `articulate config post.md` shows what applies.

## 3. See where the findings sit

```bash
articulate check post.md --spans
```

```
[articulate] post.md [flavored]: 4 paragraph(s)
  L1-1 (0H/0M/0L): no findings
  L3-6 (0H/2M/1L): expletive-opener/empty-opener-it-is-important-worth x1, marketing/marketing-superlative x1, unsupported-authority/authority-appeal-no-citation-in-the-sentence x1
  L8-8 (0H/0M/0L): no findings
  L10-10 (0H/0M/0L): no findings
[articulate] These findings name prose patterns and where they occur. They do not show who or what wrote the text, and no finding or count is a basis for an accusation.
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
writes a rewrite so the intended reader can follow the text on one read and
re-checks it under the same profile. `polish` keeps a pass only when no quality
score falls, the gate does not go from ok to blocked and no note the mode
requires opens. The house writing
standard reaches the model only under a house profile, and no instruction names
an outside score. The rewrite is
a suggestion; read it against the original.

The model never sees your code, math, links, citations, or quotes. Each one is
swapped for a placeholder before the rewrite and spliced back byte for byte after
it, and a rewrite that loses a placeholder is refused.

Every rewrite also passes the meaning guard before it lands. If the model drops a
number, flips a negation, weakens a "must" to a "should", or loses a link, a code
span, a citation, or a name, the rewrite is refused, the previous text stays, and
the output names what blocked it:

```
[fix] pass 1 refused: meaning guard refused the rewrite: changed modal 'must' (L3) -> 'should' (L3); kept the previous text
```

Run the same check on any two versions, with a gate for continuous integration:

```bash
articulate compare post.md post.fixed.md --gate
```

To see what changed and why, add `--explain`. Each changed sentence is shown
before and after, with the detector findings it carried:

```bash
python -m articulate.editor --fix post.md --explain
```

```
[changes] post.md -> post.fixed.md: 1 change(s); detector findings 1 -> 0; meaning preserved
  #1 L3 replace
    - We rely on cutting-edge tools.
    + We rely on current tools.
      flagged before: MEDIUM marketing/marketing-superlative: marketing superlative: 'cutting-edge'
[changes] does not prove: The invariants are surface proxies. A rewrite can keep every one of them and still change the meaning, for example by moving a negation into another clause, swapping the order of two numbers, or changing a word no invariant covers. A capitalized word that opens a sentence may be an ordinary word, so it counts as a name only when the text also uses it as one mid-sentence: a name used once, at a sentence start, can be swapped for another unreported. A reported change can also be harmless. 'preserved' is a screen, never a proof that the two texts say the same thing.
```

Had the model written "We rely on two tools", the guard would have refused it:
"two" is a number the original never stated.

`--explain json` writes the same report as JSON for a review tool.

The guard compares surface facts, so a rewrite can pass it and still shift a
claim. See [Boundaries](boundaries.md).

## 5. Record a re-derivable receipt

```bash
articulate receipt post.md > post.receipt.json
articulate verify post.receipt.json post.md
```

```
[articulate] Match: re-derived 3 findings, gate ok
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
[desk] Prepares the questions a reviewer should ask, inside the document and across the field. It checks the document's own statements and cannot judge contribution, novelty or significance.

Inside the document
  [missing-section] The venue asks for a limitations section. Where are the limits stated?
  [missing-tool-statement] The venue asks for a statement of tool use. Is one attached?
  L4 [unsupported-authority] Which sources does 'Studies show' refer to?
      "Studies show that clear docs cut support tickets."
  L5 [number-without-source] Where does 38% in paragraph 2 come from?
      "Moreover, the results speak for themselves: tickets fell 38% in one quarter."

Across the field
  What does this work let us learn that we did not know before?
  How does it change how the field should think about the problem?
  What future work does it make possible, and what does it rule out?
  Which closest prior work does it build on, contradict or supersede, and does it say so?
  If every local claim holds, does the contribution still matter?

[desk] This question points at the document's own statement. It says nothing about who or what wrote the text, or about the merit of the work.
```

The desk prints questions, never a score or a ranking. The across-the-field
questions always appear, even when every inside check passes.

## 9. Wire it into continuous integration

```bash
shopt -s globstar      # bash: let ** reach every folder depth
articulate check **/*.md --sarif > articulate.sarif
```

GitHub code scanning, Azure DevOps and reviewdog render SARIF inline. Each rule's
help text carries its reader-cost reason and the does-not-prove line. The
repository ships a GitHub Action and a pre-commit hook; see
[Features](features.md#surfaces).
