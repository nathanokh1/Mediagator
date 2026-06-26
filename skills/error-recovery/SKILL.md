---
name: error-recovery
description: Defines how the system handles failures in AI calls, tool calls, and agent orchestration. Use during AI App Scaffold Decision 6 for any step that calls an external tool, writes data, or runs an agent loop. Also use when debugging a broken agentic flow. Covers retries, fallbacks, timeouts, partial failure, and how to surface errors to the user or Approver without losing work.
---

# Error Recovery

Every external call can fail. Every agent loop can get stuck. This skill defines the
recovery strategy before the failure happens, not after.

---

## Four failure modes and their responses

### 1. Transient failure (network blip, rate limit, timeout)
Strategy: **retry with backoff**
- Retry up to 3 times with exponential backoff (1s, 2s, 4s)
- Log each retry to `memory/learnings/ERRORS.md`
- If all retries fail, move to fallback or surface to user

### 2. Tool / API failure (external service is down or returns an error)
Strategy: **fallback or graceful degrade**
- Define a fallback for every write-capable or business-critical tool call
  (e.g., if email send fails → queue to retry; if search API fails → return cached results)
- Read-only tool failures can degrade gracefully (skip the tool, tell the user)
- Write tool failures must never silently drop data

### 3. Agent loop stuck (no progress after N iterations)
Strategy: **max-iterations cap + escalation**
- Set a hard cap on agent loop iterations (recommend: 10 for most tasks, 3 for destructive ops)
- If the cap is hit without a confident result: stop, preserve state, surface to the Approver
- Never let an agent loop run indefinitely

### 4. Partial failure (multi-step chain, one step fails mid-way)
Strategy: **checkpoint and resume**
- Write results to disk after each successful step
- On failure, identify the last successful checkpoint and resume from there
- Never re-run steps that already succeeded (idempotency)

---

## For every tool call in the orchestration plan, document:
- Can it fail transiently? → add retry
- Can it write or mutate data? → add fallback + idempotency check
- Is it in an agent loop? → set iteration cap
- Is it part of a chain? → add checkpoint

---

## Error surfaces
- **User-facing errors**: clear, non-technical, actionable ("Something went wrong — try again" or "We couldn't reach X, here's what we have so far")
- **Dev / log errors**: full detail, written to `memory/learnings/ERRORS.md`
- **Approver escalation**: any error that caused data loss, a stuck loop, or a safety-floor breach

---

## Output
Add an "Error recovery" section to `docs/ai-architecture.md` covering each tool and
agent loop in the orchestration plan with its failure mode and recovery strategy.
