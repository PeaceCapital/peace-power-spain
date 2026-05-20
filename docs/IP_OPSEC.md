# IP + OpSec Checklist

Use this before sharing the project with banks, funds, consultancies, or potential partners.

## Core Principle

Treat the project as a **trade secret product**, not a public research toy.

What should stay private:
- model logic
- feature engineering choices
- BESS sunset thresholds
- congestion-scoring methodology
- client lists and outreach notes
- model artifacts
- API tokens and data-access details

What can be shown:
- dashboard screenshots
- sanitized demo outputs
- methodology at a high level
- memo language and commercial framing
- sample charts without full formulas or raw source code

## Repo Security

- keep the GitHub repo private
- enable 2FA on GitHub and email
- do not store tokens in notebooks or committed files
- use `.env` or GitHub secrets for credentials
- rotate tokens if they were ever pasted into chat, email, or notebooks
- avoid uploading client names, emails, or private deal notes into the repo

## Demo Discipline

Before any demo:
- remove tokens from notebook cells
- hide raw paths and local machine details
- avoid sharing full notebooks live unless necessary
- prefer the dashboard over raw code
- use synthetic or sanitized data when the live stack is not ready

During any call:
- explain the signal concept, not the exact threshold stack
- show outputs, not the internal weighting logic
- keep the “how” higher level than the “what”

After any demo:
- note exactly what was shown
- note who saw it
- note whether an NDA exists

## Outreach Discipline

Do not send:
- source code
- notebooks
- raw model artifacts
- detailed feature lists
- training data dumps

Do send:
- one-page summary
- dashboard screenshot
- sample output pack
- short demo invitation

Good language:
- “signal engine”
- “market-monitoring stack”
- “storage-aware Iberian power analytics”
- “congestion intelligence”

Avoid language like:
- “secret algo”
- “guaranteed alpha”
- “trading bot”
- “fully automated hedge fund system”

## Device / Personal Security

- keep full-disk encryption enabled on your Mac
- use a password manager
- use unique passwords for GitHub, email, and data providers
- keep backups encrypted
- do not keep sensitive spreadsheets on a public cloud link without access controls
- separate personal and project outreach accounts where possible

## Legal / IP Posture

Default posture:
- protect the system as a trade secret
- use NDAs before deep methodology conversations
- document authorship and dates for important files
- keep a clean record of what you built and when

Patent posture:
- do **not** rush into patenting the whole strategy
- only consider patent counsel if there is a narrow technical invention worth isolating
- remember that patent filings can create publication risk

## Bank / Boutique Sharing Rules

For first contact:
- share only the problem, use case, and dashboard outcome

For second conversation:
- share a tighter methodology summary
- still avoid code and exact threshold logic

For serious diligence:
- use NDA first
- prepare a limited disclosure pack
- watermark exported decks or PDFs when appropriate

## Red Flags

Stop and tighten controls if:
- someone asks for the notebook immediately
- someone asks for raw formulas before any real conversation
- someone wants unrestricted forwarding of your materials
- someone pushes for “just send the code”
- you are about to paste tokens or internal paths into a screen share

## Safe Operating Order

1. Build privately.
2. Demo through the dashboard.
3. Share sanitized outputs.
4. Use NDA before detailed methodology.
5. Keep code and core logic private unless there is a serious commercial reason not to.
