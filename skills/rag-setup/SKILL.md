---
name: rag-setup
description: Sets up the personal RAG layer (Layer 0) — the always-on knowledge base that indexes all of Forge's memory, project docs, and external content. Run once during initial Forge setup. Required, not optional. Without this, agents search the web before checking what you already know. Run this before forge-setup or as part of it.
---

# RAG Setup — Layer 0

The always-on personal knowledge base underneath everything else in Forge.
Indexes your memory, docs, skills, and external saved content. Queried
automatically at session start and by the Researcher before any web search.

This is not optional. It is the difference between an agent that knows your
history and one that starts from zero every time.

---

## What Layer 0 does

At session start → retrieve relevant context from your knowledge base automatically.
Researcher query → hit Layer 0 first, go to web only if nothing comes back.
New learnings → index them into Layer 0 as they're written.

---

## Recommended backend: agentmemory

Open source, MIT licensed, MCP-native (works directly in Cursor), supports
BM25 keyword + vector semantic + graph search simultaneously.

### Install

```bash
# Requires Python 3.10+
pip install agentmemory

# Start the MCP server (run this in a terminal that stays open)
agentmemory serve --port 8765
```

### Connect to Cursor

Add to your Cursor MCP config (`~/.cursor/mcp.json` or project-level):
```json
{
  "mcpServers": {
    "agentmemory": {
      "url": "http://localhost:8765",
      "description": "Personal RAG knowledge base for Forge"
    }
  }
}
```

Verify the install commands at github.com/AgentMemory/agentmemory before
running — they may have changed since this skill was written.

---

## Alternative backends

| Backend | Best for | Notes |
|---------|----------|-------|
| agentmemory | Default — multi-search, MCP-native | Recommended |
| claude-mem | Simpler setup, session-only | Less powerful search |
| Chroma | Local vector DB, no MCP needed | Requires more manual wiring |
| pgvector | If project already uses Postgres | Production-grade |

---

## What to index

Index these on first setup, then keep in sync as files change:

**Always index (Forge core):**
- `memory/forge-changelog.md`
- `memory/learnings/LEARNINGS.md`
- `memory/learnings/ERRORS.md`
- `memory/map/capability-map.md`
- `skills/README.md`
- `CODEBASE.md`

**Index per project:**
- `docs/brief.md`, `docs/plan.md`, `docs/research.md`
- `memory/map/doc-index.md`
- `memory/backlog.md`
- Any existing project docs surfaced by forge-setup

**Index as it grows (personal knowledge base):**
- Saved articles, links, research notes you paste in
- Past project handoffs and reviews
- External reference docs relevant to your work

### Initial index command (agentmemory)
```bash
# Index a file
agentmemory add --file memory/learnings/LEARNINGS.md --tags forge,learnings

# Index a folder
agentmemory add --folder memory/ --tags forge

# Index a URL (saved article, doc, reference)
agentmemory add --url https://example.com/article --tags research,saved
```

---

## Query order (enforced in Researcher role)

1. Query Layer 0 (agentmemory) — semantic + keyword search
2. Check `memory/map/doc-index.md` — is there a specific file to load?
3. Check `@nathanokh/codebase` — does a module already solve this?
4. Web search — only if 1-3 come back empty

---

## Keeping Layer 0 current

After every session where new content is created:
```bash
# Re-index updated files
agentmemory add --file memory/learnings/LEARNINGS.md
agentmemory add --file memory/forge-changelog.md
```

The Skill Smith adds indexing commands to `forge-changelog.md` entries whenever
a promotion candidate is confirmed, so Layer 0 stays in sync automatically.

---

## Log the setup
After completing setup, append to `memory/forge-changelog.md`:
```
YYYY-MM-DD HH:MM | SETUP | Layer 0 RAG initialized | rag-setup | forge-itself |
  backend: agentmemory, indexed: [list what was indexed]
```
