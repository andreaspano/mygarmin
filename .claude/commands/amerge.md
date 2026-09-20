---
description: Switch to main and merge the current branch into it
---

Merge the current branch into `main`:

1. Run `git rev-parse --abbrev-ref HEAD` to get the current branch name. If it is already `main`, stop and tell me there is nothing to merge.
2. Run `git status` and stop with a warning if there are staged or unstaged changes (the working tree must be clean before switching branches).
3. Note the branch name from step 1, then run `git checkout main`.
4. Run `git pull --ff-only` to make sure local `main` is up to date (it tracks `origin/main`). If the fast-forward fails, stop and warn me instead of resolving it yourself.
5. Run `git merge --no-ff <branch>` using the branch name captured in step 1.
6. If the merge reports conflicts, stop and list the conflicting files — do not attempt to resolve them automatically.
7. Run `git log -1 --oneline` to show the resulting merge commit.
8. Run `git checkout main` to make sure the session ends on the `main` branch.

Do not push, and do not delete the merged branch.
