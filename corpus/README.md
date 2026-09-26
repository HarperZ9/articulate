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
| `control/nws-thunderstorms.txt` | National Weather Service, "Understanding Lightning Science", the first two paragraphs on thunderstorm development, retrieved 26 September 2026 from https://www.weather.gov/safety/lightning-science-overview | Public domain: a work of the United States federal government (NOAA/NWS, see https://www.weather.gov/disclaimer). Copied without change |
| `patterns/*` | Written for this project | Same licence as the repository |

The control set is small and narrow: historic public-domain prose and one
passage of present-day United States federal government prose. It includes no learner English, no spoken-register text and no
World Englishes. The fairness harness measures those groups on corpora that stay
outside this repository. The one run so far, the Liang et al. (2023) release,
has no licence file (its README shows an MIT badge), so its texts are used
locally and never committed.
