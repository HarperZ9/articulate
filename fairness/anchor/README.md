# Timestamps for the pre-registration

Two RFC 3161 time-stamp tokens from FreeTSA (freetsa.org) sign the SHA-256 of
`fairness/PREREG.md` at two points. Only each digest was sent to the
time-stamping authority.

| Token | PREREG.md as it stood | SHA-256 | Time in the token | Serial |
|:-|:-|:-|:-|:-|
| `PREREG.tsr` | with the confirmatory corpus amendment (commit 5a30364) | `a52026395371cbb9b624715b32e266af43a4e969995b29c4fdc7800f4e96a643` | 2026-09-26 22:33:21 UTC | `0x08810CA9` |
| `PREREG-2.tsr` | with the domain-review extension and the final ruleset fingerprint, before the confirmatory run (commit e247280) | `3f2863ff84d8e00d96b647d629e04095ca17f0086f5d8105111d5606ce586869` | 2026-09-27 03:28:14 UTC | `0x0883D111` |

Both tokens carry the FreeTSA policy `tsa_policy1`.

Files here:

- `PREREG.tsq` and `PREREG-2.tsq`: the requests, each made with
  `openssl ts -query -data fairness/PREREG.md -sha256 -cert -out <name>.tsq`.
- `PREREG.tsr` and `PREREG-2.tsr`: the signed replies.
- `freetsa-cacert.pem` and `freetsa-tsa.crt`: the FreeTSA root and signing
  certificates, fetched from freetsa.org/files/ on 26 September 2026 and fetched
  again for the second token with the same bytes. For an independent check,
  fetch them from freetsa.org yourself and compare.

## Verify

From the repository root, for each token (`PREREG` or `PREREG-2`):

```
openssl ts -verify -in fairness/anchor/PREREG-2.tsr -queryfile fairness/anchor/PREREG-2.tsq \
  -CAfile fairness/anchor/freetsa-cacert.pem -untrusted fairness/anchor/freetsa-tsa.crt
openssl ts -verify -in fairness/anchor/PREREG-2.tsr -data fairness/PREREG.md \
  -CAfile fairness/anchor/freetsa-cacert.pem -untrusted fairness/anchor/freetsa-tsa.crt
```

Each prints `Verification: OK`. The second command checks the file itself, so
it holds only for the version of `fairness/PREREG.md` whose SHA-256 the token
names. The amendment of 27 September 2026 was added after both tokens, so
neither token matches the file as it stands now. Check each against its own
version: write token 1's file with `git show 5a30364:fairness/PREREG.md > PREREG-first.md`
and token 2's with `git show e247280:fairness/PREREG.md > PREREG-second.md`, then
pass it to `-data`. No token covers the amendment of 27 September yet; a
third token over the file with it is still to be taken. To read the time in a
token:

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
