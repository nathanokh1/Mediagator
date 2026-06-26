---
name: mcp-setup
description: Installs and configures the core MCPs that give Forge hands, eyes, and reach into external tools. Run once during initial setup after rag-setup. Without this, agents can reason and plan but cannot act on external systems, see rendered output, or run real commands. Required for full autonomous operation.
---

# MCP Setup — Forge's Nervous System

MCPs (Model Context Protocol servers) are what turn Forge from a thinking system into
a doing system. Each MCP adds a category of capability: hands to act, eyes to see,
reach into external services.

---

## The core MCPs

### 1. GitHub — hands on your repos
Read code, create branches, open PRs, post review comments, check issues.
The Researcher reads `@nathanokh/codebase` directly. The Builder creates PRs.
The Code Reviewer posts findings as comments. All without leaving Cursor.

```bash
# No install needed — runs via npx
# Requires a GitHub Personal Access Token with repo + PR permissions
# Create at: github.com/settings/tokens → Fine-grained token
# Scopes: Contents (read/write), Pull requests (read/write), Issues (read/write)
export GITHUB_TOKEN=your_token_here
```

Add to `~/.cursor/mcp.json`:
```json
"github": {
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-github"],
  "env": { "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}" }
}
```

### 2. Playwright — eyes on the browser
Opens a real browser, takes screenshots, clicks, fills forms, reads the DOM.
Builder ships a component → Playwright opens it → takes a screenshot → Code
Reviewer sees exactly what rendered. Catches visual bugs before you do.

```bash
npm install -g @playwright/mcp
npx playwright install chromium
```

Add to `~/.cursor/mcp.json`:
```json
"playwright": {
  "command": "npx",
  "args": ["@playwright/mcp"]
}
```

### 3. Brave Search — eyes on the web (controlled)
Real web search with full result content, not just snippets. Better than
built-in search for the Researcher's deep dives. Get a free API key at
api.search.brave.com (free tier: 2000 queries/month).

```bash
export BRAVE_API_KEY=your_key_here
```

Add to `~/.cursor/mcp.json`:
```json
"brave-search": {
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-brave-search"],
  "env": { "BRAVE_API_KEY": "${BRAVE_API_KEY}" }
}
```

### 4. Filesystem — hands on files across projects
Extended filesystem access beyond the current project. Lets agents reach into
`@nathanokh/codebase`, reference other projects, and manage files across directories.

```bash
# Set YOUR_PROJECTS_PATH to wherever your repos live e.g. ~/Projects
```

Add to `~/.cursor/mcp.json`:
```json
"filesystem": {
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "${YOUR_PROJECTS_PATH}"]
}
```

---

## Full `~/.cursor/mcp.json`

```json
{
  "mcpServers": {
    "agentmemory": {
      "url": "http://localhost:8765",
      "description": "Forge Layer 0 — personal RAG"
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    },
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp"]
    },
    "brave-search": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-brave-search"],
      "env": {
        "BRAVE_API_KEY": "${BRAVE_API_KEY}"
      }
    },
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "${YOUR_PROJECTS_PATH}"
      ]
    }
  }
}
```

---

## What each role gains

| Role | GitHub | Playwright | Brave Search | Filesystem |
|------|--------|-----------|--------------|------------|
| Researcher | Read repos, check codebase | Screenshot reference sites | Deep web research | Read across projects |
| Architect | Read existing code structure | — | Research patterns | Read shared modules |
| Builder | Create branches, push commits, open PRs | Visual smoke test after build | — | Read/write across project |
| Code Reviewer | Post review comments on PRs | Screenshot for visual diff | — | Compare files |
| Skill Smith | Check agent-skills upstream | — | Find new skills/libs | Access skill templates |

---

## Optional MCPs (add when needed)

| MCP | When to add |
|-----|-------------|
| Notion | If you use Notion for planning or client docs |
| Slack | If you want agent notifications to Slack |
| Linear | If you migrate backlog from markdown to Linear |
| Figma | When designing UI — agents read your design files |
| Vercel | When you want agents to trigger deploys (SAFETY FLOOR applies) |

---

## After setup

Restart Cursor. The agents now have the MCPs available as tools.
Log in `memory/forge-changelog.md`:
```
### YYYY-MM-DD HH:MM
- SETUP: MCPs configured
  by: you
  project: forge-itself
  reason: hands + eyes for full autonomous operation
  mcps: github, playwright, brave-search, filesystem
```
