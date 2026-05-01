# Security Policy

## Reporting a vulnerability

If you find a security issue — particularly anything that exposes the configured STT API key or could trigger unintended uploads of audio — **do not open a public issue**.

Email the maintainer privately at the address on the GitHub profile, with:
- The vulnerable code path
- A minimal reproduction
- Whether you've already disclosed it elsewhere

I'll acknowledge within 7 days.

## Scope

- Any path that uploads audio outside the configured STT endpoint
- Any path that prints / logs / persists the API key outside `config.env`
- Any keylogger-like behaviour on non-hotkey input

This is a single-file Python script that talks to one HTTP endpoint. The attack surface is small; please respect that and don't waste your time (or mine) on theoretical issues.
