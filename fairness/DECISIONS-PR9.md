# Decisions on pull request 9

`fairness/PREREG.md`, the changelog and the fairness pages cite "the pull
request 9 decisions" and "decision 2". This file is that record. An AI coding
agent (Claude) made these decisions on 26 and 27 September 2026 under the
maintainer's written delegation, which asked for a decision or for research
toward the best approach; the maintainer reviews them before merge. Each gives
the rule it applies, the evidence and what would reverse it. Releases already
published are not yanked.

## The principle behind decisions 1 to 3

The blocking tier is for a reader cost that holds in nearly every use of the
pattern. A pattern whose cost depends on register, or that style authorities
accept in some uses, belongs in the report-only tier, where the writer decides.
A report-only note that measures as skewed toward one group and carries no
reliable reader cost belongs in the house pack, which a writer sees only on
request. These grounds were stated before re-measuring. A change made after
reading a corpus is still exploratory on that corpus, so confirmation comes
from a corpus the rules were not tuned on (decision 7).

## 1. The release gate

The gate covers releases that change the ruleset. A package release whose
ruleset fingerprint equals the last published one is not gated, since nothing
the gates measure has changed and blocking it would hold back a security fix
while the same rules stay live. A changed ruleset must pass every gate on every
required receipt. An override for one exact ruleset stays possible, and it is
accepted only when no gate row fails that did not fail under the published
ruleset. That blocks an override from shipping a regression and still lets a
strict improvement ship over a worse live ruleset. Gate definitions and
thresholds do not change.

Reverses if a code change outside the fingerprint can change blocking. Nine
masking and splitting patterns are such a case today; they are recorded as a
known defect and join the fingerprint with the next ruleset.

## 2. "in order to" and "state of the art"

Both leave the blocking tier in every profile. "in order to" becomes a LOW note,
`padded-purpose`: usually "to" does the same work, and usage guides keep it
where it separates a purpose from a complement. "state of the art" becomes a LOW
note, `unanchored-claim`, that fires only when its sentence carries no number,
year or citation: in research writing it names the best published result on a
named benchmark. The other marketing superlatives and the rest of `wordiness`
stay MEDIUM. Evidence on the tuned corpus: under `essay`, 16 of the 19 blocked
abstract windows were blocked by these two phrases. Reverses if the
confirmatory corpus shows the LOW notes skewed toward learner essays; on
PERSUADE 2.0 neither is.

## 3. Two skewed default notes

`curly-quote` moves to the house pack: curly quotation marks are
typographically correct, word processors and phone keyboards insert them, and
the note carries no reader cost. `expletive-opener` splits: "It is important /
worth / crucial / essential / necessary" stays a default LOW note, since it is
metadiscourse that delays the subject; a bare "There is / are / was / were"
moves to the house pack, since existential "there is" is grammatical and often
the clearest phrasing. Neither half ever blocks.

## 4. House notes hidden by default

House notes encode one owner's taste, and the intensifier note skewed 26 of 91
learner texts against 4 of 145 abstract windows. Showing taste by default
presents it as a finding, so `--house-notes` shows them on request.

## 5. `.tex` resolves to `research`

LaTeX source is overwhelmingly academic, and `research` is the profile
calibrated for that register. A writer who wants the strict essay gate on a
`.tex` file names it.

## 6. A second reader for the reader-cost reasons

Open. It must be a person other than the author. It does not block a release;
the pull request checklist keeps it unchecked and the release notes say so.

## 7. A held-out corpus of written learner essays

PERSUADE 2.0 (Crossley et al., CC BY-NC-SA 4.0) became the confirmatory corpus,
pre-registered with its manifest hash and timestamped before the run. ELLIPSE
is a report-only proficiency check. ASAP is dropped: its terms are unverified
and PERSUADE covers the same need. The harness reads each corpus file at run
time and pins its hash; only content-free receipts enter the repository. If the
tool ever becomes a paid product, the non-commercial term is checked first.

## 8. The `clean` key

Deprecated, not dropped. `blocking` counts blocking findings; `clean` keeps its
meaning (no HIGH or MEDIUM finding, whose equal is `findings == "no_findings"`)
on every surface that had it, the MCP `check` tool included, and leaves in
package 0.7.0. `blocking_count`, which carries the same number as `blocking`,
leaves on the same schedule.

## 9. The unlicensed control file, and the outside anchor

`ptacek-tweets.txt` left the tree: posts are their author's copyright and no
licence for redistribution is recorded. Public-domain federal government prose
replaced the control. The PREREG carries RFC 3161 timestamps over its SHA-256.

## Decisions of 27 September 2026, after the confirmatory run

The confirmatory run failed the release gate (G1, G2 and G4). These decisions
change no rule, threshold, corpus, sampling rule or seed.

- **The release record.** A commit after a release updates
  `fairness/published-ruleset.json`; the release commit never does, and the
  check skips the gates only for a record naming an earlier package. Under the
  old wording the release commit's own record passed the ruleset it
  introduced.
- **The override base.** An override compares only with a sound receipt of the
  published ruleset itself. No receipt of another ruleset on PERSUADE 2.0 made
  after this result was read may serve as that base for the current ruleset:
  it would be chosen with the outcome known, and gate rows are coarse enough
  that "fails in both" can hide a wider gap. The next pre-registration names
  any override base before its reading.
- **What PERSUADE 2.0 can still confirm.** Only ruleset
  `sha256:46e1485cd2c98caa`. For any other ruleset its receipt is exploratory.
  A changed ruleset needs a corpus pre-registered for it, with an overlap check
  against every corpus already read, and the release check enforces this.
- **Fixes that change the ruleset wait.** The reviews found defects in quote
  blanking, citation reading, sentence splitting and fingerprint coverage.
  Fixing them now would be tuned on a corpus whose outcome is known, so each is
  recorded as a strict expected-failure test and lands with the next
  pre-registered ruleset. Changes to what the harness writes (unrounded
  p-values, category keys for count-bearing notes, a report-only marker) wait
  as well, so the committed receipts still re-derive from the code.
- **Corpus fragments in an early receipt.** The first draft's receipt,
  committed and pushed on this branch, carried 21 keys that quoted three to
  five words of the Liang et al. texts. A new commit removes those report-only
  rows and marks the receipt as redacted. The branch history is not rewritten.
  The pull request is squash-merged, so no commit that holds the fragments
  reaches `main`. GitHub keeps the pull request's commits reachable after a
  force-push, so rewriting would not remove them from GitHub, and it would break
  the commit ids that the timestamped PREREG text cites. The fragments are
  short, carry no personal data, and come from a public release.
- **The removed control file in history.** `ptacek-tweets.txt` has been in
  `main` since the first commit and in every tag from v0.1.0 to v0.5.0, and the
  build config puts it in each release's source archive. Rewriting `main` would
  break every clone and every tag, and it would not reach archives already
  published. The file stays in history and leaves every release from this one
  on. If its author asks for more, the published archives are the part to act
  on first.
