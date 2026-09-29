# Incidents

Security and operational incidents: anything that exposed a credential or data, or took a deployed
system down. Engineering problems found during development belong in `docs/failure-log.md`.

Format for an entry: date, what happened, how it was detected, impact, what was revoked or rotated,
and what now prevents a repeat (`docs/RUNBOOK.md` §5).

No incidents to date.

Checked on 2026-09-29: `python scripts/check_submission.py` scans the working tree and the full git
history (`git log -p --all`) for key-shaped strings and committed `.env` files, and reported no
findings.
