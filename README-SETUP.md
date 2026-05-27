# Mediagator — Cursor Setup Guide

## What's In This Package

```
.cursor/
  rules/
    development-lifecycle.mdc     — SDLC, comments, structure standards
    python-standards.mdc          — Python 3.12 coding standards
    file-transfer-safety.mdc      — File safety rules for irreplaceable media
    github-autopush.mdc           — Auto commit/push behavior
    mediamigrator-architecture.mdc — App-specific patterns and constants

CURSOR-PROJECT-PROMPT.md          — Paste this into Cursor Composer to build the app
README-SETUP.md                   — This file
```

---

## How to Set This Up

### Step 1 — Create your project folder
Create a new empty folder called `Mediagator` wherever you want the project to live.

### Step 2 — Copy the .cursor folder
Copy the entire `.cursor/` folder from this package into your `Mediagator` project folder.
Your structure should look like:
```
Mediagator/
  .cursor/
    rules/
      development-lifecycle.mdc
      python-standards.mdc
      file-transfer-safety.mdc
      github-autopush.mdc
      mediamigrator-architecture.mdc
```

### Step 3 — Open in Cursor
Open the `Mediagator` folder in Cursor (File → Open Folder).
Cursor will automatically detect and load the rules from `.cursor/rules/`.

### Step 4 — Initialize Git
In Cursor's terminal:
```bash
git init
git remote add origin <your-github-repo-url>
```

### Step 5 — Paste the Project Prompt
1. Open Cursor Composer: `Ctrl+I`
2. Switch to **Agent** mode (top of Composer panel)
3. Open `CURSOR-PROJECT-PROMPT.md`, copy everything below the dashed line
4. Paste into Composer and hit Enter
5. Let it build — it will scaffold the entire project structure and all modules

### Step 6 — Install Dependencies
Once Cursor generates `requirements.txt`:
```bash
pip install -r requirements.txt
```

### Step 7 — Run the App
```bash
python src/main.py
```

---

## GitHub Auto-Push
Once Git is set up, just tell Cursor in chat:
- "push to github"
- "push it"
- "commit and push"

Cursor will automatically stage, generate a commit message, commit, and push.
It will NOT push directly to main/master — it will warn you and ask for a branch name.

---

## Notes
- Python 3.12 required
- Windows only (uses Windows drive enumeration and toast notifications)
- Minimum screen resolution: 1000x700
