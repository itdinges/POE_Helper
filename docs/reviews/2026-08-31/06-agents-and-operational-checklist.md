# Agents, operational risks, and review checklist

## Agents that would help this repo

| Agent | Job | Why it matters |
| --- | --- | --- |
| Loot-filter grammar agent | review generated filter text against POE2 semantics | highest product risk; the repo currently has invalid output patterns |
| Economy-math agent | validate conversion, ROI, and recommendation logic | recommendation logic is a live example of plausible-looking but weak math |
| Docs-vs-code drift agent | diff roadmap and project context against CLI reality | docs are ahead of the code and can mislead future work |
| Snapshot-contract agent | require fixture and parser assertions for market types | default catalog and payload shape drift are real risks |
| Bugbot | diff-based bug hunting on branch changes | already caught the two high-severity review issues |
| Security review | dependency and local-file safety | important as the project grows and future auth surfaces appear |
| Coverage/test-gap agent | prefer behavior-driven tests over broad coverage claims | current coverage can stay high while the product is still wrong |
| Domain glossary agent | force terminology definitions for new in-game concepts | helps keep scope aligned and equipment out of default utility work |
| Handoff agent | update project context and end-of-day handoff | helps future chats stay grounded in current reality |

## Operational and reliability warnings

- fetch failures should not abort the whole all-run on the first bad type
- there should be a saved-snapshot offline flow
- repeated fetches need retry/backoff and a proper user-agent policy
- SQLite second-level uniqueness is vulnerable to same-second collisions
- pydantic is in the requirements but the repo mostly uses dataclasses; contract expectations are unclear
- league default should be config-driven instead of hard-coded
- no CLI smoke tests are yet in place despite the stated strategy

## Review checklist for future work

Before calling a feature done, confirm:

- the generated output matches valid POE2 filter grammar
- the ranking metric is not constant under realistic inputs
- the CLI path is actually executable, not just present in a module
- saved snapshots can be used without a live network fetch
- the change is documented in the relevant project context or roadmap files
- tests fail when the old bug is reintroduced

## Closing note

The repo does not need more generic feature work yet. It needs tighter product truth, valid filter grammar, a real ranking metric, and a smaller set of reviewed commands that can be trusted.
