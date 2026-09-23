# Features

Each section names what the feature gives you and how to reach it. For the exact
commands and flags, see the [CLI reference](cli.md). For what a verdict and a
receipt mean, see [Boundaries](boundaries.md).

## The deterministic detector

The core reads prose and flags the tells that make text read as generated, in
three confidence tiers:

- HIGH: banned rhetorical devices (antithesis, corrective negation, the triad,
  negative parallelism, em-dashes) and named register words. These are hits.
- MEDIUM: strong tells of current frontier-model prose, the stock transitions,
  the marketing superlatives, the participial closers, the email and blog tells.
- LOW: advisories that catch a real pattern and also fire on innocent prose, so
  they never block and expand only with `--verbose`.

It also carries keyword-free detection for a parallel-negation contrast pair, and
document-level signals for uniform cadence, repeated sentence openers, passive
density, and adverb density. Every finding carries a line, a column, and a
character span, so an editor can place a squiggle and a receipt can pin the exact
location.

Alongside the pass or fail gate, it emits a graded 0 to 100 texture score that
accumulates weak evidence by density. The score is a signal for grading and for
the benchmark, and it never changes the clean or flagged verdict.

## Register profiles

A profile is a register configuration expressed as data. It sets which detector
tiers block, a list of terms of art the detector never flags, and provenance
fields. The shipped profiles cover procedures, commits, error messages,
changelogs, release notes, API docs, specs, research, proofs, model cards,
readmes, legal text, journalism, social copy, chat, essays, and narrative, plus
the domain profiles below: UI microcopy, code review comments, plain language,
and controlled English.

The gate follows a slop level. `off` blocks nothing, for narrative where authorial
voice governs. `flavored` blocks the HIGH device tier, for docs and research.
`strict` blocks HIGH and MEDIUM, for procedures and essays that must be device
free. A profile resolves from an explicit flag, an in-file `writing-profile:` tag,
or the file path.

## Domain profiles

Some kinds of writing have rules of their own. A domain profile switches on a
rule pack: deterministic rules for that kind of writing, run beside the detector.
Their findings gate, report, and export like any other finding. A rule whose
judgment is a heuristic sits in the LOW tier and reports without blocking. Every
numeric default is an option under `options` in the project config, and the
source of each default is named below. All of these rules read English only.

### `ux-microcopy`: UI strings

One UI string per line. A `button:`, `label:`, or `error:` prefix sets the type,
or a resource key does (`"save_button": "Save"`). Strict gate.

- `ux-length` (MEDIUM): a button over 3 words or 26 characters, a label over 4
  words, an error sentence over 25 words. Button words follow Material Design 3
  ("ideally 1-3 words"), button characters follow Microsoft's Windows button
  guidance (26 characters), and error sentences follow GOV.UK's 25-word split.
  The 4-word label limit is Articulate's own default, with no published number
  behind it.
- `ux-case` (LOW): title case where the project uses sentence case (Material
  Design 3, the Microsoft Style Guide). Apple's guidelines use title-style
  buttons, so `case` takes `sentence`, `title`, or `off`. A proper noun reads like
  title case, so this reports only.
- `ux-vague-error` (LOW): an error with no next step whose text is vague or names
  no cause, after the Nielsen Norman Group error-message guidelines.
- `ux-link-text` (MEDIUM): "click here", or link text such as "here" or "learn
  more", after the W3C tip against "click here" links. WCAG applies the rule
  strictly at level AAA (failure F84 under success criterion 2.4.9); at level A,
  link text may lean on its context.

```
[articulate] strings.txt [ux-microcopy]: 0 high, 4 medium (blocked)  texture 0/100
  L1 [MEDIUM ux-length] button label has 7 words and 34 characters; the limit is 3 words and 26 characters: button: Save And Continue To The Next Step
  L5 [MEDIUM ux-link-text] link text that names no destination; name where the link goes: link: For details, click here.
```

### `code-review`: review comments

Flavored gate, so these report and the banned devices still block.

- `review-condescension`: "just", "simply", "obviously", "clearly" (LOW), and
  stronger markers such as "why didn't you" or "any competent developer" (MEDIUM).
- `review-no-reason` (LOW): a request ("please rename", "can you move", "this
  should be") in a comment that gives no reason anywhere in it.
- `review-absolute` (MEDIUM): absolute language about a person, such as "you
  always", "you never", or "your code is wrong".

These are phrase lists. They miss a paraphrase and cannot read tone.

### `plain-language`: a readability gate

Strict gate.

- `plain-readability` (MEDIUM): the document's Flesch-Kincaid grade is above
  `max_grade` (default 8). The finding names the grade and the reading ease and
  anchors on the hardest sentence.
- `plain-long-sentence` (LOW): a sentence over 25 words (GOV.UK's split).
- `plain-wordy` (LOW): a wordy phrase with a plainer form, such as "in order
  to" for "to". The list is curated for this tool.

Where grade 8 comes from: Microsoft Word's readability help recommends a grade
score of "around 7.0 to 8.0". No US federal rule sets a number. The Plain Writing
Act of 2010 defines plain writing without a score, and the Federal Plain Language
Guidelines argue against a blanket grade. Health guidance aims lower: AHRQ's
health literacy toolkit points to a 4th to 6th grade level for patient
materials, so a health team should set `max_grade` to 6. Below `min_words`
(default 100, Articulate's own floor) the grade is too unstable to gate on, and
the rule stays silent. Syllables are estimated, so the grade can differ from
another tool's by a grade or more, and a low grade shows short words and short
sentences, which is not the same as a reader understanding the text.

### `normative-spec`: RFC 2119 and RFC 8174 keywords

The existing spec register now checks BCP 14 keyword use. RFC 8174 gives the
keywords their special meaning only in all capitals, and asks a document that
uses them to say so in a boilerplate sentence citing BCP 14.

- `bcp14-mixed-case` (HIGH, gates): "MUST not", "SHOULD not", "must NOT",
  "NOT recommended".
- `bcp14-no-boilerplate` (MEDIUM): capital keywords with no citation of BCP 14,
  RFC 2119, or RFC 8174.
- `bcp14-may-not` (MEDIUM): "MAY NOT", which neither RFC defines.
- `bcp14-lowercase` (LOW): a lowercase "must", "shall", or "should" in a document
  that declares BCP 14. Lowercase "may", "required", "recommended", and
  "optional" are left alone as common plain words.
- `bcp14-shall-must` (LOW): both SHALL and MUST in one document.
- `bcp14-old-boilerplate` (LOW): a declaration without the RFC 8174 clause
  "when, and only when, they appear in all capitals".

Quoted keywords, such as those listed in the boilerplate itself, never count as
uses. The rules check keyword form, and they cannot tell whether a requirement is
the right one.

### `controlled-english`: second-language readers and translation

Inspired by controlled-language practice in technical writing. Articulate does
not implement ASD-STE100 or any other controlled-language specification, ships
none of their dictionaries, and makes no conformance claim. Strict gate.

- `controlled-sentence-length`: a sentence over 25 words (MEDIUM), or an
  instruction over 20 words (LOW, because spotting an instruction is a
  heuristic). The two limits follow the published sentence-length rules of
  ASD-STE100 Issue 9 (rules 5.1 and 6.3), and both are options.
- `controlled-multi-instruction` (LOW): two instructions chained in one sentence.
- `controlled-idiom` (LOW): an idiom a translation engine may read word by word,
  with a literal form.
- `controlled-phrasal-verb` (LOW): a phrasal verb with a single-word form, such as
  "find out" to "learn".
- `controlled-vague-pronoun` (LOW): a sentence that opens with "This", "That",
  "These", or "It" and a verb, with no noun.

The idiom and phrasal-verb lists are Articulate's own and are short. A clean
result means these lists found nothing; it cannot certify a text for
translation.

### Sources for the domain defaults

Each page was read on 2026-09-23. A source can change after that date, so
check it before you rely on a default.

- Material Design 3, button guidelines: <https://m3.material.io/components/buttons/guidelines>
- Microsoft, Windows button controls: <https://learn.microsoft.com/en-us/windows/apps/develop/ui/controls/buttons>
- Microsoft Style Guide, capitalization: <https://learn.microsoft.com/en-us/style-guide/capitalization>
- Apple Human Interface Guidelines, buttons: <https://developer.apple.com/design/human-interface-guidelines/buttons>
- Nielsen Norman Group, error-message guidelines: <https://www.nngroup.com/articles/error-message-guidelines/>
- W3C, "Don't use 'click here' as link text": <https://www.w3.org/QA/Tips/noClickHere>
- GOV.UK, clear language: <https://guidance.publishing.service.gov.uk/writing-to-gov-uk-standards/writing-guidelines/clear-language/>
- Microsoft Word, readability statistics: <https://support.microsoft.com/en-us/word/get-your-document-s-readability-and-level-statistics-in-microsoft-word>
- Plain Writing Act of 2010: <https://www.govinfo.gov/content/pkg/PLAW-111publ274/html/PLAW-111publ274.htm>
- AHRQ Health Literacy Universal Precautions Toolkit, Tool 11: <https://www.ahrq.gov/health-literacy/improve/precautions/tool11.html>
- RFC 2119 and RFC 8174: <https://www.rfc-editor.org/rfc/rfc2119.txt>, <https://www.rfc-editor.org/rfc/rfc8174.txt>
- ASD-STE100: <https://www.asd-ste100.org/>

The Flesch-Kincaid and Flesch reading-ease formulas trace to Kincaid, Fishburne,
Rogers, and Chissom (1975), Research Branch Report 8-75. The coefficients here
match the ones Microsoft's readability page reproduces; the original report was
not checked.

## Project config

A project sets its own rules in a `.articulate.json` file. Articulate finds it
by walking up from each checked file's directory, and the nearest file wins.
`--config PATH` names a file, and `--config none` turns discovery off. The format
is JSON because the package supports Python 3.9, and a TOML parser joined the
standard library only in 3.11.

```json
{
  "version": 1,
  "profiles": {"docs/api/**": "api-docs", "blog/*.md": "essay"},
  "terminology": {
    "banned": [{"term": "whitelist", "suggestion": "allowlist",
                "reason": "inclusive language"}],
    "preferred": [{"use": "sign in", "instead_of": ["log in", "login"]}],
    "allowed": ["leverage"]
  },
  "freeze": ["Articulate"],
  "protect": {"quotes": true, "blockquotes": true},
  "options": {"plain-language": {"max_grade": 6}, "ux-microcopy": {"case": "title"}}
}
```

- `profiles` maps a path glob, relative to the config file, to a profile, genre,
  or mode. The first matching glob wins. It ranks below `--profile`, `--mode`, and
  an in-file `writing-profile:` tag, and above inference from the path.
- `terminology` adds project rules to every check. A banned term fires as rule
  `terminology/banned/<term>` (HIGH by default), and a replaced variant fires as
  `terminology/preferred/<preferred form>` (MEDIUM by default). Each entry may set
  its own `severity` and `match_case`, and the finding carries the reason and the
  suggestion. Code spans, URLs, and fenced blocks are skipped. The findings show
  in `check`, SARIF, the LSP server, per-span verdicts, and receipts.
- `allowed` terms join the profile's terms-of-art keep list. They clear the
  vocabulary and register rules; a structural device such as antithesis still
  fires on them.
- `freeze` terms are protected spans and meaning-guard invariants in every
  rewrite and in `articulate compare`.
- `protect` switches the two configurable protected kinds.
- `options` tunes a domain rule pack by name (`ux-microcopy`, `plain-language`,
  `controlled-english`). An unknown pack, option, or value is an error.

A malformed file stops the command with the file name and the reason: an unknown
key, a bad type, an unknown profile, or a term that is both banned and allowed.
It is never ignored in silence. The LSP server reports a broken config as a
diagnostic and checks the document without it. `articulate config PATH` prints
which config and profile apply to a file.

A receipt made under a config embeds the terminology and options with their
hash, so anyone can replay it with no access to the project. An edited rule set
reads `Unverifiable`, and a consistently re-hashed edit that changes the findings
reads `Drift`.

## Writing modes

A mode crosses a domain register with an articulation need, what the prose does to
the reader: explain, persuade, instruct, narrate, argue, or prove. A mode is a
base profile plus a small delta: terms of art to keep, categories to block even
under a lenient base, and editor guidance. Run `articulate modes` for the list.

A mode tunes style within the plain-writing standard. It may tighten the gate and
add terms of art. It may not re-enable a banned device on prose, with the single
exception of literary narrative, where nothing gates.

## The genre axis

Narrative and expressive prose read by their own convention, so a scanner tuned
for an essay misreads a novel. The genre axis adds `literary-fiction`,
`genre-fiction`, `ya-fiction`, `memoir`, `screenplay`, and `poetry`. Under a
fiction genre:

- Quoted speech is masked out of the device passes, so a character's line is
  never scored as the author's own prose.
- The craft devices report without blocking, because voice governs.
- A report-only lexicon flags generation artifacts, such as the somatic cliche or
  the "could not help but" reflexive. It never gates.

Screenplay classifies Fountain roles first, so only action lines face the device
gate and dialogue keeps the character's voice. Poetry reads by the line, and the
craft-device categories drop from its report, because they name legitimate
technique in verse.

## Science and mathematical writing

`academic/prove` and `science-writing/explain` target hard technical exposition:
stating the idea before the formalism, keeping a roadmap, defining each symbol
once. On a `.tex` file the editor masks every math span before a rewrite and
splices it back byte for byte, so a formula is never altered. The proof mode does
not rewrite by default, because a wrong change to a quantifier order or an
inequality direction changes a theorem; it routes to the judge, and the fix loop
is opt-in.

The boundary here is fixed and load-bearing: a clean gate or a passing receipt
means the prose was screened. It says nothing about whether the theorem is true.
A clear proof can still be false, and this tool never checks the mathematics.

## The editor layer

The editor adds the two things a detector cannot do:

- `judge` reads the judgment-level failures a regex cannot see: a fluent paragraph
  with no fact a reader could restate, vague abstraction, hedging with no
  committed position, a weak verb carrying the meaning. It reports.
- `fix` rewrites to a plain, skilled standard, preserving every number, name,
  citation, term of art, and code span, then re-runs the detector until clean.
- `polish` runs a monotonic loop that accepts a pass only when the gate stays
  clean and no quality score drops, so a rewrite never regresses.

The document is treated strictly as data. A trust boundary is appended to every
model call, so a directive embedded in the text (a line that says to ignore the
standard or to reply approved) is edited as content and never obeyed. The rewrite
optimizes writing quality, and it never tunes prose toward a lower detector score.

## The meaning guard

A rewrite that reads better and says something different is a defect. The meaning
guard compares a rewrite with its original and reports each surface invariant as
kept, dropped, added, or changed, with its line and column. It reads:

- numbers with their units, percentages, dates, times, and versions. They are
  normalized, so "10 ms" matches "10ms", "50%" matches "50 percent", "three"
  matches "3", and "May 5, 2026" matches "2026-05-05".
- negations: not, no, never, none, nothing, nobody, nowhere, cannot, n't, without,
  neither, and nor.
- modal strength in three classes: required (must, shall, required, have to),
  recommended (should, recommended, ought to), and optional (may, might, can,
  could, optional). An all-capitals BCP 14 keyword is its own value, so MUST to
  must counts as a change.
- scope words that bound a claim: only, unless, except, at least, at most, up to
  a number, always, and exactly.
- named entities, approximated as capitalized words that do not open a sentence,
  plus acronyms.
- URLs and emails, inline and fenced code, math spans, citations (`[1]`, `[@key]`,
  `(Author, 2020)`, `Author et al.`, a DOI, an arXiv id, `\cite{}`), quoted
  strings, and project freeze terms.

`fix` and `polish` run every model rewrite through the guard. A rewrite that
drops, adds, or changes an invariant is refused, the previous text is kept, and
the output names the invariant that blocked it. `--allow-change number,entity`
lets the named kinds change, and `--allow-change all` turns the refusal off. Both
are explicit choices, and neither is a default. `articulate compare` runs the same
check on any two files, and the MCP servers expose it as the `compare` tool.

What it does not prove: the invariants are surface proxies. A rewrite can keep
all of them and still change the meaning, for example by moving a negation into
another clause or by swapping two numbers. A reported change can also be harmless.
A `preserved` verdict is a screen. It is no proof that two texts say the same thing.

## Protected spans

Before any model rewrite, the editor replaces each protected span with a numbered
placeholder, so the model never sees the protected text and cannot alter it:

- fenced and inline code,
- math (display math always; inline `$...$` on a `.tex` file, or elsewhere when
  its body carries TeX syntax, so a pair of prices is left alone),
- URLs and emails,
- citations,
- block quotes and quoted material,
- freeze terms.

After the rewrite, every placeholder must come back exactly once and in its
original order. Each span is then spliced back byte for byte. A placeholder that
is missing, duplicated, invented, reordered, or mangled refuses the whole rewrite,
and the previous text is kept. Each placeholder carries a short nonce drawn from
the text's hash, so a document that contains a similar string cannot collide with
one. Block quotes and quoted material can be released with `--unprotect
quotes,blockquotes` for a document whose quotes are the author's own prose; code,
math, links, citations, and freeze terms stay protected.

The guarantee is structural: it holds whatever the model returns. It covers the
spans the patterns recognize. A citation style or a link form the patterns miss
is ordinary prose to the model, and the meaning guard is the second check on it.

## The change report

`--explain` after `--fix` or `--polish` prints what changed and why the tool
touched it, sentence by sentence. Each changed pair shows:

- the sentence before and the sentence after, with its line;
- the detector findings in the original sentence, by rule id and message, which
  are the tells the rewrite was asked to fix;
- any finding still present in the new sentence;
- the meaning-guard rows that fall inside the pair, such as a changed number.

It also lists every candidate the guard refused, with the placeholder or the
invariant that blocked it. `--explain json` gives the same report as JSON. Pairs
come from a sentence alignment, so a merged or split sentence shows up as one
record that spans several sentences. The findings column shows what the detector
saw in the original sentence. It cannot show that the model changed the sentence
for that reason, and a change with no finding came from the judgment-level
instructions. The MCP `fix` tool returns the same per-sentence records.

## Re-derivable receipts

A receipt records a detection result together with the exact text hash and a
fingerprint of the whole ruleset. Anyone replays it: recompute the findings on
the same text under the same ruleset and confirm they match, with no network and
no trust in whoever issued it first. The verdict uses a closed set of three:

- `Match`: same text, same ruleset, identical findings and gate.
- `Drift`: same text and ruleset, but the re-derived findings differ.
- `Unverifiable`: the ruleset moved, the text hash mismatches, or the text is
  below the signal floor. Re-derivation cannot be done, so nothing is asserted.

There is deliberately no trusted or approved value. The receipt certifies
re-derivability, and the issuer's identity is not load-bearing.

## Per-span mixed-authorship

`--spans` scores each paragraph on its own and reports its line range, so a single
generated paragraph in an otherwise clean document is flagged in place, and one
aggregate score cannot smear across the whole file. A per-span receipt records the
per-block verdicts, each with its own text hash.

## Sub-threshold calibration

Below a 30-word floor there are too few tokens to call a text clean human writing,
so a device-clean short text reads `unverifiable` and the receipt abstains rather
than emit a confident verdict on noise. A banned device is unambiguous at any
length, so a short text with a device still reads `flagged`.

## The content-free audit receipt

For a team that must retain a record without keeping the sensitive text, a
content-free receipt drops the matched substring and the exact offsets, and keeps
only which rule fired, its tier and category, and the line. It still replays to
`Match`, and `verify` rejects a mislabeled or a smuggling receipt. The `articulate
audit` command queries a directory of committed receipts locally, and with
`--reverify` it re-checks that each still holds against its source, failing the
gate only when a source drifted or changed since it was screened.

A content-free record is not zero-leakage. Which rules fired and the line remain,
which for a closed-vocabulary rule narrows the flagged word to that rule's small
public candidate set. Read [Boundaries](boundaries.md) before you rely on it.

## Binary inputs fail closed

A binary or an unsupported document (a `.docx`, a PDF, an image) is refused with
an explicit reason, so the tool never returns a spurious clean scan of a lossy
decode. A UTF-8 non-English document is screened, not refused; the patterns are
English literals, so they simply do not fire on it.

## Surfaces

The same detection reaches you through several surfaces:

- CLI: `check`, `score`, `receipt`, `verify`, `audit`, `compare`, and `modes`.
- LSP server: inline squiggles in VS Code, JetBrains through LSP4IJ, and Neovim.
  It is standard-library only, with no dependency.
- SARIF: `check --sarif` for GitHub code scanning, Azure DevOps, and reviewdog.
- MCP server: the detector, the meaning guard, and the editor as tools for an
  agent.
- GitHub Action and a pre-commit hook, wired to gate a change and to re-verify
  committed receipts.
- A VS Code client in `editors/vscode/` and a JetBrains note in
  `editors/jetbrains/`.

## The benchmark

Quality is measured, not asserted. `articulate.bench` runs the detector over a
labeled corpus and reports recall on the AI-authored samples, specificity on the
human-authored samples, and a count of regressions. The exit code is the number
of misclassified files, so a checker can gate on it.

The same run checks the domain rule packs against `corpus/domains/`: each sample
names its profile and the exact set of pack rules it must produce, and a clean
sample must produce none and pass its gate. The samples are short and written for
the purpose, so this is a regression check. It measures nothing about recall or
precision on real documents.
