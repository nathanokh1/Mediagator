# Getting Started

## Prerequisites (done once)
1. Install Forge globally: `git clone https://github.com/nathanokh1/forge.git ~/.forge`
2. Add aliases to `~/.zshrc` (see INSTALL.md)
3. Install agentmemory, Playwright, Obsidian
4. Set env vars: GITHUB_TOKEN, BRAVE_API_KEY, YOUR_PROJECTS_PATH, ANTHROPIC_API_KEY

---

## nathanokh.com (existing project)

```bash
cd ~/path/to/nathanokh.com
forge-init --existing
```

What forge-init does:
- Symlinks `.cursor/agents/` → `~/.forge/.cursor/agents/`
- Symlinks each rule file → `~/.forge/.cursor/rules/`
- Symlinks `skills/` → `~/.forge/skills/`
- Symlinks `.obsidian/` → `~/.forge/.obsidian/`
- Creates `memory/` with project-specific files (real files, not symlinks)
- Creates `.cursor/rules/project.mdc` for your project-specific overrides
- Registers nathanokh.com in `~/.forge/memory/map/capability-map.md`

Then:
```bash
forge-start
```
Open Obsidian → "Open folder as vault" → select the nathanokh.com folder.
Open Cursor and paste:
```
Run forge-setup on this project. It's an existing project with docs already
in place — run the full ingestion pass.
This is nathanokh.com — my personal portfolio site. Stack: Next.js 14,
TypeScript, Tailwind CSS, Framer Motion, Cloudinary, Resend, Vercel.
Three verticals: Creative & Media, AI & Development, Enterprise & Systems.
I have existing Cursor rules and design system docs. Show me the setup
summary before we proceed.
```

---

## New project

```bash
mkdir ~/Projects/my-project && cd ~/Projects/my-project
git init
forge-init
forge-start
```

Open Obsidian → vault = project folder.
Open Cursor and paste:
```
Run forge-setup on this project. It's a new project — memory starts blank.
Here's the idea: [your idea]. Start with Ideation once setup is complete.
```

---

## Daily rhythm
```bash
forge-start          # always first — updates Forge, starts RAG
# Open Obsidian → check backlog Kanban for today's task
# Open Cursor → paste SESSION-START prompt
# Work — agents write to memory/ as they go
# Obsidian shows what happened in real time
```

---

## What lives where (quick ref)
| What | Where |
|------|-------|
| What's next | `memory/backlog.md` (Obsidian Kanban) |
| What's built | `memory/map/app-graph.md` |
| What Forge can do | `skills/README.md` |
| This project's history | `memory/forge-changelog.md` |
| Forge's own history | `~/.forge/memory/forge-changelog.md` |
| All projects index | `~/.forge/memory/map/capability-map.md` |
| How to start sessions | `SESSION-START.md` |
| Everything explained | `FORGE-EXPLAINED.md` |
