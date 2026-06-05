# Subagent-Driven Development

**Execute implementation plans by dispatching fresh subagents per task with two-stage review.**

## Per-Task Workflow

### 1. Dispatch Implementer
```python
delegate_to_expert("Coder", """
Task: [full task text from plan]
Context: [project structure, relevant files, tech stack]
Follow TDD: write failing test → verify FAIL → implement → verify PASS → commit.
""")
```

### 2. Spec Compliance Review
After implementer completes, check against the original spec:
- All requirements implemented?
- File paths match spec?
- No scope creep?
→ If gaps: fix, re-review. Continue only when PASS.

### 3. Code Quality Review
```python
delegate_to_expert("Reviewer", """
Review files: [list files changed]
Check: conventions, error handling, naming, test coverage, security.
Output: Critical Issues / Important Issues / Minor Issues / Verdict (APPROVED or REQUEST_CHANGES)
""")
```
→ If issues: fix, re-review. Continue only when APPROVED.

### 4. Mark complete, move to next task.

## After ALL tasks
Run full test suite. Dispatch final integration reviewer to check everything works together.

## Rules
- Fresh subagent per task (no context pollution)
- Spec compliance review BEFORE code quality review
- Never skip either review
- Provide full task text in context — don't make subagents read plan files
- Each task = 2-5 min of focused work
