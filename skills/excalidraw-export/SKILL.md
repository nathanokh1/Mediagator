---
name: excalidraw-export
description: Converts Forge's Mermaid graphs (forge-graph, app-graph) into Excalidraw diagrams for sharing with clients or stakeholders. Use when you need a polished, presentable version of the architecture map or Forge structure. Does not replace the Mermaid source — the Mermaid files remain the working graphs that agents update. Requires the Excalidraw MCP server to be running.
---

# Excalidraw Export

Turns the internal Mermaid maps into beautiful, shareable Excalidraw diagrams.
One-way: Mermaid → Excalidraw. The Mermaid source stays as the working copy.
Agents never edit the Excalidraw output — it's for humans and presentations.

---

## When to use

- Sharing the app architecture with a client or stakeholder
- Presenting Forge's structure to a collaborator
- Creating a visual artifact for a proposal or doc
- When `forge-graph.md` or `app-graph.md` need to look polished

## When NOT to use

- Internal working diagrams — Mermaid is fine and auto-updates
- Anything agents will need to edit — they can't reliably update .excalidraw files

---

## Setup (one-time)

Install the Excalidraw MCP server:
```bash
npx excalidraw-mcp
```

Or via Claude Code / Cursor MCP config:
```json
{
  "mcpServers": {
    "excalidraw": {
      "command": "npx",
      "args": ["excalidraw-mcp"]
    }
  }
}
```

Verify current install method at the Excalidraw MCP repo before running.

---

## Steps

1. Read the source Mermaid file:
   - `memory/map/forge-graph.md` → Forge structure
   - `memory/map/app-graph.md` → project architecture

2. Extract the Mermaid diagram block(s) from the file.

3. Call the Excalidraw MCP tool with the diagram content.

4. Save the output to `memory/map/exports/`:
   - `forge-graph.excalidraw`
   - `app-graph.excalidraw`

5. Log to `memory/forge-changelog.md`:
   ```
   YYYY-MM-DD HH:MM | USED | excalidraw-export | [role] | [project] | exported [which graph]
   ```

---

## Notes

- The `.excalidraw` file is a JSON artifact — do not commit it to the
  working parts of the repo. Put it in `memory/map/exports/` and add
  `memory/map/exports/` to `.gitignore` if you don't want it tracked.
- Re-export whenever the Mermaid source changes significantly.
- The Excalidraw diagram does NOT auto-update — it is a snapshot.
