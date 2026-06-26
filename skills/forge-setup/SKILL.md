---
name: forge-setup
description: Sets up the Forge platform in any project, new or existing. Use this at the very start of onboarding Forge into a repo — the agent walks through the checklist, ingests existing docs and rules, seeds memory from them, and leaves the project ready to run without re-reading those files every session. Invoke explicitly ("run forge-setup") or when someone says "add Forge to this project", "set up the agents", or "onboard this repo."
---

# Forge Setup

Gets any project — new or existing — fully onboarded onto Forge in one pass.
Run top to bottom, skipping steps that are already done.

---

## Step 1: Detect project type

Determine whether this is:
- **New**: no source files, no prior docs or stack. Memory starts blank.
- **Existing**: source files and/or docs already present. Run the full ingestion pass.

---

## Step 2: Copy Forge structure (if not already present)

Confirm these folders exist at the repo root. Create any that are missing:
- `.cursor/rules/`   — constitution + memory + skills rules
- `.cursor/agents/`  — the six role files
- `skills/`          — registry + _template + pulled skills
- `memory/`          — decisions log, learnings, capability map
- `docs/`            — working docs (brief, research, plan, handoff, review)
- `tests/evals/`     — golden dataset, judge prompt, latency baseline (AI projects)
- `memory/backlog.md`— prioritized work queue for ongoing projects

**If `.cursor/rules/` already has files: merge, never overwrite.** Note any conflicts
in `memory/forge-changelog.md` for the Approver to resolve.

---

## Step 3: Doc ingestion (existing projects — this is the key step)

The project's existing `.md` files, rules, and docs ARE already memory. Do not ignore
them and do not re-load them every session. Instead, read them once and extract.

### 3a — Inventory
Scan the repo for:
- `.cursor/rules/*.mdc` or `.md` — existing agent rules and conventions
- `*.md` files in root, `/docs`, `/notes`, `/specs`, or similar
- `README.md`, `ARCHITECTURE.md`, `STACK.md`, `CONVENTIONS.md` (any names)
- Any existing project plan, roadmap, or spec files

List every file found with a one-line description of what it covers.

### 3b — Extract and distill
Read each file and extract the following (do not copy full text):
- **Stack and tooling**: language, framework, key libraries, deploy target
- **Conventions**: naming, file structure, code style, commit format
- **Architecture decisions**: why key choices were made, what was ruled out
- **Current state**: what is built, what is in progress, what is not started
- **Open questions or risks**: anything flagged as unresolved
- **Reusable modules**: anything that could belong in `@nathanokh/codebase`

### 3c — Write to memory
Populate these files from the extraction. Write short, factual entries; do not
copy paragraphs from the source docs.

**`memory/map/capability-map.md`**
- Projects node: this repo's name and one-line purpose
- Stack confirmed from docs
- Modules / reusable pieces found
- Skills being pulled for this project

**`memory/learnings/LEARNINGS.md`**
- One entry per key architectural decision or convention extracted
- Category: `best_practice` or `insight`
- Format: `[date] | best_practice | [what] | applies to: [this project / all projects]`

**`memory/map/doc-index.md`** ← create this file
- A lightweight index of every doc found, its location, and what it covers
- This replaces re-reading those files every session; agents check the index first
  and only open a specific doc when they need its full detail

Example entry:
```
| /docs/ARCHITECTURE.md | Core stack decisions, data model, API structure |
| .cursor/rules/stack.mdc | Next.js conventions, import aliases, Tailwind tokens |
```

### 3d — Rules reconciliation
Compare existing `.cursor/rules/` files against Forge's constitution.
- If a rule conflicts: note it in `memory/forge-changelog.md`, flag for Approver
- If a rule is compatible: it stays; add a reference to it in the constitution's
  TODO block so agents know it exists
- Do not delete existing rules under any circumstances

---

## Step 4: Pull only the skills this project needs

Do not load all agent-skills. Based on the project type and current phase:

| Situation                | Pull these skills |
|--------------------------|-------------------|
| Any project              | code-review-and-quality, security-and-hardening |
| Has a UI                 | + web-performance-auditor |
| Greenfield / ideating    | + interview-me, idea-refine, spec-driven-development |
| Active build phase       | + incremental-implementation, test-driven-development |
| Approaching ship         | + shipping-and-launch |
| Debugging in progress    | + debugging-and-error-recovery |

```
git clone https://github.com/addyosmani/agent-skills.git /tmp/agent-skills
cp -r /tmp/agent-skills/skills/<skill-name> ./skills/
```

---

## Step 5: Stack defaults — confirm or override

Check `00-constitution.mdc` stack defaults against what was detected.
If this project differs, append an override block (do not edit the defaults):

```
## Project overrides — [project name]
- Stack: [actual]
- Deploy: [actual]
- Conventions: see [doc name] in doc-index
```

---

## Step 6: Setup summary

Append to `memory/forge-changelog.md`:
```
[date] | forge-setup | onboarded [new/existing] project "[name]" |
  docs ingested: [n files], stack: [x], skills pulled: [list] | escalated: n
```

Surface a short summary to the Approver:
- Project type
- Docs found and indexed (not re-loaded — indexed)
- Stack confirmed
- Skills pulled
- Any conflicts or open questions needing their input

---

## Escalation

Setup is routine — proceed without approval. Escalate only if:
- A rules conflict needs a human decision
- The stack is ambiguous and the wrong assumption materially affects the plan
- Anything touches credentials, secrets, or existing prod config (Safety Floor)

---

## What this achieves

After forge-setup runs on an existing project:
- Agents start sessions knowing the project's stack, conventions, and current state
  **without re-reading the original docs** — the doc-index and capability map carry
  that knowledge forward
- Token usage drops: heavy docs only load when a specific task needs them
- Your existing work is preserved and respected, not overwritten
