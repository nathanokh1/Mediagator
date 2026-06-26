---
name: evals-and-quality
description: Designs the testing and evaluation strategy for AI-powered features. Use during AI App Scaffold Decision 8, before shipping any AI feature, or when AI output quality is inconsistent. Covers unit tests for code, LLM output quality metrics, latency benchmarks, and the iteration loop. Different from standard code testing — AI outputs are probabilistic and need their own eval approach.
---

# Evals and Quality

AI outputs are not deterministic. Standard unit tests catch code bugs but cannot tell
you whether the LLM is giving good answers. This skill covers both.

---

## Two separate testing concerns

### 1. Code tests (standard)
Test the surrounding code as normal: API routes, data transforms, tool call wrappers,
UI components. These are deterministic and testable with Jest, Pytest, etc.
Use the `test-driven-development` skill from agent-skills for this layer.

### 2. LLM evals (AI-specific)
Test whether the model's outputs are actually good. Four dimensions:

| Dimension | What you measure | How |
|-----------|-----------------|-----|
| Correctness | Is the answer right? | Golden dataset: known input → expected output pairs |
| Quality | Is it well-reasoned, well-written? | LLM-as-judge: use a second model to score |
| Latency | How fast is the first token / full response? | p50 / p95 benchmarks under load |
| Regression | Does a model/prompt change break prior behavior? | Run evals before and after any change |

---

## Building the eval suite

**Step 1 — Golden dataset**
Write 10–20 representative input/output pairs that capture the range of what this
feature should do well. Include edge cases and things it must never do (from the
system prompt guardrails). Store in `tests/evals/golden.json`.

**Step 2 — LLM-as-judge**
For outputs that are hard to score mechanically (reasoning quality, tone, helpfulness):
write a judge prompt that scores the output 1–5 with a reason.
Store the judge prompt in `tests/evals/judge-prompt.md`.

**Step 3 — Latency baseline**
Run 20 calls under realistic load. Record p50 and p95 time-to-first-token and
total response time. Store in `tests/evals/latency-baseline.json`.
Flag if p95 exceeds the UX budget defined in the brief.

**Step 4 — Regression gate**
Before any prompt change, model upgrade, or major feature change: re-run the golden
dataset and compare scores. A drop of more than 10% on any dimension blocks the change.

---

## Output
Write `docs/eval-plan.md`:
- The golden dataset location and coverage
- The judge prompt location (if applicable)
- Latency budget and baseline
- Regression gate definition
- Who reviews eval failures (hint: the Code Reviewer runs evals; the Approver sees regressions)
