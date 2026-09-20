---
description: Generate a commit message from the delta vs main and commit immediately
---

Analyze the delta between the current branch and `main`:

1. Run `git rev-parse --abbrev-ref HEAD` and stop with a warning if the current branch is `main` itself
2. Run `git diff main...HEAD` to see the changes
3. Run `git log main..HEAD --oneline` to see the commits already made on this branch
4. Run `git status` to check for staged or unstaged changes to commit
5. Write ONE commit message in Conventional Commits style summarizing the merge:
   - line 1: `type(scope): summary` in English, imperative present tense, max 72 characters
   - blank line, then bullet points of the main changes (max 5 lines)
   - use "test" if it only touches tests, "chore" if it only touches config/CI
6. If there are unstaged changes that should be included, run `git add -A`
7. Commit with that message using `git commit -m "..."`
8. Show me the message used and the resulting commit hash (`git log -1 --oneline`)

Do not push. Stop and warn me if `git diff` is empty (no difference from main) or if there are conflicts.
