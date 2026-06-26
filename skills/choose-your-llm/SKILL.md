---
name: choose-your-llm
description: Selects the right LLM for a project based on task type, context window needs, cost tolerance, and latency requirements. Run by the Architect during AI App Scaffold Decision 3, or any time a project adds an AI feature and the right model is unclear.
---

# Choose Your LLM

Picks the right model and documents the reasoning. Output appended to
`docs/ai-architecture.md` under "LLM Selection."

---

## The four questions

Answer these from `docs/brief.md` and the scaffold decisions so far.

**1. What is the primary task type?**
| Task | Lean toward |
|------|-------------|
| Reasoning, analysis, long-form generation | Claude Sonnet / Opus, GPT-4o |
| Code generation | Claude Sonnet, GPT-4o |
| Fast, short responses (chat, autocomplete) | Claude Haiku, GPT-4o mini |
| Image understanding | Claude Sonnet (vision), GPT-4o |
| Embeddings / semantic search | text-embedding-3-small (OpenAI), Voyage AI |
| Local / private (no cloud) | Llama 3, Mistral (self-hosted) |

**2. How much context does the app need in one call?**
- Under 32k tokens → any model works
- 32k–100k → Claude Sonnet (200k), GPT-4o (128k)
- Over 100k (large doc analysis, long codebases) → Claude Sonnet or Opus (200k)

**3. What is the latency requirement?**
- Real-time chat (under 2s first token) → Haiku, GPT-4o mini, or streaming Sonnet
- Background / async processing → any model; cost matters more than speed

**4. What is the cost profile?**
Check current pricing at time of build (prices change frequently):
- High volume / many users → Haiku or mini tier first; upgrade only if quality demands it
- Low volume / internal tool → cost is rarely the deciding factor; pick for quality

---

## Output

Document:
- Chosen model and provider
- Context window being used
- Cost estimate (per 1k tokens × expected call volume)
- Latency strategy (streaming y/n, async y/n)
- Why the alternatives were ruled out (one line each)
- Fallback model if the primary is unavailable
