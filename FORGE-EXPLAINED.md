# Forge — Full Explanation

Everything you need to know about what Forge is, what it does, and how its pieces
fit together. Written for someone who knows how to build software but is new to
structured agentic workflows.

---

## What problem Forge solves

Every new project restarts from scratch: re-explaining the stack to the AI, re-writing
the same boilerplate rules, relearning what already exists in your codebase, rebuilding
things you already built. Forge is the system that stops all of that.

Drop Forge into a project and a small team of AI agents already knows your stack, your
conventions, your reusable code, and what phase the project is in. They build, review,
research, and grow their own skill set as they work — and they only pull you in when
something actually matters.

---

## The two layers

Forge has two distinct layers that serve different purposes.

---

### Layer 0 — Personal RAG (always installed)

**What it is:** The always-on personal knowledge base underneath everything else.

**Powered by:** agentmemory (MCP-native, BM25 + vector + graph search)

**What it does:**
- Indexes all of Forge's memory, project docs, skills, and external content you feed it
- Queried automatically at session start to retrieve relevant context
- Queried by the Researcher before any web search
- Grows continuously as learnings, decisions, and research are added

**When you use it:** Always. It runs in the background. You set it up once.

---

### Layer 1 — The Dev Workflow Platform

**What it is:** The AI team that helps you build *any* project faster.

**Lives in:** `.cursor/` (agents + rules), `skills/`, `memory/`

**What it does:**
- Runs six specialized roles that own different phases of work
- Maintains a growing skill set sourced from production-grade libraries
- Remembers what was decided, what was built, and what was learned — across sessions
- Detects when a capability is missing and fills the gap
- Indexes your existing docs so agents never re-read them from scratch

**When you use it:** Always. Every project. This is the foundation.

---

### Layer 2 — The AI App Scaffold

**What it is:** A specialized blueprint the Architect runs when the project being built
is *itself* an AI-powered application.

**Lives in:** `skills/ai-app-scaffold/` (plus three supporting skills)

**What it does:**
- Walks through 8 architecture decisions specific to AI apps
- Produces `docs/ai-architecture.md` — the complete AI layer plan
- Covers LLM selection, memory architecture, orchestration, evals, and error recovery
- Outputs a draft system prompt and eval plan as separate docs

**When you use it:** Only when the project ships with AI features (an AI assistant,
an agentic workflow, a product powered by an LLM). Not for standard web apps with no
AI layer.

---

### How they relate

```
Layer 1 (Forge dev team)
  └── Ideation    → defines what the app does
  └── Researcher  → finds prior art and existing tools
  └── Architect   → makes the technical plan
        └── runs ai-app-scaffold  ← Layer 2 kicks in here
              └── Decision 3: choose-your-llm
              └── Decision 8: evals-and-quality
              └── Decision 6: error-recovery (per tool/loop)
  └── Builder     → implements against the plan
  └── Code Reviewer → reviews + security + evals pass
  └── Skill Smith → fills capability gaps
```

Layer 1 is always running. Layer 2 is a skill Layer 1 invokes when the project calls
for it.

---

## The six roles (Layer 1)

Roles are the **who** — the agents that own phases of work. Each has one job. They hand
off to each other through shared documents and never overlap responsibilities.

| Role | Job | Reads | Writes |
|------|-----|-------|--------|
| **Ideation** | Sharpens a fuzzy idea into a scoped brief | Nothing (converses with you) | `docs/brief.md` |
| **Researcher** | Finds what already exists before building | `docs/brief.md` | `docs/research.md` |
| **Architect** | Turns the brief into a technical plan | `docs/brief.md`, `docs/research.md` | `docs/plan.md`, `docs/ai-architecture.md` |
| **Builder** | Implements code against the plan | `docs/plan.md` | Code, `docs/handoff.md` |
| **Code Reviewer** | Quality, security, and evals check | `docs/handoff.md`, diff | `docs/review.md` |
| **Skill Smith** | Detects missing capabilities and fills them | Skills registry, gaps noticed | New skills, registry updates |

---

## Skills (Layer 1 + Layer 2)

Skills are the **how** — reusable workflows the roles run. They are files, not people.
A role invokes a skill for a specific task; the skill provides the step-by-step method.

Skills load by **progressive disclosure**: only the name and description stay in context
at all times. The full skill body loads only when needed. Heavy resources (scripts,
reference docs) load only when used. This keeps token usage low.

### Where skills come from (sourcing order)
1. Local `skills/` registry — check here first
2. `addyosmani/agent-skills` — production-grade upstream library, pull and adapt
3. `@nathanokh/codebase` — your shared reusable library
4. New skill authored by Skill Smith — last resort only

### Current skill set

**Forge-native skills (built here)**
| Skill | What it does | Run by |
|-------|-------------|--------|
| `forge-setup` | Onboards Forge into any project | Skill Smith / you |
| `ai-app-scaffold` | Layer 2 entry: 8 AI architecture decisions | Architect |
| `choose-your-llm` | Selects the right model for the project | Architect (via scaffold) |
| `evals-and-quality` | Designs the AI output testing strategy | Code Reviewer / Architect |
| `error-recovery` | Defines failure handling for every AI call | Architect (via scaffold) |

**Pulled from addyosmani/agent-skills**
| Skill | What it does | Run by |
|-------|-------------|--------|
| `interview-me` | Structured ideation interview | Ideation |
| `idea-refine` | Sharpens a rough idea | Ideation |
| `spec-driven-development` | Turns a concept into a spec | Ideation → Architect |
| `planning-and-task-breakdown` | Sequences a spec into commits | Architect |
| `incremental-implementation` | The build loop | Builder |
| `test-driven-development` | Tests written alongside code | Builder |
| `debugging-and-error-recovery` | When something fails in the code | Builder |
| `code-review-and-quality` | The core code review | Code Reviewer |
| `security-and-hardening` | Security pass | Code Reviewer |
| `web-performance-auditor` | UI performance (optional, UI work only) | Code Reviewer |
| `code-simplification` | Reduce complexity | Builder / Reviewer |
| `shipping-and-launch` | The ship checklist | Builder |
| `using-agent-skills` | Discovers which skill fits a task | Skill Smith |

---

## Memory (Layer 1)

Memory is how Forge persists knowledge across sessions so agents never start from zero.

### The three memory types

**Working docs (`docs/`)**
The live handoff bus — generated per project as work progresses. Agents read the
upstream doc and write their own. Layer 1 docs are always present; Layer 2 docs
(`ai-architecture.md`, `system-prompt.md`, `eval-plan.md`) appear only on AI projects.

**Durable memory (`memory/`)**
Lessons and decisions that outlive a single project. Four files:
- `decisions.md` — a running log of every notable decision made
- `learnings/LEARNINGS.md` — corrections, insights, best practices extracted from real work
- `learnings/ERRORS.md` — command and integration failures worth remembering
- `learnings/FEATURE_REQUESTS.md` — things the Approver asked for, captured between sessions

**The self-map (`memory/map/`)**
The index of what exists and how it connects. Two files:
- `capability-map.md` — projects, modules, skills, and their relationships
- `doc-index.md` — a one-line-per-file table of contents for every doc in the project

### The doc-index: the token-saver
When Forge onboards an existing project, it reads all existing docs once and writes
a one-line summary of each into `doc-index.md`. From then on, agents check the index
first and load only the specific doc a task actually needs. This replaces re-reading
everything from scratch every session.

### Optional: retrieval memory backend
Static files are the baseline. For automatic session recall and semantic search across
memory, add a retrieval backend over MCP:
- **claude-mem** — session-lifecycle hooks, local storage
- **agentmemory** — MCP/HTTP server, BM25 + vector + graph search

These are optional. Forge works without them.

---

## Governance (Layer 1)

Three rules files in `.cursor/rules/` that apply to every agent at all times:

**`00-constitution.mdc`** — the operating law. Defines the Approver, the escalation
triggers, the reuse-first rule, and the stack defaults.

**`10-memory.mdc`** — how agents read and write memory. Enforces the doc-index pattern
and the four memory types.

**`20-skills.mdc`** — skill discovery and sourcing order. Enforces progressive
disclosure and the pull-don't-duplicate convention for upstream skills.

### Approval by exception
Agents run autonomously. They escalate to the Approver only on four triggers:
1. **Kickoff** — confirm scope once, at the start
2. **Material change** — the plan stops fitting reality
3. **Direction decision** — a real fork with meaningful tradeoffs
4. **Safety floor** — deploy, delete data, spend money, touch secrets

Everything else flows. Decisions get logged; you read the log when you want the picture.

---

## Key terms and definitions

**Agent**
An AI model running with a specific role, instructions, and set of tools. In Forge,
each agent has one job, one lane, and one set of skills it can invoke. They do not
message each other directly — they communicate through shared files.

**Approver**
You. The human controller. The only entity that authorizes scope changes, direction
decisions, and anything irreversible. Not a role file — baked into the constitution
as a behavioral constraint on all agents.

**Capability map**
The self-map of what Forge knows exists: projects, modules, skills, and the
relationships between them. Agents check it before building anything to avoid
recreating what's already there.

**Constitution**
The `00-constitution.mdc` file. The operating law of the agent team. Applies to
every agent in every session automatically.

**Context window**
The maximum amount of text an LLM can hold in memory at one time — both input and
output combined. Measured in tokens. Once exceeded, earlier content is forgotten.
Managing context is the primary reason Forge uses progressive disclosure and a
doc-index instead of loading everything at once.

**Doc index**
A one-line-per-file table of contents for every doc in the project.
Created by forge-setup. Agents check it before opening files so they only load
what the current task actually needs.

**Escalation**
When an agent stops and asks the Approver for input. Forge uses approval by exception:
agents escalate only on the four defined triggers, not at every step.

**Eval / Evaluation**
A structured test of an AI model's output quality. Unlike code tests (which check
correctness deterministically), evals measure reasoning quality, tone, accuracy,
and latency across a set of representative inputs. Required before shipping any AI
feature and before any model or prompt change.

**Gate**
A defined point in the workflow where a check must pass before work proceeds.
Forge has four gates: kickoff, material change, direction decision, and safety floor.
Agents run autonomously between gates.

**Guardrail**
A hard constraint on what an AI may output or do. Written into the system prompt.
Example: "Never recommend specific financial products." Guardrails are defined in
Decision 2 of the AI App Scaffold.

**LLM (Large Language Model)**
The AI model at the core of any AI feature — Claude, GPT-4o, Llama, etc. It takes
text (and sometimes images) as input and produces text as output. Different models
have different strengths, context windows, costs, and latency profiles.

**Memory (AI)**
How an AI system retains information. There are five types used in AI apps:
- Episodic: per-session conversation history
- Semantic: long-term facts about a user or domain
- Vector store: embeddings for semantic search (RAG)
- SQL / structured: relational data, queryable records
- File / doc storage: markdown, JSON, plain files

**MCP (Model Context Protocol)**
An open protocol for connecting AI models to external tools, data sources, and
services. How agents in Cursor talk to things like GitHub, Slack, or a memory backend.

**Orchestration**
The logic that controls when and how AI calls are sequenced. Four patterns:
- Single call: one prompt, one response
- Chain: output of one call feeds the next
- Agent loop: AI decides its own next action until done
- Parallel: multiple calls run simultaneously

**Persona**
The role and identity defined for an AI in its system prompt. Example: "You are a
senior code reviewer. Your job is to find bugs, not fix them." Determines tone, focus,
and behavioral defaults.

**Progressive disclosure**
A loading strategy where only a skill's name and description stay in context always;
the full body loads only when the skill is invoked; heavy resources load only when
used. Keeps token usage low without sacrificing capability.

**Promotion candidate**
A piece of reusable logic built inside a project that should be lifted into a formal
skill or into `@nathanokh/codebase` so it can be used across projects. Flagged in
handoff docs and captured by the Skill Smith.

**RAG (Retrieval Augmented Generation)**
A pattern where an AI retrieves relevant documents or data from an external index
before generating its response. Used when the answer lives in a document set too
large to fit in the context window. Two main variants:
- Vector RAG: finds semantically similar chunks (good for documents)
- GraphRAG: traverses a knowledge graph to find answers in relationships

**Role**
A Forge agent with a defined job. Roles are the who; skills are the how.
Six roles in Forge: Ideation, Researcher, Architect, Builder, Code Reviewer, Skill Smith.

**Safety floor**
The absolute bottom line of Forge governance. No agent may deploy, delete data, spend
money, rotate secrets, or take any hard-to-reverse action without explicit Approver
approval. Cannot be overridden.

**Skill**
A reusable workflow stored as a SKILL.md file. Skills are the how; roles are the who.
A role invokes a skill for a specific task; the skill provides the method.

**Skill Smith**
The Forge agent that detects missing capabilities and fills them. It checks the
skills registry and upstream libraries before authoring anything new. This is how
the skill set grows without manual intervention.

**System prompt**
The instructions given to an LLM before a user interaction begins. Sets the persona,
goals, behavioral rules, and guardrails. The highest-leverage configuration decision
in any AI app — a weak system prompt cannot be fixed by a better model.

**Token**
The unit of text an LLM processes. Roughly 3/4 of an English word. Models are billed
by token and constrained by context window (max tokens in one call). Forge's
progressive disclosure and doc-index patterns exist primarily to reduce token usage.

**Vector store / Embeddings**
A database that stores text as numerical representations (embeddings) so it can be
searched by meaning rather than exact keywords. The storage layer under RAG.

---

## File structure reference

```
project-root/
├── .cursor/
│   ├── rules/
│   │   ├── 00-constitution.mdc    ← operating law, always active
│   │   ├── 10-memory.mdc          ← memory behavior rules
│   │   └── 20-skills.mdc          ← skill sourcing and loading rules
│   └── agents/
│       ├── ideation.md
│       ├── researcher.md
│       ├── architect.md
│       ├── builder.md
│       ├── code-reviewer.md
│       └── skill-smith.md
│
├── skills/
│   ├── README.md                  ← the skills registry (phase→skill→role map)
│   ├── _template/SKILL.md         ← template for new skills
│   ├── forge-setup/SKILL.md       ← Layer 1: project onboarding
│   ├── ai-app-scaffold/SKILL.md   ← Layer 2: AI app architecture entry point
│   ├── choose-your-llm/SKILL.md   ← Layer 2: LLM selection
│   ├── evals-and-quality/SKILL.md ← Layer 2: AI output testing
│   ├── error-recovery/SKILL.md    ← Layer 2: failure handling
│   └── [pulled from agent-skills]/
│
├── memory/
│   ├── forge-changelog.md         ← all decisions, skill usage, and Forge changes (DECISION/USED/ADDED/etc)
│   ├── learnings/
│   │   ├── LEARNINGS.md           ← insights, corrections, best practices
│   │   ├── ERRORS.md              ← failures worth remembering
│   │   └── FEATURE_REQUESTS.md    ← things the Approver asked for
│   ├── backlog.md                 ← prioritized work queue for the project
│   └── map/
│       ├── capability-map.md      ← projects, modules, skills, relationships
│       ├── doc-index.md           ← one-line index of all project docs
│       ├── forge-graph.md         ← live Mermaid map of Forge's own structure
│       └── app-graph.md           ← live Mermaid map of the project under construction
│
│
│   (Layer 0 — agentmemory runs as an MCP server, separate from the file tree)
│   Connect via ~/.cursor/mcp.json — see INSTALL.md Step 1
│
├── CODEBASE.md                    ← how to set up and use @nathanokh/codebase
├── SESSION-START.md               ← copy-paste prompts for starting any Cursor session
├── .gitignore                     ← what to commit vs. keep private
└── docs/                          ← generated per project, not committed to template
    ├── brief.md                   ← Ideation output
    ├── research.md                ← Researcher output
    ├── plan.md                    ← Architect output
    ├── ai-architecture.md         ← Architect output (AI projects only)
    ├── system-prompt.md           ← Architect output (AI projects only)
    ├── eval-plan.md               ← Evals skill output (AI projects only)
    ├── handoff.md                 ← Builder output
    └── review.md                  ← Code Reviewer output
```

---

## Credits

- Skill library curated from **addyosmani/agent-skills** (SKILL.md standard, MIT)
- Optional memory backends: **claude-mem**, **agentmemory**
- Keep upstream attributions in all pulled skill files
