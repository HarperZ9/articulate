# Structure rules

The line checker reads one line at a time. A reply can pass it and still read as a row of short flat statements, three of them opening on one word, with each paragraph announced by its first sentence. The structure rules read a paragraph at a time and report those shapes.

They run under the `chat` profile and in the house voice notes. They do not run under `author-voice`, `narrative`, `essay` or the default profile, so deliberate anaphora in a person's own text raises nothing.

```bash
articulate check reply.md --profile chat --gate
```

In an MCP host, pass `profile: "chat"` to `check` or `score`. With no profile the two tools run the default rules, as before.

## Where they came from

On 2026-11-15 a reply passed `check` with a texture score of 0. Its reader then read it back line by line as a list of faults. That reply is `tests/fixtures/structure/specimen_b.txt`, with names and figures changed and every sentence shape kept. The reply the reader accepted afterwards is `counterpart.txt` beside it. The tests hold each finding the reader named, with its span.

## The rules

| Rule | Tier | What it reports | What to do |
| --- | --- | --- | --- |
| `structure-anaphora/run` | HIGH | Three or more sentences in a row open with the same word | Vary the openings or join the sentences |
| `structure-anaphora/pair` | LOW | Two sentences in a row open with the same word | Vary one opening |
| `structure-parallel/skeleton` | HIGH | Three sentences within four share one frame, with only the content words changed | Recast one or merge them |
| `structure-parallel/label` | HIGH | Three sentences within four have the form "X is a Y" | Recast one or merge them |
| `structure-triad/sentences` | HIGH | Exactly three parallel sentences in a row | Say it in one sentence or drop to two |
| `structure-triad/items` | LOW | A list of three short phrases | Keep it when the three are the full set |
| `structure-pin/cue` | HIGH | A paragraph opener of 8 words or fewer with a pointing phrase: "here is", "the following", "each of them", "two things" | Start with the content the sentence points at |
| `structure-pin/label` | MEDIUM | A paragraph opener of 5 words or fewer that is a bare label, as in "The cause is mine." | Fold the label into the sentence that carries the content |
| `structure-parataxis/run` | HIGH | Three or more statements in a row of 12 words or fewer, none opening on a linking word | Join the ones that depend on each other |
| `structure-parataxis/stub` | MEDIUM | A statement of 6 words or fewer with no linking word, in a paragraph of four or more sentences where no sentence opens on a linking word | Attach it to its neighbour |
| `structure-pointer/judge` | HIGH | A sentence that only rates the text before it: "That matters.", "That agrees with ..." | State the fact it rests on |
| `structure-pointer/meta` | HIGH | A sentence that points at another sentence and rates it: "His last sentence is the useful part." | Say what that sentence says |
| `structure-pointer/beat` | MEDIUM | A beat of 6 words or fewer that labels the point before it: "That is the silo." | Cut it or make the point in the sentence itself |
| `structure-landing/handoff` | HIGH | A paragraph's last sentence hands the next step back: "... is up to you.", "... is yours to write." | Say what you need from the reader, or stop a sentence earlier |
| `structure-landing/closer` | MEDIUM | A paragraph of four or more sentences ends on one clause of 12 words or fewer | Join it to the sentence it restates, or cut it |

A finding spans the whole run, across wrapped lines when the run wraps. Under `chat` the HIGH findings gate.

### How a frame is compared

Articulate has no dependencies, so there is no part-of-speech tagger. A sentence is reduced to a token-shape signature. A function word stays as itself, a quoted span becomes `Q`, a number becomes `#`, and every other word becomes its ending class: `s`, `ed`, `ing`, `ly` or a blank. Two signatures of five tokens or fewer match when they are equal once every content word is a blank. Two longer signatures match when they open on the same token, differ in length by two tokens at most, and are 0.8 alike by `difflib.SequenceMatcher`.

"The parser reads the file." and "The lexer splits the tokens." both reduce to `the _ _ the _`.

### The local opener measure

The published `repetitive_openers` flag is a whole-document ratio over content-word openers. It needs twelve of them, and it leaves out function words such as "one". Three sentences in a row that open with "One" leave it False. The published detector is byte-pinned, so the flag stays as it is. Under `chat` the cadence block adds `longest_opener_run` and `repeated_openers_in_a_row`, which count consecutive sentences.

## Across turns

`articulate corpus`, and the `corpus_check` tool, read several documents together. Pass one author's turns as the documents and two more findings appear.

- `corpus/sentence-template`: a sentence ending that several turns share once names, numbers and content words are slots and every possessive is one token. "A reply in his name is his to write or approve" and "The question is yours to answer too" share `is POSS to _`.
- `corpus/ritual`: the same two opening words, or the same skeleton, in the first sentence of enough turns, or in the last.

Both report only. A template needs three documents, or two in a series of three or fewer.

## Measured rates

The counts below come from one run on 2026-11-15. Rates are findings per 1,000 sentences.

| Text | Sentences | HIGH | MEDIUM | Documents with a HIGH finding |
| --- | --- | --- | --- | --- |
| Specimen B, the reply that passed | 24 | 8 | 4 | 1 of 1 |
| The accepted counterpart | 7 | 0 | 0 | 0 of 1 |
| 52 replies by the same session on the same day | 681 | 17 (25.0) | 19 (27.9) | 8 of 52 |
| 18 human texts in `corpus/provenance/human` | 204 | 3 (14.7) | 1 (4.9) | 2 of 18 |
| Running prose from four public-domain books | 3,973 | 38 (9.6) | 34 (8.6) | 4 of 4 |

The four books are Darwin's *Origin of Species*, Faraday's *Chemical History of a Candle*, Russell's *Problems of Philosophy* and Strunk's *Elements of Style*, from Project Gutenberg, about 40,000 words of each with tables, contents lists and example pairs removed.

HIGH findings in the books, by rule: anaphora 12, triad 11, parataxis 8, parallel 5, pin 1, pointer 1, landing 0. Most of the anaphora and triad findings are the device used on purpose, as in Darwin's "He does not allow ... He does not rigidly destroy ... He often begins ...". A writer who wants the device should use a profile that leaves these rules out.

Three findings in the books that a reader would call wrong:

- `structure-pin/cue` on Faraday's "Here is another application of the same principle." He is pointing at apparatus on the bench.
- `structure-parataxis/run` on Jerome's "We made George work, now we had got him. He did not want to work, of course; that goes without saying. He had had a hard time in the City, so he explained." The clauses link inside each sentence.
- `structure-parallel/label` on Faraday's run of metals, "Osmium is the most difficult to fuse ...". The paragraph is a list of facts given as prose.

On the 52 replies, the series check reported 12 templates. Seven are stock phrasing a reader would notice, such as `_ is POSS` ("That click is yours.") in four replies and `on POSS own _` ("waiting on its own CI") in six. Five are ordinary phrasing, such as `before the _ and`.

These rules were tuned on one session's replies and one reader's verdict. The rates will differ on other writers.

## Limits

- The rules skip list items, headings, block quotes and code. Ten of the 52 replies carried a hand-back sentence, and the ones inside list items raised no landing finding.
- Each phrase list is closed, so a paraphrase gets past it.
- Parataxis is read from sentence length and opening words. A paragraph of long unlinked sentences passes.
- Setup and payoff is caught only in the announcer form ("Here is X said plainly.").
- English only.

## Coverage of one house rule set

One author's standing prose rules name 23 patterns. The table says which had a detector before these rules, and which have one now. "Partial" means a closed phrase list or a density measure that catches some forms.

| Pattern | Before | Now |
| --- | --- | --- |
| Antithesis | Detector | Detector |
| Corrective negation | Detector | Detector |
| Paragraph pinning | None | Detector: `structure-pin` |
| Parataxis | None | Detector: `structure-parataxis` |
| Summary beats | Partial: a curated "That is the ..." list | Detector: `structure-pointer` |
| Rhetorical crutches | Partial: reveal, meta and throat-clearing lists | Partial |
| Negative parallelisms | Detector | Detector |
| Negative anaphoras | None | Detector: `structure-anaphora`, any polarity |
| Contrasting pairs | Detector | Detector |
| Rule of three | Partial: single-word triads, report only | Detector: `structure-triad` |
| Em dashes | Detector | Detector |
| Throat-clearing openers | Detector | Detector |
| Landing sentences | Partial: closing phrases such as "in conclusion" | Detector: `structure-landing` |
| Setup and payoff | Partial: reveal phrases | Partial: plus the announcer form |
| Parallel sentence structures in a paragraph | None | Detector: `structure-parallel` |
| Vary sentence length | Partial: a uniform-cadence flag | Partial |
| Stacked noun phrases | None | None |
| Filler intensifiers | Detector | Detector |
| Corporate-register verbs | Partial: "reflect" is flagged only as a trailing participle | Partial |
| Nominalization | Partial: four or more in one line, report only | Partial |
| Hedging qualifiers | Partial: stacked hedges and clusters of three | Partial |
| Write for the spoken voice | None | None |
| Performed enthusiasm | Partial: email and flattery phrases | Partial |

Before: 7 with a detector, 10 partial, 6 with none. Now: 14 with a detector, 7 partial, 2 with none.
