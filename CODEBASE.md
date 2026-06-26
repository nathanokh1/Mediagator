# @nathanokh/codebase

The shared library that connects all your projects. When Forge says "check
@nathanokh/codebase before building anything reusable" — this is what it means.

---

## What it is

A private GitHub repository published as an npm package via GitHub Packages.
Any project in your GitHub org can install it and import shared components,
utilities, hooks, types, and functions. Stops you from rebuilding the same
auth component, image utility, or API client in every project.

---

## One-time setup (do this once)

### 1. Create the repo
```bash
# On GitHub: create a new repo under your account
# Name: codebase
# Visibility: private
# URL: github.com/nathanokh1/codebase
```

### 2. Initialize as an npm package
```bash
git clone https://github.com/nathanokh1/codebase.git
cd codebase
npm init -y
```

Edit `package.json`:
```json
{
  "name": "@nathanokh/codebase",
  "version": "0.1.0",
  "private": false,
  "publishConfig": {
    "registry": "https://npm.pkg.github.com"
  }
}
```

### 3. Authenticate with GitHub Packages
Create a `.npmrc` in the consuming project (not in the codebase repo itself):
```
@nathanokh:registry=https://npm.pkg.github.com
//npm.pkg.github.com/:_authToken=${GITHUB_TOKEN}
```

Add `GITHUB_TOKEN` to your environment (a GitHub personal access token with
`read:packages` and `write:packages` scopes).

### 4. Publish the first version
```bash
cd codebase
npm publish
```

### 5. Install in any project
```bash
npm install @nathanokh/codebase
```

---

## Folder structure

```
codebase/
├── src/
│   ├── components/     # Shared React/UI components
│   ├── hooks/          # Shared React hooks
│   ├── utils/          # Shared utility functions
│   ├── types/          # Shared TypeScript types
│   ├── api/            # Shared API clients and fetchers
│   └── styles/         # Shared design tokens, base styles
├── index.ts            # Main export barrel
├── package.json
└── README.md           # Document every export here
```

---

## How to add something (the promotion workflow)

When the Builder or Code Reviewer flags a PROMOTION CANDIDATE:

1. **Verify it's genuinely reusable** — used (or likely to be used) in more than
   one project. Don't promote one-off code.

2. **Copy to the right folder** in the codebase repo.

3. **Export it** from `index.ts`:
   ```ts
   export { MyComponent } from './src/components/MyComponent'
   export type { MyComponentProps } from './src/components/MyComponent'
   ```

4. **Document it** in the codebase `README.md` — one line: what it is and when
   to use it. This is what agents read when checking for reuse.

5. **Bump the version** following semver:
   - Patch (0.1.x) — bug fix, no API change
   - Minor (0.x.0) — new export, backwards compatible
   - Major (x.0.0) — breaking change to an existing export

6. **Publish**:
   ```bash
   npm version patch   # or minor or major
   npm publish
   ```

7. **Update consuming projects**:
   ```bash
   npm update @nathanokh/codebase
   ```

8. **Log it** in `memory/forge-changelog.md` as type PROMOTED.

---

## How agents check it

Agents check the codebase README.md for existing exports before designing anything
new. The README is the index — keep it current. Format:

```markdown
## Exports

| Export | What it does | Import from |
|--------|-------------|-------------|
| `useAuth` | Auth hook — session, user, signOut | `@nathanokh/codebase` |
| `ImageGallery` | Responsive image grid with Cloudinary | `@nathanokh/codebase` |
| `ApiClient` | Typed fetch wrapper with error handling | `@nathanokh/codebase` |
```

---

## Current exports

| Export | What it does | Import from |
|--------|-------------|-------------|
| _(empty — populate as modules are promoted)_ | | |

---

## Rules

- Never promote code that is still changing rapidly — stabilize it in the source
  project first.
- Never promote secrets, env vars, or config. Code only.
- If a module exists here, use it. Do not duplicate it in a new project.
- If you need to change a shared module, bump the version. Don't edit it silently.
