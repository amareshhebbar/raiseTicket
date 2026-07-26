# Security

## Scope

`data/test_manifest.json` defines shell commands IssueLoop runs. That
file is trusted input, same as a CI config — it is not sandboxed,
allowlisted, or reviewed before execution. Don't add a manifest entry
for a repo whose test suite you haven't looked at.

`issueloop serve` binds to `127.0.0.1` with no authentication. It is a
local integration point, not a hosted API. Don't expose it to the
network without putting your own auth in front of it.

`notify.webhook` receives error payloads (context, exception message,
traceback) over plain HTTP POST. Use HTTPS endpoints; the payload is
not signed.

## Reporting a vulnerability

GitHub Security tab → Report a vulnerability. Not a public issue.
Include what you found, how to reproduce it, what it lets an attacker
do. Response within 5 business days.

## Supported versions

| Version | Supported |
|---|---|
| latest `main` | yes |
| older | no |

Pre-1.0, no backports — update to `main`.

## Out of scope

- Vulnerabilities in repos you point IssueLoop at
- Vulnerabilities from a `test_manifest.json` you wrote yourself
- Supabase/ollama/Anthropic/OpenAI vulnerabilities — report to those
  projects directly