# Handoff Workflow

This is the project pattern for ending and restarting work across chat sessions.

## Why

Chat context is temporary. A short handoff file keeps next-session startup fast and accurate.

## End-Of-Day Command

Run:

```bash
powershell -ExecutionPolicy Bypass -File scripts/eod_handoff.ps1
```

Optional notes:

```bash
powershell -ExecutionPolicy Bypass -File scripts/eod_handoff.ps1 -Notes "What changed, what is blocked, what is next"
```

This writes:

- docs/SESSION_HANDOFF.md

## Next-Day Restart

1. Open docs/SESSION_HANDOFF.md first.
2. Open docs/PROJECT_CONTEXT.md second.
3. Continue from the Next Priorities section.
4. Run pytest if you need a quick confidence check.

## Pattern

This mirrors a common engineering pattern:

- runbook + handoff note
- short operational state snapshot
- clear next actions

It is intentionally lightweight and works well for solo/small teams.
