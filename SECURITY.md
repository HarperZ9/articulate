# Security Policy

## Supported versions

`articulate-writing` is distributed on PyPI and packaged as a local CLI and MCP server.
Security fixes ship in the current release line as a new release. Older lines do not receive backports.

| Version | Supported |
|-|-|
| 0.19.x | Yes |
| < 0.19 | No |

## Reporting a vulnerability

Report suspected vulnerabilities privately through GitHub: open this repository's **Security** tab
and select **Report a vulnerability**, or open
<https://github.com/HarperZ9/articulate/security/advisories/new>.
Keep security reports out of public issues, pull requests, and discussions.

Include:

- the affected version and operating system,
- a concise description of the issue and its impact,
- the minimal input or steps needed to reproduce it.

The maintainer, Zain Dana Harper, acknowledges reports and works on a fix before public disclosure.
Allow a reasonable period to remediate before disclosing.

## Scope and trust model

Articulate analyzes prose locally using deterministic rule packs and emits machine-readable scores
and diagnostics.

- **Local execution by default.** The core CLI and deterministic checks run offline without network
  calls or credential access.
- **MCP surface.** The local MCP server speaks JSON-RPC over stdio, binds no network port, and reads
  only the text or paths passed in tool arguments. Results returned to an MCP client flow to that
  client and its configured provider.
- **Optional hosted or model edges.** If you enable optional hosted endpoints or external model
  integrations, credentials and outbound traffic for those integrations remain your responsibility.
- **What counts as a vulnerability.** Arbitrary code execution triggered by untrusted text or rule
  input, path traversal outside explicitly requested paths, or unintended credential disclosure.
- **What does not count.** False positives or false negatives in stylistic prose scoring are quality
  issues, not security vulnerabilities.

## Good practice

- Keep optional API tokens in environment variables and out of committed files or prompt text.
- Treat untrusted text inputs as data and run automated gates with least-privilege filesystem access.
