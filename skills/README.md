# Forge Skills Registry

> What Forge can do. Agents check here before writing new code.

Skills are reusable, composable playbooks. Each lives in its own folder with a `SKILL.md` that defines inputs, outputs, steps, and memory hooks.

Source order (agents follow this): **Layer 0 RAG → this registry → `~/agent-skills` → write new**.

---

## Native Skills

| Skill | Folder | Purpose |
|-------|--------|---------|
| forge-setup | `forge-setup/` | Onboard Forge into any new or existing project |
| ai-app-scaffold | `ai-app-scaffold/` | 8-decision AI architecture scaffold (model, RAG, evals, etc.) |
| choose-your-llm | `choose-your-llm/` | LLM selection guide (cost, latency, capability matrix) |
| evals-and-quality | `evals-and-quality/` | AI output evaluation strategy and test harness |
| error-recovery | `error-recovery/` | Failure handling patterns for AI calls and tool errors |
| rag-setup | `rag-setup/` | Layer 0 agentmemory setup and ingestion |
| mcp-setup | `mcp-setup/` | Configure GitHub, Playwright, Brave, Filesystem MCPs |
| obsidian-setup | `obsidian-setup/` | Obsidian visual dashboard, Kanban backlog, graph view |
| observe-and-iterate | `observe-and-iterate/` | Sense-reason-act-observe loop for iterative builds |
| computer-control | `computer-control/` | VM / desktop control via SSH and computer-use MCP |
| documentation-update | `documentation-update/` | Post-merge doc sync across memory and app-graph |
| excalidraw-export | `excalidraw-export/` | Export Mermaid diagrams to Excalidraw format |

---

## Upstream Skills (~/agent-skills)

Cloned from [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) (MIT).  
Available after `git clone https://github.com/addyosmani/agent-skills.git ~/agent-skills`.

Agents pull from this library when no native skill covers the need.

---

## Writing New Skills

Use the template at `_template/SKILL.md`. Skill Smith writes skills during real work sessions — review, then commit and push to keep the registry current.

Promotion rules (from `20-skills.mdc`):
1. Used successfully ≥2 times → promote to native
2. Supersedes an existing skill → mark old one `RETIRED` in forge-changelog
3. New skill must include: inputs, outputs, steps, memory-hooks, and a test case

---

## Skill Health

Run the Skill Smith quarterly health check to identify stale or redundant skills:

```
Quarterly task: Run Skill Smith health check.
Scan ~/.forge/memory/forge-changelog.md for USED entries,
identify stale skills, and log a HEALTH-CHECK entry.
```
