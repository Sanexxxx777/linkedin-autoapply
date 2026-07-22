# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it by
opening a [GitHub issue](https://github.com/Sanexxxx777/linkedin-autoapply/issues)
or contacting the maintainer directly via the GitHub profile linked in the
[README](README.md#автор).

Please do not include real credentials, tokens, or personal data in a public
issue — describe the vulnerability and, if needed, ask for a private channel
to share sensitive details.

## Scope and Nature of This Project

This repository is a browser-automation bot (Playwright) that scans LinkedIn
job listings. A few things to keep in mind:

- All credentials (Telegram bot token, LLM API keys, VNC password) are read
  from a local `.env` file (see `.env.example`) and are **never** committed to
  version control.
- Authenticated browser state (cookies, `auth_state.json`) and scraped profile
  data are excluded from the repository and should stay local to your machine.
- This bot does not submit job applications automatically — it only scans and
  scores. Automating browsing/scanning of LinkedIn may still violate its Terms
  of Service — see the "⚠️ Риски" section in the [README](README.md) before
  running it.

## Supported Versions

This is a personal/showcase project without formal versioned releases;
security fixes are applied to the `main` branch.
