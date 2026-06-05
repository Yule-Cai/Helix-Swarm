# Pre-Commit Code Review

**Use after code changes, before `git commit` or `git push`.**

## Step 1 — Get diff
```bash
git diff --cached    # If empty, try: git diff
```

## Step 2 — Static security scan (added lines only)
```bash
git diff --cached | grep "^+" | grep -iE "(api_key|secret|password|token)\s*=\s*['\"][^'\"]{6,}['\"]"
git diff --cached | grep "^+" | grep -E "os\.system\(|subprocess.*shell=True|eval\(|exec\(|pickle\.loads?\("
```

## Step 3 — Run baseline tests
```bash
python -m pytest --tb=no -q 2>&1 | tail -5   # Python
npm test -- --passWithNoTests 2>&1 | tail -5  # Node
```
Count failures BEFORE your changes (stash/unstash). Only NEW failures block the commit.

## Step 4 — Self-review checklist
- [ ] No hardcoded secrets
- [ ] Input validation on user data
- [ ] SQL queries parameterized
- [ ] Error handling on external calls
- [ ] No debug logs left behind
- [ ] Tests exist for new code

## Step 5 — Independent reviewer subagent
Call `delegate_to_expert("Reviewer", task)` with ONLY the diff and scan results.
Reviewer returns JSON: `{passed, security_concerns, logic_errors, suggestions, summary}`
Fail-closed: unparseable response = FAIL.

## Step 6 — Auto-fix loop (max 2 cycles)
If failures: dispatch a fix agent with only the specific issues. Re-run Steps 1-5.
After 2 failed cycles: report to user, suggest `git stash`.

## Step 7 — Commit
```bash
git add -A && git commit -m "[verified] <description>"
```
