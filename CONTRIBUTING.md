# Contributing to `HarperZ9/articulate`

Contributions, bug reports, reproducible benchmarks, and documentation fixes are welcome.
Participation in this repository is governed by [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
Security vulnerabilities must be reported privately through [SECURITY.md](SECURITY.md), never in a
public issue or pull request.

## Licensing and Developer Certificate of Origin (DCO)

This repository is licensed under `MIT` (see [LICENSE](LICENSE)). No Contributor
License Agreement (CLA) is required; contributors retain copyright and license their work under
the repository license.

Sign off every commit with the Developer Certificate of Origin 1.1 (`git commit -s`), adding a
`Signed-off-by: Name <email>` trailer certifying that you have the right to submit the work under
`MIT` (<https://developercertificate.org/>).

If you used an automated coding tool to help draft a change, note that in the pull request
description and verify the diff and tests as your own.

## Workflow

1. Open an issue first for substantial features or architectural changes so scope and interfaces
   stay aligned.
2. Branch from `main` and keep pull requests focused on one logical change.
3. Run the local test suite before opening a pull request:
- `python -m pytest -q`
4. Verify no secrets, private paths, or third-party material with incompatible licenses enter the
   diff.

## Repository Standards

- Keep the core prose detector standard-library only with zero mandatory runtime dependencies.
- Mirror changes under `src/articulate/` into `claude-plugin/src/articulate/` when required by the plugin parity tests.
- Add both positive and negative test cases for every new writing pattern or profile rule.
