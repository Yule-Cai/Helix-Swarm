# Systematic Debugging

**Rule: NO fixes without root cause investigation first.**

## 4 Phases (complete each before proceeding)

### Phase 1 — Root Cause
- Read error messages completely (stack traces, line numbers)
- Reproduce the issue: `pytest tests/test_x.py::test_name -v --tb=long`
- Check recent changes: `git diff` / `git log --oneline -10`
- Trace data flow upstream to find the source (not the symptom)
- **STOP here until you understand WHY it's broken**

### Phase 2 — Pattern
- Find similar working code in the codebase (`search_files`)
- List every difference between working and broken

### Phase 3 — Hypothesis
- State: "I think X is root cause because Y"
- Make the SMALLEST possible change to test it
- One variable at a time

### Phase 4 — Fix
- Write failing test reproducing the bug first (use TDD skill)
- Fix root cause only — no "while I'm here" changes
- Run full suite: `pytest tests/ -q`
- **If 3+ fixes failed → STOP, question the architecture, discuss with user**

## Stop signs — return to Phase 1
- "Quick fix for now"
- "Just try X and see"
- Proposing fixes before tracing data flow
- "One more attempt" (when already tried 2+)
