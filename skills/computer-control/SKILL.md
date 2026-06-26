---
name: computer-control
description: Gives Forge full control of a computer — seeing the screen, controlling mouse and keyboard, opening apps, running workflows. Two modes: supervised (Claude Cowork on host Mac) for tasks you watch, and autonomous (VM sandbox) for unattended operation. Use when agents need to control a UI that has no API, run workflows across desktop apps, or operate fully autonomously without touching the host machine.
---

# Computer Control

Full computer control for Forge agents. The agent sees the screen, reasons about
what to do, acts, observes the result, and iterates. The sense-reason-act-observe
loop applied to a full operating system.

---

## Two modes — pick based on whether you're watching

### Mode 1: Supervised — Claude Cowork (host Mac)
Use when you are present and watching. Fast to set up, full Mac access.

- Install Claude Desktop (desktop.claude.ai)
- Enable Computer Use in settings
- Claude sees your screen, controls mouse/keyboard, uses Chrome via MCP
- You watch and can stop it at any time
- **Safety**: runs on host — agent has access to your entire machine

Good for: quick automation tasks, demos, workflows you're supervising.
Not for: long unattended autonomous runs.

### Mode 2: Autonomous — VM Sandbox
Use when you want Forge to run unattended. Agent operates inside a VM;
your host machine is never touched.

**Local VM (Mac):**
- **UTM** — free, Apple Silicon native (utm.app)
- **Parallels** — paid, best performance on Mac

**Cloud sandbox (no local setup):**
- **E2B** — purpose-built for AI agent sandboxes, spins up in seconds
- Any cloud VM (AWS EC2, GCP, DigitalOcean) with Ubuntu

---

## Setup: VM sandbox (recommended for Forge autonomous)

### Option A: Local VM with UTM (free, Mac)

1. Download UTM from utm.app
2. Create a new VM:
   - OS: Ubuntu 24.04 LTS
   - RAM: 4GB minimum, 8GB recommended
   - Storage: 40GB
   - Enable: shared clipboard, directory sharing
3. Install dependencies in the VM:
   ```bash
   sudo apt update && sudo apt install -y \
     openssh-server xfce4 xrdp chromium-browser \
     python3-pip nodejs npm git
   ```
4. Enable SSH:
   ```bash
   sudo systemctl enable ssh && sudo systemctl start ssh
   ```
5. Note the VM's IP address: `ip addr show`

### Option B: E2B cloud sandbox (fastest start)

```bash
pip install e2b
```

```python
from e2b import Sandbox

sandbox = Sandbox("base")
# Agent now has a full Ubuntu environment
# Access via sandbox.process, sandbox.filesystem, sandbox.commands
```

Full docs at e2b.dev. Free tier available.

---

## MCP config for VM control

Add to `~/.cursor/mcp.json`:

```json
"ssh-vm": {
  "command": "npx",
  "args": ["-y", "mcp-ssh"],
  "env": {
    "SSH_HOST": "${VM_IP}",
    "SSH_USER": "ubuntu",
    "SSH_KEY_PATH": "${HOME}/.ssh/forge-vm"
  }
}
```

Generate a dedicated SSH key for the VM:
```bash
ssh-keygen -t ed25519 -f ~/.ssh/forge-vm -C "forge-vm"
# Copy public key to VM
ssh-copy-id -i ~/.ssh/forge-vm.pub ubuntu@VM_IP
```

---

## Computer Use MCP (for screen control)

For visual desktop control beyond SSH, add the Computer Use MCP:

```json
"computer-use": {
  "command": "npx",
  "args": ["-y", "@anthropic/computer-use-mcp"],
  "env": {
    "ANTHROPIC_API_KEY": "${ANTHROPIC_API_KEY}",
    "DISPLAY": ":0"
  }
}
```

This gives agents:
- `screenshot` — take a screenshot of current screen state
- `click` — click at coordinates or on an element
- `type` — type text
- `key` — press keyboard shortcuts
- `scroll` — scroll the page

---

## The perception-reasoning-action loop (computer use)

```
PERCEIVE   take screenshot, read screen state
     ↓
REASON     what is on screen? what needs to happen next?
     ↓
PLAN       which action achieves the next step?
     ↓
ACT        click / type / scroll / open app
     ↓
OBSERVE    take screenshot, confirm action worked
     ↓
ITERATE    did it work? if not, adjust and act again
```

This is `observe-and-iterate` applied to a full desktop. Max iterations: 10
for desktop tasks (more complex than code, more steps needed). Escalate after
10 without progress.

---

## What roles use computer control

| Role | What they do with it |
|------|---------------------|
| Builder | Run the built app, navigate it, confirm it works visually |
| Code Reviewer | Open the PR branch, run it, screenshot the result |
| Researcher | Navigate sites that block scrapers, interact with web apps |
| Skill Smith | Discover and test new tools by actually running them |

---

## Safety rules (non-negotiable)

**On the VM sandbox:**
- No access to host filesystem unless explicitly shared
- No access to host credentials or SSH keys
- VM can be destroyed and rebuilt anytime — treat it as disposable
- Never store real credentials in the VM; use test/dev keys only

**On the host Mac (Cowork mode):**
- Safety Floor applies: agent cannot delete files, install system software,
  or access iCloud/personal data without explicit approval
- Watch mode: if running on host, stay present
- Scope it: create a dedicated user account on Mac if you want more isolation

**In both modes:**
- Max iterations before escalating: 10
- Log every computer control action to `memory/forge-changelog.md` (type: USED)
- Take a screenshot before AND after any destructive action
- Never type passwords in a screenshot-observable session without masking

---

## Recommended setup for Nathan's workflow

1. **Dev and testing**: UTM local VM → SSH MCP + Computer Use MCP
   Agent builds in Cursor, then SSHes into VM to run and test the result.
   
2. **Visual QA**: Playwright MCP (already set up) for web, Computer Use for desktop apps

3. **Autonomous overnight runs**: E2B sandbox → spin up, run the task, destroy
   No VM to manage, clean slate every time.

4. **Quick supervised tasks**: Claude Cowork on host Mac
   You're watching, it's fast, no VM needed.
