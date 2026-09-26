# Corpus

`python -m articulate.bench` reads this folder. It checks the rules, and says
nothing about who wrote any text here.

- `patterns/` holds texts written to exercise named patterns. `patterns/expect.json`
  lists, per file, the categories each must still raise under the profile named
  there. A rule change that stops matching one fails the benchmark.
- `control/` holds plain public texts that must raise no blocking finding under
  the profiles `expect.json` lists for the control set.

## Provenance

| File | Source | Licence |
|:-|:-|:-|
| `control/declaration-preamble.txt` | US Declaration of Independence (1776), preamble | Public domain |
| `control/gettysburg.txt` | Lincoln, Gettysburg Address (1863) | Public domain |
| `control/lincoln-2nd-inaugural.txt` | Lincoln, second inaugural address (1865), excerpt | Public domain |
| `control/ptacek-tweets.txt` | Posts by Thomas Ptacek on writing | Unknown: no licence note has been found. Kept pending a maintainer decision |
| `patterns/*` | Written for this project | Same licence as the repository |

The control set is small and narrow: historic public-domain prose and one
writer's posts. It includes no learner English, no spoken-register text and no
World Englishes. The fairness harness measures those groups on licensed corpora
that stay outside this repository.
