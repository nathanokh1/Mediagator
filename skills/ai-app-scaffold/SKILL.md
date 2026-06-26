---
name: ai-app-scaffold
description: The Layer 2 entry point. Use when the project being built is itself an AI-powered application — something that ships with agents, LLMs, memory, or AI features baked in. Run by the Architect after the brief is confirmed. Walks through 8 architecture decisions and produces a complete AI app starting structure. Do not use for standard web/app projects with no AI features.
---

# AI App Scaffold

Produces the architectural foundation for an AI-native application. Run after the
Ideation brief is confirmed. Output is a complete `docs/ai-architecture.md` that the
Builder follows — the AI layer equivalent of `docs/plan.md`.

---

## The 8 decisions

Work through each in order. Document every decision and the reason for it.

---

### Decision 1 — Purpose and scope
Read `docs/brief.md`. Extract and confirm:
- The core use case (what the AI does, not what the app does)
- Who the user is and what they hand the AI
- What a successful AI output looks like, concretely
- What the AI must never do (guardrails)
- What is out of scope for the AI layer specifically

---

### Decision 2 — System prompt design
Design the AI's identity and operating rules:
- **Role / persona**: who the AI is to the user
- **Goal**: what it is optimizing for in every response
- **Instructions**: step-by-step behavioral rules
- **Guardrails**: hard limits on behavior and output
- **Output format**: structure, length, tone

Write the draft system prompt to `docs/system-prompt.md`.
This is one of the highest-leverage decisions. A weak system prompt cannot be
patched later by a better model.

---

### Decision 3 — LLM selection
Run the `choose-your-llm` skill. Output: the chosen model, context window, and
cost/latency profile documented in `docs/ai-architecture.md`.

---

### Decision 4 — Tools and integrations
Identify what the AI needs to reach outside its context window:
- **Web / data APIs**: what external data sources it reads
- **Databases**: what it reads or writes to persistent storage
- **AI tools**: image gen, speech, embeddings, search (e.g. Cloudinary, Resend)
- **Custom functions**: business logic it needs to call

For each tool: name it, state what it does, and flag whether it is read-only or
can write/mutate data. Write-capable tools get extra scrutiny in error recovery.

Consult `memory/map/capability-map.md` and `@nathanokh/codebase` before adding
new integrations.

---

### Decision 5 — Memory architecture
Decide which memory types this app needs:

| Type | What it is | Use when |
|------|-----------|----------|
| File / doc storage | Markdown or JSON files on disk | Dev tools, small datasets, Forge itself |
| SQL / structured | Relational DB (Postgres, SQLite) | User data, transactions, queryable records |
| Vector store | Embeddings DB (Pinecone, pgvector, Chroma) | Semantic search, RAG over large doc sets |
| Episodic memory | Per-session conversation history | Chatbots, assistants that remember context |
| Semantic memory | Long-term facts about a user or domain | Personalized assistants, knowledge bases |

Most apps need 2-3 types, not all five. Choose the minimum that satisfies the use case.
Document the choice and why the others were ruled out.

If RAG is needed: flag it and use the `graphrag` or standard vector RAG pattern
depending on whether the answer lives in relationships (graph) or documents (vector).

---

### Decision 6 — Orchestration
Design how AI calls are sequenced and managed:
- **Single call**: one prompt, one response. Simple; use by default.
- **Chain**: output of one call feeds the next. Use for multi-step reasoning.
- **Agent loop**: AI decides its own next action until confident. Use for autonomous tasks.
- **Parallel**: multiple calls run simultaneously, results merged. Use for speed.

For each flow, define:
- Trigger: what starts it (user action, schedule, webhook, etc.)
- Parameters passed in
- How results are routed
- Error handling: run the `error-recovery` skill for each write-capable or
  externally-dependent step

---

### Decision 7 — User interface
Choose the surface the user interacts through:
- Chat interface (conversational, streaming)
- Web app UI (structured input/output, forms, dashboards)
- API endpoint (headless; another system calls it)
- Slack / Discord bot (team or community tooling)

This is a product decision, not an AI decision. Pick what fits the user, not what is
easiest to build. Document the choice and the reasoning.

---

### Decision 8 — Testing and evals
Run the `evals-and-quality` skill. Output: an eval plan written to `docs/eval-plan.md`.

---

## Output

Write `docs/ai-architecture.md` containing:
- All 8 decisions with one-paragraph rationale each
- Draft system prompt reference (full text in `docs/system-prompt.md`)
- Memory architecture diagram (text-based is fine)
- Orchestration flow (text-based)
- Eval plan reference (full plan in `docs/eval-plan.md`)
- Open questions for the Approver (if any)

Log to `memory/forge-changelog.md` and hand to the Builder.

## Escalation
Proceed autonomously through all 8 decisions. Escalate on a DIRECTION DECISION
(a genuinely ambiguous fork like build-vs-buy on a major component) or the SAFETY FLOOR.
