# Review Playbook

Use this before declaring a branch ready.

## Review Agents

### 1. Coverage Agent
Purpose:
- verify behavior with tests and expose weakly tested areas

Checks:
- run pytest with coverage
- inspect missing lines in app modules

Command:
- scripts/review_gate.ps1

Pass expectation:
- tests pass
- coverage report generated and reviewed

### 2. Security Agent
Purpose:
- catch risky code patterns and vulnerable dependencies

Checks:
- static scan over app code
- dependency vulnerability audit

Command:
- scripts/review_gate.ps1
- scripts/review_gate.ps1 -SkipSecurity

Pass expectation:
- no high-risk findings without documented justification

### 3. Architecture Agent
Purpose:
- ensure implementation still matches architecture and ADRs

Checks:
- architecture docs exist and are current
- code changes align with service and contract boundaries

Command:
- scripts/review_gate.ps1
- scripts/review_gate.ps1 -SkipArchitecture

Pass expectation:
- key architecture docs present
- no major boundary violations introduced

## Branch Ready Checklist

1. Run review gate script.
2. Review coverage output for untested logic.
3. Review security findings and exceptions.
4. Update PROJECT_CONTEXT and ROADMAP when behavior changed.
5. Commit only after all required checks pass.

## Notes

- This playbook is intentionally lightweight for a small team.
- Keep exceptions explicit in commit notes when bypassing a check.
