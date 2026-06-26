# Session Start

## Before every session
```bash
forge-start   # pulls Forge updates + starts agentmemory on :8765
```
Then open Obsidian (vault = project folder) and check the backlog Kanban.

---

## New project
```
Run forge-setup on this project. It's a new project — memory starts blank.
Here's the idea: [your idea in 1-2 sentences].
Start with Ideation once setup is complete.
```

## Continuing an existing project
```
We're continuing work on [project name].
Check memory/map/doc-index.md and memory/map/app-graph.md to orient yourself,
then check memory/backlog.md for what's next.
Today's goal: [what you want to accomplish].
```

## First time adding Forge to an existing project
```
Run forge-setup on this project. It's an existing project with docs already
in place — run the full ingestion pass.
Here's what it is: [1-2 sentences].
Show me the setup summary before we proceed.
```

## After a long break
```
I haven't touched this project in a while. Orient yourself:
1. Read memory/map/doc-index.md
2. Read memory/forge-changelog.md (last 10 entries)
3. Read memory/map/app-graph.md for build status
4. Read memory/backlog.md for what was next
Give me a one-paragraph summary of where things stand.
```

## Adding an AI feature
```
We're adding an AI feature to [project name].
Read docs/plan.md for current architecture, then run ai-app-scaffold.
The feature: [describe it].
```

## Quick task
```
Quick task on [project name]: [describe it].
Check skills/README.md for any relevant skill. Log to memory/forge-changelog.md when done.
```

## Quarterly Skill Smith health check
```
Run the Skill Smith quarterly health check on Forge.
Scan ~/.forge/memory/forge-changelog.md for USED entries,
identify stale skills, and log a HEALTH-CHECK entry.
```
