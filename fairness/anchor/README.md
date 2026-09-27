# Timestamps for the pre-registration

Four RFC 3161 time-stamp tokens from FreeTSA (freetsa.org) sign SHA-256
digests: three of `fairness/PREREG.md` at three points, and one of the
confirmatory receipt after the run. Only each digest was sent to the
time-stamping authority.

| Token | PREREG.md as it stood | SHA-256 | Time in the token | Serial |
|:-|:-|:-|:-|:-|
| `PREREG.tsr` | with the confirmatory corpus amendment (commit 5a30364) | `a52026395371cbb9b624715b32e266af43a4e969995b29c4fdc7800f4e96a643` | 2026-09-26 22:33:21 UTC | `0x08810CA9` |
| `PREREG-2.tsr` | with the domain-review extension and the final ruleset fingerprint, before the confirmatory run (commit e247280) | `3f2863ff84d8e00d96b647d629e04095ca17f0086f5d8105111d5606ce586869` | 2026-09-27 03:28:14 UTC | `0x0883D111` |
| `PREREG-3.tsr` | with the amendment of 27 September 2026, written after the confirmatory run (commit 25bbdec) | `5456cd79debe0b7cc1483f2ac9fada8ebf39e01c2d7a122f33cccbf0c4af975d` | 2026-09-27 11:18:50 UTC | `0x088837AD` |
| `CONFIRM-persuade-2.0.tsr` | not PREREG: the confirmatory receipt `fairness/receipts/sha256-46e1485cd2c98caa-persuade-2.0.json` | `22992435165b85aa04f2096627060d0a5e0ccdb5b8cc9a72af2befd229f1e7a7` | 2026-09-27 11:18:50 UTC | `0x088837AF` |

All four tokens carry the FreeTSA policy `tsa_policy1`.

Files here:

- `PREREG.tsq`, `PREREG-2.tsq` and `PREREG-3.tsq`: the requests, each made with
  `openssl ts -query -data fairness/PREREG.md -sha256 -cert -out <name>.tsq`.
  `CONFIRM-persuade-2.0.tsq` was made the same way with `-data` set to the
  confirmatory receipt.
- `PREREG.tsr`, `PREREG-2.tsr`, `PREREG-3.tsr` and `CONFIRM-persuade-2.0.tsr`:
  the signed replies.
- `freetsa-cacert.pem` and `freetsa-tsa.crt`: the FreeTSA root and signing
  certificates, fetched from freetsa.org/files/ on 26 September 2026 and fetched
  again for the second, third and fourth tokens with the same bytes. For an independent check,
  fetch them from freetsa.org yourself and compare.

## Verify

From the repository root, for each PREREG token (`PREREG`, `PREREG-2` or
`PREREG-3`):

```
openssl ts -verify -in fairness/anchor/PREREG-2.tsr -queryfile fairness/anchor/PREREG-2.tsq \
  -CAfile fairness/anchor/freetsa-cacert.pem -untrusted fairness/anchor/freetsa-tsa.crt
openssl ts -verify -in fairness/anchor/PREREG-2.tsr -data fairness/PREREG.md \
  -CAfile fairness/anchor/freetsa-cacert.pem -untrusted fairness/anchor/freetsa-tsa.crt
```

Each prints `Verification: OK`. The second command checks the file itself, so
it holds only for the version of `fairness/PREREG.md` whose SHA-256 the token
names. The third token matches the file as it stands, with the amendment of
27 September 2026; any later edit breaks that match. Check the first two
against their own versions: write token 1's file with
`git show 5a30364:fairness/PREREG.md > PREREG-first.md` and token 2's with
`git show e247280:fairness/PREREG.md > PREREG-second.md`, then pass it to
`-data`. For the receipt token, use `-in fairness/anchor/CONFIRM-persuade-2.0.tsr`,
`-queryfile fairness/anchor/CONFIRM-persuade-2.0.tsq` and
`-data fairness/receipts/sha256-46e1485cd2c98caa-persuade-2.0.json`. To read the
time in a token:

```
openssl ts -reply -in fairness/anchor/PREREG-2.tsr -text
```

## What it shows

A token shows that a file with its SHA-256 existed by the time it names. It
does not show when any run took place, and it signs only the file's bytes: the
harness code is pinned by git history and by the byte-identity proof the
confirmatory page describes. The pull request was opened on 26 September 2026 at
18:38 UTC, before the confirmatory amendment, so its creation time anchors only
the original gate table.
