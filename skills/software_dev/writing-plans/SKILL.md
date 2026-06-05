# Writing Implementation Plans

**A good plan makes implementation obvious. If someone has to guess, the plan is incomplete.**

## Plan Structure

```markdown
# [Feature] Implementation Plan

**Goal:** [one sentence]
**Architecture:** [2-3 sentences]
**Tech Stack:** [key libraries/frameworks]

---

### Task N: [Name]
**Objective:** [one sentence]
**Files:** Create/Modify/Test [exact paths]

Step 1: Write failing test → [exact test code]
Step 2: Run: `pytest tests/path/test.py::test_name -v` → Expected: FAIL
Step 3: Implement: [exact minimal code]
Step 4: Run: `pytest tests/path/test.py::test_name -v` → Expected: PASS
Step 5: Commit: `git add [files] && git commit -m "feat: ..."`
```

## Before Writing
1. Read requirements fully
2. Explore codebase (`ls`, `cat` key files)
3. Design approach and file organization

## Task Granularity — each task = 2-5 minutes
- Bad: "Implement authentication system"
- Good: "Create User model with email field" / "Add password hashing" / "Create login endpoint"

## Principles
- **DRY** — extract shared logic, don't copy-paste
- **YAGNI** — only what's needed now, no "future flexibility"
- **TDD** — every code task has the full RED-GREEN cycle
- **Frequent commits** — one commit per task

## Save location
`docs/plans/YYYY-MM-DD-feature-name.md`

After saving: offer to execute with subagent-driven-development skill.
