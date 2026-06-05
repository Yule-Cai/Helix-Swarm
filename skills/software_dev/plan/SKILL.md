# Plan Mode

**For this turn: plan only. No code, no execution.**

## Behavior
- Inspect repo with read-only commands if needed
- Do NOT edit any project files except the plan file
- Do NOT run mutating commands, commit, or push

## Output — write a markdown plan including
- Goal
- Proposed approach
- Step-by-step plan (exact file paths, test targets)
- Files likely to change
- Verification steps
- Risks and open questions

## Save
```
write_file(".hermes/plans/YYYY-MM-DD_HHMMSS-<slug>.md", content)
```

After saving: reply briefly with what was planned and the saved path.
If request is underspecified: ask one clarifying question instead of guessing.
