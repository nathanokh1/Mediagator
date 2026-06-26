---
name: obsidian-setup
description: Sets up Obsidian as Forge's visual layer — graph view of all memory files, Mermaid rendering, Kanban backlog, and dynamic queries across the knowledge base. Run once after rag-setup and forge-setup. Point Obsidian at the project root folder. Free, zero build, zero maintenance.
---

# Obsidian Setup

Obsidian becomes Forge's visual dashboard. No build required — just point it at
the project folder. The whole Forge folder is the vault: memory, docs, skills,
everything is connected and browsable.

---

## One-time setup

### 1. Install Obsidian
Download free at obsidian.md. No account required.

### 2. Open the vault
- Open Obsidian → "Open folder as vault"
- Select your project root (the folder containing `.cursor/`, `memory/`, `skills/`)
- Obsidian indexes everything immediately

### 3. Install these plugins
Go to Settings → Community plugins → Browse

| Plugin | Why |
|--------|-----|
| **Kanban** | Turns `memory/backlog.md` into a visual drag-and-drop board |
| **Dataview** | Query across all files — build live views of forge-changelog, skills, decisions |
| **Templater** | Create new project docs from templates |
| **Git** | Auto-commit memory changes from inside Obsidian |
| **Mermaid Tools** | Extra Mermaid support (core Mermaid already built into Obsidian) |

Install order: Kanban first (you'll use it immediately), Dataview second.

### 4. Enable core settings
Settings → Editor:
- Strict line breaks: OFF
- Show frontmatter: OFF (cleaner reading)

Settings → Files & Links:
- Default location for new notes: `docs/`
- Use wikilinks: ON

Settings → Appearance:
- Base theme: Dark (matches Forge's color system)

---

## What you get immediately

### Graph view (Cmd/Ctrl + G)
Every file in `memory/` and `docs/` appears as a node. Files that link to each
other draw edges. The result is a live map of Forge's knowledge — more connected
than the Mermaid diagrams and interactive. Color-code by folder:
- Purple → `memory/`
- Blue → `skills/`
- Green → `docs/`
- Gold → root files (README, FORGE-EXPLAINED, CODEBASE)

To set colors: Graph view → Groups → Add group by folder path.

### Kanban backlog
Open `memory/backlog.md`. With the Kanban plugin, the table automatically becomes
a drag-and-drop board. Columns: Todo / In Progress / In Review / Done.

### Mermaid diagrams
Open `memory/map/forge-graph.md` or `memory/map/app-graph.md`. The Mermaid blocks
render inline as live diagrams. No export needed.

### forge-changelog timeline
Open `memory/forge-changelog.md`. Every entry is readable with full formatting.
Use Dataview to query it (see below).

---

## Dataview queries (add these to any note)

### All skills and what they do
````
```dataview
TABLE description FROM "skills"
WHERE file.name = "SKILL"
```
````

### Recent forge-changelog entries (last 10)
Obsidian doesn't query log files natively, but you can pin `forge-changelog.md`
as a tab and use Cmd+F to filter by type (ADDED, USED, DECISION, etc.)

### Backlog — active items only
````
```dataview
TABLE priority, status, notes FROM "memory"
WHERE file.name = "backlog"
SORT priority ASC
```
````

---

## Wikilinks — making the graph richer

Obsidian's graph view connects files that link to each other. The more wikilinks
in your memory files, the richer the graph. As you work, naturally reference other
files using `[[filename]]` syntax:

- In `LEARNINGS.md`: "This relates to [[capability-map]]"
- In `backlog.md`: "Depends on [[forge-setup]]"
- In `docs/brief.md`: "See prior art in [[docs/research]]"

The Skill Smith adds wikilinks when writing learnings that connect to existing files.

---

## Daily workflow with Obsidian open

1. Start agentmemory server
2. Open Obsidian (vault already open)
3. Check `memory/backlog.md` Kanban for today's task
4. Paste the right SESSION-START.md prompt into Cursor
5. Work in Cursor; Obsidian auto-refreshes as memory files update
6. End of session: review `memory/forge-changelog.md` in Obsidian for what happened

Obsidian is read-mostly during active work. Cursor and the agents write; you and
Obsidian read, navigate, and manage priorities.

---

## Gitignore note
The `.obsidian/` config folder should be committed so collaborators get the same
setup. Add this to `.gitignore` to keep workspace-specific files out:
```
.obsidian/workspace.json
.obsidian/workspace-mobile.json
```
