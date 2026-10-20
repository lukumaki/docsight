# Project Instructions for the CH7465ONE DOCSight Development Track

These instructions apply to work in this DOCSight checkout for the Hungarian ONE Compal CH7465ONE investigation. Keep the DOCSight upstream project documentation intact and distinguish this user-specific development track from official upstream claims.

## Project objective and evidence

- Investigate whether the modem's internal Network Log can be collected safely and correlated with DOCSight's connection and signal monitoring.
- Treat `investigation/PROJECT_LOG.md` as the chronological record and `investigation/ARCHITECTURE.md` as the current verified technical model and design record. Product-facing documentation belongs in the GitHub Wiki; do not add Markdown files under `docs/`.
- Label claims as **Verified**, **User-reported**, **Proposed**, **Assumption**, or **Unresolved** where that distinction matters. Do not promote a proposal or user report to a verified source-code or live-device fact.
- Inspect existing files before editing. Preserve prior phase reports and unrelated DOCSight content. Prefer additive, focused edits.

## Modem and credential safety

- Do not access or authenticate to the live modem unless the user explicitly authorizes that specific activity. Read-only authorization does not permit configuration changes.
- Never change modem settings, enable remote administration, attempt SSH/Telnet, enumerate undocumented function codes, or attempt authentication bypass.
- Do not expose, persist, or include modem passwords, SID/session cookies, tokens, or raw authentication exchanges in logs, fixtures, reports, screenshots, or commits. Redact identifiers and sensitive event payloads in examples.
- Do not create a second administration session. If implementing native-log retrieval, coordinate it through the existing authenticated CH7465 driver session and core modem poll lifecycle.
- Do not infer timestamp timezone, undocumented `t` semantics, event severity, or firmware compatibility without evidence. Preserve original modem values when integration is eventually approved.

## Git and change safety

- Prior explicit user approval is required before **any Git operation that changes repository state or metadata**. This includes staging or unstaging files (`git add`, `git restore --staged`), commits or amendments, pushes, pulls, fetches, merges, branch or tag creation/deletion/switching, rebases, resets, cherry-picks, remote changes, and changes to Git configuration, the index, references, or repository metadata. Treat any unlisted state-changing Git operation the same way. Approval for one operation does not authorize other operations.
- Read-only Git inspection commands (such as `git status`, `git diff`, `git log`, `git show`, `git remote -v`, `git branch -vv`, and `git rev-parse`) may run without additional approval.
- Step 2 remote configuration was completed and verified on 2026-10-20: `origin` is `https://github.com/lukumaki/docsight.git`, `upstream` is `https://github.com/itsDNNS/docsight.git`, and `main` tracks `upstream/main`.
- Do not overwrite, delete, or discard existing work. Include relevant documentation updates in any proposed commit description or file list.
- Before implementation, inspect `git status`, the target source, tests, and applicable project guidance. Preserve the current CH7465 authentication path and existing standard driver behavior.

## Phase documentation workflow

After each completed development phase:

1. Append a dated report to `investigation/PROJECT_LOG.md` with objectives, findings, changes, tests, unresolved issues, and next steps. Keep earlier reports unchanged.
2. Update `investigation/ARCHITECTURE.md` when verified technical findings or design decisions change; mark proposals and unresolved points clearly.
3. Update the project-status section of `README.md` when the objective or current phase status changes, without replacing the upstream README content.
4. Verify that documentation agrees with the actual checkout and test results. State clearly when a test was not run.

For historical phases whose exact completion date or environment record is not available locally, record the documentation date and state that the original date/details were not retained. Do not invent them.
