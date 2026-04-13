# Security Policy

## Supported versions

OpenWhisper is a single rolling release. Only the latest `main` and the most recent tagged release receive security fixes.

## Reporting a vulnerability

**Please do not open a public GitHub issue for security problems.**

Instead, open a private vulnerability report via GitHub's *Security → Report a vulnerability* tab on this repository. If that isn't available, open a minimal public issue titled "Security: please reach out" with no details and a maintainer will respond with a private contact channel.

When you report, please include:

- A clear description of the issue and the impact you believe it has
- Steps to reproduce (or a proof-of-concept)
- The OpenWhisper version / commit you tested against
- Your Windows version

We'll acknowledge receipt within a few days, keep you posted on progress, and credit you in the fix commit if you'd like.

## Scope

In scope:

- Arbitrary code execution, privilege escalation, or sandbox escape via OpenWhisper
- Leaks of the user's Groq / Anthropic API keys (e.g. out of Credential Manager, into logs, over the network to anywhere other than the intended vendor endpoint)
- Leaks of audio or transcripts to disk / network beyond what the documented settings allow
- Hotkey or clipboard hijacking that OpenWhisper enables unintentionally

Out of scope:

- Vulnerabilities in upstream dependencies (faster-whisper, CTranslate2, Groq, Anthropic, PySide6). Report those upstream; we'll bump our pinned versions.
- Issues requiring an attacker who already has code execution on the user's machine.
- Denial of service from a legitimate user (e.g. pointing OpenWhisper at a broken model). File a normal bug instead.

## What we won't do

- We will not add telemetry, crash reporting, or any "phone home" feature to investigate reports. If we can't reproduce locally, we'll ask for your help.
