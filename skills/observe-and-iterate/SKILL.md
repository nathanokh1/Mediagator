---
name: observe-and-iterate
description: The sense-reason-act-observe feedback loop. Use whenever an agent needs to do something, check if it worked, and adjust until it does. Run by Builder (code/tests), Code Reviewer (visual check), and Researcher (verifying findings). This is what makes Forge autonomous rather than one-shot — it keeps going until the outcome matches the goal or it hits the escalation ceiling.
---

# Observe and Iterate

The feedback loop that makes Forge autonomous. The pattern: act → observe the outcome
→ reason about what happened → adjust → act again. Repeat until success or escalate.

---

## The loop

```
┌─────────────────────────────────────────────┐
│                                             │
│  DEFINE  what success looks like            │
│     ↓                                       │
│  ACT     do the thing                       │
│     ↓                                       │
│  OBSERVE what actually happened             │
│     ↓                                       │
│  REASON  did it work? why / why not?        │
│     ↓                                       │
│  ┌─ SUCCESS → log it, move on              │
│  └─ FAILURE → adjust approach, ACT again   │
│        ↑__________________________|         │
│                                             │
│  CEILING: escalate after 5 iterations       │
└─────────────────────────────────────────────┘
```

---

## How to observe — by context

### Code / tests
```bash
# Run the tests, capture full output
npm test 2>&1
# or
pytest -v 2>&1
```
Read the output completely. Categorize failures:
- **Assertion error** → logic bug, fix the code
- **Import/module error** → dependency issue, fix the setup
- **Timeout** → performance problem, profile first
- **All passing** → success, move on

### Visual / browser (requires Playwright MCP)
1. Use Playwright to navigate to the page or component
2. Take a screenshot
3. Analyze: does it match the design spec or the goal?
   - Layout broken → check CSS, responsive breakpoints
   - Component missing → check render conditions, props
   - Wrong content → check data flow
4. Fix, reload, screenshot again, compare

### Build / compile
```bash
npm run build 2>&1
```
Read errors top-to-bottom. First error is usually root cause.
Fix root cause first — cascade errors disappear.

### API / network
Check response: status code, body shape, error messages.
- 4xx → client error (your request is wrong)
- 5xx → server error (the service is broken)
- Unexpected shape → schema mismatch, check types

---

## Logging observations (non-optional)

After each iteration, append a short observation to `memory/forge-changelog.md`:
```
### YYYY-MM-DD HH:MM
- USED: observe-and-iterate
  by: [role]
  project: [project]
  iteration: [n of max 5]
  observed: [what actually happened — one line]
  action: [what was adjusted — one line]
  status: [continuing | success | escalating]
```

This is how the feedback loop becomes memory. Future sessions start knowing
what patterns failed and what worked.

---

## The ceiling — when to stop and escalate

After **5 iterations** on the same problem without progress, STOP.
Do not keep trying the same thing in different ways.

Escalate to the Approver with:
- What was the goal
- What was tried (all iterations)
- What was observed each time
- Your best hypothesis for why it's stuck

This is not failure — this is the system working. Knowing when to stop and
ask is more valuable than grinding past the ceiling.

---

## Role-specific patterns

### Builder — code iteration
1. Write the implementation
2. Run tests: `npm test`
3. Read output — fix failures one at a time, root cause first
4. Rebuild and re-run
5. When all green: take a Playwright screenshot if it's UI work
6. If screenshot matches goal: write handoff.md, done

### Builder — visual iteration
1. Build the component
2. Playwright: navigate → screenshot
3. Compare to design spec or goal description
4. Fix CSS/layout issues
5. Playwright: reload → screenshot again
6. Repeat until visual matches goal

### Code Reviewer — visual diff
1. Playwright: screenshot the current state
2. Playwright: screenshot what it looked like before (if baseline exists)
3. Note visual regressions in `docs/review.md` under MUST FIX

### Researcher — verification
1. Find a candidate library or solution
2. Test it: clone/install, run the example
3. Observe: does it actually work for this use case?
4. If yes: recommend with confidence. If no: note why, find next candidate.

---

## What makes this different from just "trying again"

The loop only works if each iteration:
1. Changes something specific based on what was observed
2. Gets logged (so patterns emerge across sessions)
3. Has a hard ceiling (so it doesn't spin forever)

Random retries without observation is not a feedback loop. It's noise.
