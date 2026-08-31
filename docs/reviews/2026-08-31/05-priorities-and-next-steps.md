# Priority list and next actions

## Must exist before calling the helper useful in-game

1. valid loot-filter emission using Show/Hide and BaseType rules instead of illegal Watch/Class combinations
2. a recommendation metric that is not algebraically constant
3. dry-run mode for managed-filter generation
4. a profile listing command so a non-author can inspect mappings and league-start profiles
5. offline replay from saved snapshots or input JSON
6. one command that connects history -> score -> optional managed filter

## Should exist before expanding scope

7. profile rules in JSON/YAML with schema validation
8. tests that validate actual filter grammar or at least compile/filter syntax assumptions
9. architecture cleanup that splits market logic into adapter and domain layers
10. collapse the fetch-type guidance into one canonical current recommendation
11. fixture-backed tests for each default catalog type, not just Currency-shaped payloads
12. explicit handling when configured names do not match the API

## Intentionally later

- authenticated inventory planning
- desktop or web UI
- scheduled worker mode
- equipment/build search
- advanced market ratio research

## Recommended execution path

### Step 1 — fix the two high-severity bugs

- replace the constant recommendation signal with a real differentiator
- fix filter generation so it emits valid POE2 filter semantics

### Step 2 — close one vertical slice

Pick a single player story, such as:

> fetch yesterday’s currency data, score pricing from history, preview a managed filter, then decide whether to write it

### Step 3 — make the CLI honest

- add dry-run and profile listing
- add offline snapshot replay
- stop presenting recommendation as a true optimizer until the ranking is real

### Step 4 — then do architecture cleanup

- split adapters and domain logic
- move profile definitions to config
- refresh the project context and roadmap so “done” means callable and correct

## Bottom line

The best next move is not broader feature work. It is one correct vertical slice: valid filters, real ranking, dry-run preview, and history-backed scoring from saved snapshots.
