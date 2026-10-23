# Completion ledger

This page says what "feature complete" means for Articulate, one criterion at a
time, and where each one stands. Every criterion has a check that can fail. A
status changes only when someone runs that check and records the result here.

Articulate finds and edits prose for quality. A detector score is never a target
to optimise, and Articulate is not a tool for getting past AI detectors. Any
criterion that would reward a lower detector score is out of scope by
definition.

Measured on 22 October 2026 against `main` at 0.12.1, with the Markdown fix from
pull request 43 applied. Pull request 43 merged as `1b3f8fd`, after `main` moved to 0.13.0. The machine was Windows 11 with Python 3.12, and a
local Ollama model, `qwen3:8b`, served the model backend.

## Status counts

| Status | Count |
| --- | --- |
| PASS | 43 |
| PARTIAL | 13 |
| FAIL | 18 |
| NOT BUILT | 9 |
| Total | 83 |

PASS means the check ran and held. PARTIAL means it holds in part, and the row
names the missing part. FAIL means the check ran and broke. NOT BUILT means
nothing exists to check yet.

## 1. Command line

| ID | Criterion | Check that can fail | Status | Evidence |
| --- | --- | --- | --- | --- |
| C1 | `check` reports each finding with line, column and rule id, and `--gate` exits 1 on a blocked file | Run `check --gate` on a file with an em-dash in prose and on a clean file; expect exit 1, then 0 | PASS | Probe file blocked on the prose em-dash; `docs/*.md` gate exit 0 |
| C2 | `score` prints texture, verdict and counts | `score docs/walkthrough.md` prints all three | PASS | `verdict clean, texture 1/100 (low), gate ok [0H/0M, 738w]` |
| C3 | `receipt` and `verify` replay: Match on the same text, Unverifiable on changed text | Record, verify, edit one line, verify again; expect exit 0, then 2 | PASS | `Match: re-derived 3 findings`; edited copy gave `text does not match the receipt's text hash` |
| C4 | `audit --reverify --gate` reads committed receipts and fails on a break | Content-free receipt in a folder, audit it | PASS | `reverify: {'Match': 1}`, exit 0 |
| C5 | `modes` lists every mode and `check --mode` applies one | `modes` count matches `modes.names()` | PASS | 29 modes listed |
| C6 | `plan` and `submit` guard protected spans and claim features, with `--allow-change` as the named escape | Submit a rewrite that drops a negation; expect a refusal, then acceptance with `--allow-change negation,modal` | PASS | Refused with `negation claim features changed`; accepted with the flag, gate `blocked` to `ok` |
| C7 | `judge` names the problems in a passage that the detector blocks | Judge a passage with three HIGH findings; the assessment must name at least one | FAIL | `qwen3:8b` answered "The prose is strong and clear ... No significant quality failures" on a blocked passage |
| C8 | `fix` with a model keeps dates and numbers verbatim and adds no device | Fix `slop.md`; diff dates; check the result for corrective negation | FAIL | "3 May" became "May 3"; output added "The focus is on process, not features." and the gate still read `ok` |
| C9 | `fix --backend none` applies deterministic edits for the closed-list devices | Fix a passage with "It is crucial to" and "Moreover,"; expect at least one edit | FAIL | Zero edits; `gate_before` and `gate_after` both `blocked` |
| C10 | `polish` improves or keeps the text and never ends worse | Polish `slop.md`; expect fewer blocking findings or the original back with a reason | PARTIAL | Original returned, gate still `blocked`, no reason given |
| C11 | `--version` prints the package version | `articulate --version` exits 0 | FAIL | `unrecognized arguments: --version`, exit 2 |
| C12 | Unknown profile or mode fails closed with the list of known names | `check --profile nosuch` exits 2 and lists profiles | PASS | Exit 2 with the full list |
| C13 | `check --sarif` emits valid SARIF 2.1.0 and `--content-free` removes every substring | Validate against the schema; grep the output for a matched word | PARTIAL | SARIF header and schema URL present; no schema validation run in this pass |
| C14 | `--spans` gives a per-paragraph verdict | `check --spans` on a 43-paragraph doc | PASS | `43 span(s), 0 flagged` |
| C15 | `house`, `corpus`, `titles`, `interview`, `restructure`, `dialogue`, `process`, `disclose`, `desk` each have a test file and a docs entry | Test file per command and a heading in `docs/cli.md` | PASS | Suite 1,681 passed; headings present |

## 2. MCP tools

Measured through the `articulate` MCP server that Claude Code runs from the
`C:/dev/articulate` checkout (0.12.0 code), plus the installed plugin server.

| ID | Criterion | Check that can fail | Status | Evidence |
| --- | --- | --- | --- | --- |
| M1 | `check` returns span records and no Markdown false positives | Send a table and a proper name | PARTIAL | Running server (0.12.0) still reports the table delimiter row and "Transformative"; fixed in source by pull request 43, live after release and restart |
| M2 | `score` returns texture, hard hits and rates | Call on a short passage | PASS | `hard_hits: 3` and rates returned |
| M3 | `fix` returns a rewrite or a host plan | Call with `backend none` | PARTIAL | Returns, but makes no deterministic edit (same gap as C9) |
| M4 | `polish` returns a rewrite or a host plan | Call with `backend none` | PARTIAL | Returns the text unchanged with `quality_met: false` |
| M5 | `judge` returns a host plan when no backend is set | Call with no backend | PASS | `status: host_edit_required` with copyeditor instructions |
| M6 | `edit_plan` masks protected spans and returns a signed plan id | Call on text with numbers | PASS | `14` and `3` listed as protected spans |
| M7 | `edit_submit` refuses a rewrite that changes a claim feature and returns a receipt | Submit a rewrite that drops a modal | PASS | Refused with `modal claim features changed`, receipt returned |
| M8 | `voice_compare` places a draft against the author's saved voice | Call with the author's profile name | FAIL | `no voice profile named 'author' in your local voice store` |
| M9 | `house_transform` makes closed-list edits with a receipt | Send model output that opens with "Great question!" | PASS | Opener removed, `house/2` receipt with fingerprint |
| M10 | `interview` asks author-only questions at their lines | Call on a short argued paragraph | PASS | Two questions with line ranges |
| M11 | `corpus_check` finds shared titles, phrases and constructions across documents | Two documents with one title formula | PASS | Title formula, shared n-gram and shared constructions found. The n-gram excerpt runs across a sentence boundary |
| M12 | `dialogue_check` flags epigram lines and scores voice distinctness | Four lines, one epigram | PASS | One `epigram-definition` with attribution intervals |
| M13 | `title_workshop` groups formulas and asks one question per repeated title | Three titles, two sharing a formula | PASS | Two families, two questions, no invented suggestions |
| M14 | The installed Claude Code plugin serves the current version and every tool above | `articulate_status` version equals PyPI | FAIL | Plugin reports `0.5.1` and exposes 7 tools |
| M15 | The FastMCP surface works with the fastmcp that the `[mcp]` extra installs | Install `[mcp]`, run `tests/test_tool_annotations.py` | FAIL | fastmcp 4.1.3 installs and the test fails with `KeyError: 'readOnlyHint'` |

## 3. Voice learning

| ID | Criterion | Check that can fail | Status | Evidence |
| --- | --- | --- | --- | --- |
| V1 | `voice learn`, `show`, `compare`, `apply`, `export`, `import` and `delete` work from the command line | Learn from three samples, compare a draft, delete | PASS | Learned `probe`, compared, `Deleted vstore\probe.json` |
| V2 | The CLI on the author's PATH has the `voice` command | `articulate voice --help` on PATH | FAIL | PATH CLI is 0.5.1, which has no `voice` command |
| V3 | The author has a saved voice profile on this machine | `articulate voice list` shows one | NOT BUILT | `No voice profiles stored.` The author chooses the samples; the store is `%LOCALAPPDATA%\articulate\voice` |
| V4 | Every reported range is possible for its measure | Rates per 1,000 words never go below 0 | FAIL | `concession_per_1k ... your range -0.134 to 1.474` |
| V5 | `voice_apply_plan` runs only when the user says the draft is theirs | Call with `authored_by_user` false | PASS | Guard covered by `tests/test_voice_boundaries.py` |

## 4. Profiles and modes

| ID | Criterion | Check that can fail | Status | Evidence |
| --- | --- | --- | --- | --- |
| P1 | 24 register profiles and 5 domain profiles load | `check --profile nosuch` lists them | PASS | 24 and 5 listed |
| P2 | Profiles infer from the path and from a `writing-profile:` tag | `tests/test_genres.py`, `tests/test_project.py` | PASS | In the passing suite |
| P3 | Project config `.articulate.json` layers rules and terminology | `articulate config` on a folder | PASS | Covered by `tests/test_project.py` |
| P4 | Profiles and word lists live outside the code, in data an organisation can edit | Load a profile from a TOML or JSON file outside the package | PARTIAL | Project config adds rules; the base profiles stay in Python inside the pinned detector closure |

## 5. False positives by genre

Human texts in `corpus/provenance` (public-domain, in the repository), gate
under the default profile and under the matching mode. Intervals are Wilson 95%.

| Genre | n | Blocked, default | Blocked, matched mode |
| --- | --- | --- | --- |
| essay | 3 | 2 (0.21 to 0.94) | 3 under `persuasive-essay/argue` |
| fiction | 9 | 6 (0.35 to 0.88) | 0 under `literary-fiction/narrate` |
| science | 6 | 4 (0.30 to 0.90) | 4 under `science-writing/explain` |
| speech | 3 | 0 (0.00 to 0.56) | 0 under `persuasive-essay/persuade` |

The HIGH findings on these texts were em-dash 9, filler intensifier 6,
antithesis 6 and corrective negation 1. Older human prose uses the em-dash
freely, so the default profile blocks it.

| ID | Criterion | Check that can fail | Status | Evidence |
| --- | --- | --- | --- | --- |
| F1 | Per-genre human flag and block rates published with intervals | `corpus/provenance/results.json` has `by_genre` with intervals | PARTIAL | Published for flags; n is 3 to 9 per genre in the repository, too small to set a target |
| F2 | Each genre has a target block rate on human text, and the matched mode meets it | Target in the repository, checked in CI | NOT BUILT | No targets exist |
| F3 | The learner-English fairness check passes its pre-registered gate | Rerun the PERSUADE 2.0 arm on the current ruleset | FAIL | Last recorded run (27 September) failed G1, G2 and G4; no rerun since (moderate confidence, from the release record) |
| F4 | Every finding states that it is a style finding and never evidence of who wrote the text | Tool descriptions and `does_not_prove` fields | PASS | Present on every MCP tool and report |

## 6. Markdown structure

| ID | Criterion | Check that can fail | Status | Evidence |
| --- | --- | --- | --- | --- |
| K1 | A table delimiter row is never an em-dash | `tests/test_markdown_structure.py` | PASS | Fixed in pull request 43; 5,123 separator findings gone across 3,000 files, none added |
| K2 | An em-dash or `---` inside a table cell still fires | Same file | PASS | Cell em-dash and cell `---` still HIGH |
| K3 | Indented code outside a list is not prose; list continuations still are | Same file | PASS | Fixed in pull request 43 |
| K4 | YAML and TOML front matter are not prose | Same file | PASS | YAML already skipped; TOML fixed in pull request 43 |
| K5 | Fenced code, tilde fences, fences in lists and double-backtick spans are not prose | Probe file | PASS | No findings |
| K6 | URLs and autolinks are not prose | Probe file | PASS | No findings on `--` or an em-dash inside a URL |
| K7 | A register word inside a capitalised name is not flagged; a heading still is | Same test file | PASS | "Transformative AI Fund" and "Robust Intelligence" clean; Title Case heading still flagged |
| K8 | A name at the start of a sentence is not flagged | "Robust Intelligence builds models." | PARTIAL | Still flagged; a capital at sentence start is no evidence of a name, so the mask leaves it |
| K9 | `---` inside inline `$...$` math is not an em-dash | `Let $a---b$ be the gap.` | FAIL | HIGH em-dash |
| K10 | Block quotes follow one stated rule | A product decision recorded in `docs/features.md` | NOT BUILT | Block quotes are checked today; a quote can be a cited source or the author's own callout |
| K11 | The fix reaches every surface | CLI, per-paragraph view, receipts, MCP, edit hook, editor gate, house notes | PASS | All covered in `tests/test_markdown_structure.py`; the corpus series check still calls the detector directly |

## 7. Packaging and install

| ID | Criterion | Check that can fail | Status | Evidence |
| --- | --- | --- | --- | --- |
| G1 | PyPI latest equals the repository version | PyPI JSON `info.version` | FAIL | PyPI had 0.12.0 at the end of this pass; the 0.12.1 publish failed at `native-build`, and the 0.13.0 publish was still queued |
| G2 | A clean venv install resolves every console script | `publish.yml` script check, then a local clean venv | PARTIAL | The workflow step exists and passed for 0.12.0; no newer release has reached PyPI to check |
| G9 | A bug fix can ship as a patch release | Tag `vX.Y.1` and run `publish.yml` | FAIL | `scripts/native_release_source.py` raises `mature release version must end in .0`, so every fix needs a minor version |
| G3 | The release ruleset check holds the v0.5.2 detector closure | `scripts/check_release_ruleset.py` | PASS | `PASS`, fingerprint `sha256:9f78a7484bb20f84` |
| G4 | Optional extras pin versions that work | `[mcp]` and `[hosted]` installed in CI | FAIL | `[mcp]` says `fastmcp>=3` with no ceiling; CI installs only `[dev]`, so the break is invisible |
| G5 | The author's machine runs the current release everywhere | PATH CLI, plugin and MCP server report one version | FAIL | PATH CLI 0.5.1, plugin 0.5.1, MCP server from a checkout on the `release-0.12.0` branch |
| G6 | Windows native ZIP and MCPB install and run on a clean machine | Install on a machine with no Python | PARTIAL | Built and tested in CI; native client install still unverified, per the README |
| G7 | The VS Code extension is published | Marketplace listing for `harperz9` | NOT BUILT | `editors/vscode` at 0.1.0; no listing found in this pass |
| G8 | The pre-commit hook and GitHub Action work from a clean repository | Install the hook in a scratch repository and commit a blocked file | PARTIAL | Files present; not run in this pass |

## 8. Documentation

| ID | Criterion | Check that can fail | Status | Evidence |
| --- | --- | --- | --- | --- |
| D1 | Every shipped doc passes Articulate's own gate | CI `articulate-self-check` | PASS | Exit 0 locally and in CI |
| D2 | `docs/cli.md` covers every subcommand | Compare `articulate --help` with the headings | PASS | All 22 subcommands covered |
| D3 | Every public description makes the same style-not-authorship claim | Grep public files for "AI tells" and "AI-tell detection" | FAIL | `.pre-commit-hooks.yaml` says "Flag AI and prose tells"; the PATH CLI help says "AI-tell detection" |
| D4 | The hero image matches the current tagline | Compare image text with the README | FAIL | The CHANGELOG for 0.12.0 records the stale tagline in the pixels |
| D5 | A completion ledger exists and stays current | This file, updated in the same change as a status move | PASS | This page |

## 9. Enterprise roadmap

From the team audit layer scope, phases 0 to 4, plus the nine v1 items from the
September roadmap.

| ID | Criterion | Check that can fail | Status | Evidence |
| --- | --- | --- | --- | --- |
| E1 | Content-free receipts (drop or hash) verify as Match | `receipt --redact drop`, then `verify` | PASS | Audit run read `Match` |
| E2 | `audit` queries committed receipts with no server | `audit --reverify --gate` | PASS | See C4 |
| E3 | Receipts carry a reviewer and a timestamp outside the verified core | `receipt --reviewer` | PASS | `tests/test_audit.py` |
| E4 | The GitHub Action re-verifies committed receipts | `action.yml` run in a scratch repository | PARTIAL | Present; not run in this pass |
| E5 | Optional tamper-evidence signing, `[sign]` extra | `pip install articulate-writing[sign]` | NOT BUILT | Deferred until a buyer asks |
| E6 | Self-hosted audit store with SSO, RBAC and retention | Any deployable artifact | NOT BUILT | Gated on a paying signal |
| E7 | Hosted dashboard | Any deployable artifact | NOT BUILT | Gated on tiers A and B |
| E8 | Design partners resolve the willingness-to-pay null | A named partner on record | NOT BUILT | Author's call |
| E9 | LSP server, SARIF and local-model backend | `tests/test_lsp.py`, SARIF output, `--backend ollama` | PASS | Suite passes; Ollama served `qwen3:8b` |
| E10 | ReDoS audit | `tests/test_redos.py` | PASS | In the passing suite |
| E11 | Prompt-injection boundary in the editor | `tests/test_injection.py` | PASS | In the passing suite |
| E12 | Measured quality lift of the editor over the raw draft | Pre-registered blind panel result | NOT BUILT | Plan written 28 September; no run approved |

## 10. Test suite

| ID | Criterion | Check that can fail | Status | Evidence |
| --- | --- | --- | --- | --- |
| T1 | The full suite passes on CI for Python 3.9 to 3.12 on Linux, Windows and macOS | CI on pull request 43 | PASS | All jobs green on pull request 43 |
| T2 | The full suite passes locally with every extra installed | `pip install -e .[dev,mcp,hosted]`, then `pytest` | FAIL | 1,681 passed, 6 failed, all in the fastmcp and hosted tests (see G4) |
| T3 | Timing tests hold on a loaded machine | `test_house_latency`, `test_native_process` | PARTIAL | Failed in one local run of two |

## Release note

Pull request 43 fixed K1, K3, K4 and K7 and merged to `main` as `1b3f8fd`. It
carries no version change; its CHANGELOG entry sits under Unreleased. The
v0.13.0 tag points at `8b9e3e3`, one merge earlier, so 0.13.0 does not carry
the fix. The release workflow accepts only versions that end in `.0`, so the
fix reaches PyPI with 0.14.0 at the earliest. Until then, M1 stays as measured.

## Wave plan

Each package is about one agent run. A package owns its files; two packages in
the same wave never touch the same file. Every package starts with a failing
test, keeps the detector closure byte-identical (`scripts/check_release_ruleset.py`
must pass), and ends with the full suite and the self-check green.

### Wave 1, parallel

**W1-A Version and install hygiene.** Fixes C11, G5, M14, V2.
Owns `src/articulate/cli.py` (the `--version` flag only) and a new
`scripts/sync_local_install.py`.
Entry: `articulate --version` exits 2.
Exit: `--version` prints the package version; the script reinstalls the PATH
CLI, rebuilds the plugin and repoints the MCP server, then prints one version
for all three.

**W1-B Extras that install cleanly.** Fixes G4, M15, T2.
Owns `pyproject.toml` (extras only), `.github/workflows/ci.yml`,
`src/articulate/mcp_server.py` (annotation code only), `tests/test_tool_annotations.py`.
Entry: `[mcp]` with fastmcp 4 fails the annotation test.
Exit: a ceiling or a fastmcp 4 port, and a CI job that installs `[mcp]` and `[hosted]`.

**W1-C Voice range fix.** Fixes V4.
Owns `src/articulate/voice_features.py`, `src/articulate/voice_text.py`, `tests/test_voice.py`.
Entry: a rate range below 0 on three samples.
Exit: ranges clamp to what the measure allows, with a test.

**W1-D Claim consistency.** Fixes D3.
Owns `.pre-commit-hooks.yaml`, `action.yml` description text, `editors/vscode/package.json` description.
Waits for any open README or PyPI text PR to close, and does not edit `README.md`.
Exit: a grep for "AI tells" and "AI-tell detection" across public files returns nothing.

**W1-E Release path for fixes.** Fixes G1, G9. Needs the author's decision first:
either the native build accepts patch versions, or the Python release publishes
without the native build when the version is a patch.
Owns `scripts/native_release_source.py`, `.github/workflows/publish.yml`, `tests/test_native_release.py`.
Waits for pull request 44 to merge, since that pull request owns the version strings.
Entry: a `v0.13.1` dry run fails `qualify`.
Exit: a patch tag reaches PyPI, checked from a clean venv.

### Wave 2, parallel, after wave 1 merges

**W2-A Deterministic transform for backend none.** Fixes C9, M3.
Owns `src/articulate/editing.py`, `src/articulate/house_edits.py` (shared closed list), a new `tests/test_fix_none.py`.
Entry: `fix --backend none` makes zero edits on "It is crucial to" and "Moreover,".
Exit: closed-list edits applied, each guarded by the meaning check, each listed in the receipt.

**W2-B Model edit acceptance.** Fixes C8, C10.
Owns `src/articulate/meaning_guard.py` (date-format and device-introduction checks), `src/articulate/editor.py` (accept logic only), `tests/test_meaning_guard.py`.
Entry: the `slop.md` fix turns "3 May" into "May 3" and adds a corrective negation, and the gate reads `ok`.
Exit: such a rewrite is refused with a reason; polish returns a reason when it keeps the original.

**W2-C Judge floor.** Fixes C7.
Owns `src/articulate/prompts.py` (judge prompt), `src/articulate/host_edit.py` (judge result check), `tests/test_editing.py`.
Entry: a judge result calls a blocked passage clean.
Exit: a judge result that names none of the blocking findings is marked `quality_status: unreliable`, and the CLI says so.

**W2-D Markdown follow-ups.** Fixes K8, K9, K10.
Owns `src/articulate/mdstructure.py`, `tests/test_markdown_structure.py`, `docs/features.md` (one section).
Entry: `$a---b$` blocks; the block-quote rule is undocumented.
Exit: inline math masked in `.md`; the block-quote rule follows the author's decision and is written down.

### Wave 3, sequential

**W3-A Genre corpus and targets.** Fixes F1, F2.
Owns `corpus/provenance/human/` additions, `scripts/provenance_eval.py`, `corpus/provenance/results.json`.
Entry: n of 3 to 9 per genre.
Exit: at least 30 public-domain or openly licensed human texts per genre, block rates per genre under the matched mode, and a target per genre that the author approves. The target is a ceiling on human block rate and never a detector score.

**W3-B Fairness rerun.** Fixes F3. Runs after W3-A on the same ruleset.
Owns `scripts/` run files and a dated result file. Needs a new pre-registration, because PERSUADE can no longer confirm a changed ruleset.

**W3-C Author voice profile.** Fixes V3, M8. Needs the author: the author picks the samples, and they stay on this machine.
Owns nothing in the repository.
Exit: `voice list` shows the profile and `voice_compare` returns placements.

### Later, gated on the author

E5 to E8 and E12 each wait on a decision or a paying signal named in their rows.
G7 needs a publisher account action by the author.

## Top gaps

1. The editor does not yet do the job the detector points at. `fix --backend none`
   edits nothing, a model fix can change a date and add a banned device while the
   gate reads `ok`, and the judge can call a blocked passage strong (C7 to C10).
2. The author's own machine runs three different versions, and the PATH CLI and
   plugin are 0.5.1 (G5, M14, V2).
3. Human false positives by genre rest on 3 to 9 texts each, with no targets, and
   the default profile blocks most older human prose on its em-dashes (F1, F2).
4. The `[mcp]` extra installs a fastmcp that breaks the FastMCP surface, and CI
   does not test it (G4, M15).
5. No author voice profile exists, so `voice_compare` cannot run (V3, M8).
6. A fix cannot ship as a patch: the native build accepts only `.0` versions, the
   0.12.1 publish failed on that rule, and PyPI still serves 0.12.0 (G1, G9).
