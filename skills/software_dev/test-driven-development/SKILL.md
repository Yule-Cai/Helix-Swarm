# TDD Protocol

**Rule: Write failing test FIRST. No exceptions.**

## Cycle
1. **RED** — Write one test for the behavior. Run it. Confirm it FAILS.
2. **GREEN** — Write minimal code to pass. Run it. Confirm it PASSES.
3. **REFACTOR** — Clean up. Keep tests green.

## Verify each step with terminal
```bash
pytest tests/test_feature.py::test_name -v   # RED or GREEN
pytest tests/ -q                              # No regressions
```

## Rules
- One behavior per test. Clear descriptive name.
- Never write production code before the test.
- If test passes immediately on first run → test is wrong, fix it.
- After GREEN: run full suite to check regressions.

## Stop signs — delete code, restart with TDD
- Code written before test
- Test passes immediately (never saw it fail)
- "I'll add tests after"
- "Too simple to test"
