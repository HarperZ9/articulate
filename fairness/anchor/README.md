# Timestamp for the pre-registration

`PREREG.tsr` is an RFC 3161 time-stamp token from FreeTSA (freetsa.org). It
signs the SHA-256 of `fairness/PREREG.md` as that file stood when the
confirmatory corpus amendment landed. Only that digest was sent to the
time-stamping authority.

| Field | Value |
|:-|:-|
| File | `fairness/PREREG.md` |
| SHA-256 | `a52026395371cbb9b624715b32e266af43a4e969995b29c4fdc7800f4e96a643` |
| Time in the token | 2026-09-26 22:33:21 UTC |
| Token serial | `0x08810CA9` |
| Authority | FreeTSA, policy `tsa_policy1` |

Files here:

- `PREREG.tsq`: the request, made with
  `openssl ts -query -data fairness/PREREG.md -sha256 -cert -out PREREG.tsq`.
- `PREREG.tsr`: the signed reply.
- `freetsa-cacert.pem` and `freetsa-tsa.crt`: the FreeTSA root and signing
  certificates, fetched from freetsa.org/files/ on 26 September 2026. For an
  independent check, fetch them from freetsa.org yourself and compare.

## Verify

From the repository root:

```
openssl ts -verify -in fairness/anchor/PREREG.tsr -queryfile fairness/anchor/PREREG.tsq \
  -CAfile fairness/anchor/freetsa-cacert.pem -untrusted fairness/anchor/freetsa-tsa.crt
openssl ts -verify -in fairness/anchor/PREREG.tsr -data fairness/PREREG.md \
  -CAfile fairness/anchor/freetsa-cacert.pem -untrusted fairness/anchor/freetsa-tsa.crt
```

Both print `Verification: OK`. The second checks the file itself, so it holds
only while `fairness/PREREG.md` is the anchored version. After a later
amendment, check out the version whose SHA-256 is the one above and pass that
file to `-data`. To read the time in the token:

```
openssl ts -reply -in fairness/anchor/PREREG.tsr -text
```

## What it shows

The token shows that a file with this SHA-256 existed by the time it names. It
does not show when any run took place. The pull request's creation time on
GitHub is a second, weaker anchor.
