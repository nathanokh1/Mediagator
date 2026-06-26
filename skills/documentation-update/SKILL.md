---
name: documentation-update
description: Updates user-facing documentation to match what was actually shipped. Use after Code Reviewer approves a merge, whenever a feature ships, or when someone notices the README or docs are out of date. Covers project README, API docs, user guides, and the @nathanokh/codebase README if anything was promoted. Nobody owns this without this skill — it fills that gap.
---

# Documentation Update

Keeps outward-facing docs current after every ship. Runs after Code Reviewer
approval. Takes 5 minutes; skipping it means docs rot within weeks.

---

## What to update and when

### Always after any merge
- **Project README.md** — does the feature list, usage section, or setup guide
  need updating? Does anything in the README describe the old behavior?
- **memory/forge-changelog.md** — log a USED entry for this skill

### When a new feature ships
- **README.md** — add the feature to the feature list or usage examples
- **API docs** (if the project has them) — add or update any changed endpoints,
  parameters, or response shapes
- **`docs/brief.md`** — mark the v1 scope item as shipped if applicable

### When something is promoted to @nathanokh/codebase
- **codebase README.md exports table** — add the new export with what it does
  and how to import it
- **memory/map/capability-map.md** — add the module under Shared modules

### When a breaking change ships
- **README.md** migration note — what changed and how to update consuming code
- **codebase README.md** — bump the version note and migration steps

---

## What NOT to change

- `docs/plan.md`, `docs/handoff.md`, `docs/review.md` — these are internal
  working docs, not user-facing. Leave them as the build record.
- `memory/` files — those are updated by the roles that own them, not here.
- Do not rewrite the README from scratch — update only what changed.

---

## Steps

1. Read `docs/handoff.md` — what was built or changed?
2. Read the current `README.md` — what is stale or missing?
3. Make targeted edits: update the relevant sections, add nothing unrelated.
4. If a promotion candidate was confirmed, update `CODEBASE.md` exports table.
5. Log to `memory/forge-changelog.md`:
   ```
   YYYY-MM-DD HH:MM | USED | documentation-update | code-reviewer | [project] | post-merge doc sync
   ```

## Escalation
Documentation updates are routine — proceed without approval. Escalate only if
updating the docs reveals that what shipped differs materially from what was planned
(that is a MATERIAL CHANGE, not a doc issue).
