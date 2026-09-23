# Walkthrough

This is a full pass over one document, from a first screening to a rewrite to a
committed audit record a reviewer can replay. Every command runs locally. The
example file is a short blog draft, `post.md`, that was written with an assistant
and lightly edited by hand.

## 1. Screen the document

```bash
articulate check post.md --verbose
```

```
[articulate] post.md [readme]: 3 high, 4 medium (blocked)  texture 63/100
  L2 [HIGH corporate-verb] leverage / underscore: We leverage cutting-edge tools.
  L2 [MEDIUM marketing] marketing superlative: We leverage cutting-edge tools.
  L4 [HIGH antithesis] not X but Y: This is not a feature, but a philosophy.
  L6 [MEDIUM stock-transition] stock connective: Moreover, the results speak.
  L8 [HIGH em-dash] em-dash: a small change — and a large payoff.
  L2 [LOW rule-of-three] possible triad (X, Y, and Z): fast, cheap, and reliable
```

The verdict is `blocked` because HIGH findings are present. The texture score of
63 says the whole document reads machine-heavy, beyond the specific device hits.
Each line points at the exact place to fix.

## 2. Localize mixed authorship

A whole-file score hides a single generated paragraph inside otherwise clean
prose. `--spans` scores each paragraph on its own:

```bash
articulate check post.md --spans
```

```
[articulate] post.md [readme]: 4 span(s), 1 flagged
  [ ok ] span 0 L1-1: clean, texture 4/100 (0H/0M): A note on the redesign.
  [FLAG] span 1 L2-8: flagged, texture 88/100 (3H/4M): We leverage cutting-edge
  [ ok ] span 2 L10-12: clean, texture 6/100 (0H/0M): I wrote the rest by hand.
  [ ?? ] span 3 L14-14: unverifiable, texture 0/100 (0H/0M): Thanks for reading.
```

The generated paragraph is span 1 on lines 2 to 8. The hand-written paragraphs
read clean, and the short closing line is `unverifiable` because it falls under
the word floor, so the tool abstains and does not guess.

## 3. Read the judgment-level quality

The detector catches mechanical tells. The editor layer reads the failures a
regex cannot see: a fluent paragraph with no fact a reader could restate, hedging
with no committed position, a weak verb carrying the meaning. It needs a local
model backend or the `claude` CLI.

```bash
python -m articulate.editor --judge post.md
```

The judge quotes each weak passage, names the failure, and says in one line what
a skilled writer would do. It reports; it does not rewrite.

## 4. Rewrite to the standard

`--fix` rewrites to plain, skilled prose and re-runs the detector until the
result is clean. It preserves every number, name, citation, and code span:

```bash
python -m articulate.editor --fix post.md --out post.fixed.md
```

`--polish` runs a stricter loop that stops only when five qualities clear a bar:
concreteness, commitment, economy, rhythm, and a restatable fact in each
paragraph. It accepts a pass only when the detector gate stays clean and no
quality score drops, so a rewrite never regresses.

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
[changes] post.md -> post.fixed.md: 1 change(s); detector findings 2 -> 0; meaning preserved
  #1 L2 replace
    - We leverage cutting-edge tools.
    + We use current tools.
      flagged before: HIGH corporate-verb/leverage-underscore-reflect-as-corporate-verb: leverage / underscore / reflect (as corporate verb): 'leverage'
      flagged before: MEDIUM marketing/marketing-superlative: marketing superlative: 'cutting-edge'
```

Had the model written "We build with two tools", the guard would have refused
it: "two" is a number the original never stated.

`--explain json` writes the same report as JSON for a review tool.

The rewrite is a suggestion. Read it against the original before you ship it. The
guard compares surface facts, so a rewrite can pass it and still shift a claim.
The tool optimizes writing quality, and it never tunes prose toward a lower
detector score. See [Boundaries](boundaries.md).

## 5. Match the register with a mode

A mode crosses a domain register with an articulation need. A memo that argues
wants a different shape from an API reference that explains. List them:

```bash
articulate modes
```

Run the check under one:

```bash
articulate check post.md --mode marketing/persuade
```

A marketing mode blocks the register and marketing tells that a general profile
reports without blocking, and it keeps the terms of art the genre needs. For
fiction, memoir, screenplay, and poetry there is a genre axis that reads by
convention: quoted dialogue is exempt, craft devices report without blocking, and
a report-only lexicon flags generation artifacts. For a proof or a technical
paper, `academic/prove` and `science-writing/explain` protect math and keep rigor
vocabulary clean. See [Features](features.md#writing-modes).

Some writing has rules of its own. A file of UI strings checks under
`ux-microcopy`:

```bash
articulate check strings.txt --profile ux-microcopy --verbose
```

```
[articulate] strings.txt [ux-microcopy]: 0 high, 4 medium (blocked)  texture 0/100
  L1 [MEDIUM ux-length] button label has 7 words and 34 characters; the limit is 3 words and 26 characters: button: Save And Continue To The Next Step
  L5 [MEDIUM ux-link-text] link text that names no destination; name where the link goes: link: For details, click here.
  L3 [LOW ux-vague-error] error text without a cause and a next step: say what happened and what to do: error: Something went wrong.
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

## 6. Record a re-derivable receipt

Once the prose is where you want it, record a receipt so a reviewer can confirm
the screening later:

```bash
articulate receipt post.md --profile readme > post.receipt.json
articulate verify post.receipt.json post.md
```

```
[articulate] Match: re-derived 0 findings, gate ok, texture 4/100
```

The receipt pins the exact text hash and a fingerprint of the whole ruleset. A
change to a rule moves the fingerprint, and an old receipt then reads
`Unverifiable`, so it never disagrees silently.

## 7. Keep an audit record without the source

A team that must retain a record, without keeping the sensitive text, uses a
content-free receipt. It drops the matched substring and the exact offsets, and
keeps only which rule fired and on which line:

```bash
articulate receipt post.md --redact drop --reviewer alice > receipts/post.json
```

Query a directory of committed receipts locally, and re-verify that each still
holds against its source:

```bash
articulate audit receipts/ --reverify --gate
```

```
[audit] 12 receipt(s); gate {'ok': 9, 'blocked': 3}; verdict {'clean': 9, 'flagged': 3}
[audit] stale-ruleset 0; active in last 30d 12
[audit] reverify: {'Match': 11, 'source-changed': 1}
```

The `source-changed` count is the one file edited after its receipt was recorded.
With `--gate`, that fails the exit code, so continuous integration flags a
document that changed without a fresh screening. A content-free record is not
zero-leakage; the residual and the `hash` mode caveat are in
[Boundaries](boundaries.md).

## 8. Wire it into continuous integration

The detector emits SARIF, which GitHub code scanning, Azure DevOps, and reviewdog
render as inline annotations:

```bash
articulate check "**/*.md" --sarif > articulate.sarif
```

The repository ships a GitHub Action and a pre-commit hook. The Action can also
re-verify committed receipts and fail the build on drift. See
[Features](features.md#surfaces) and the `action.yml` in the repository root.

That is the full loop: screen, localize, judge, rewrite, record, and gate. Each
step is local, and each verdict is one a reviewer can reproduce.
