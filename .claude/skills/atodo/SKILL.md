---
name: atodo
description: Autonomously implement todo item N from ./todo — branch todo_NN, implement, verify, then status → 'done', commit and merge into main (or status → 'failed' and stop). Usage - /atodo 2
---

Implement one todo item from `./todo` in full autonomy, from branch to merge.
The argument is the todo number (e.g. `/atodo 2` → `todo/02_week_filters.md`).

## The todo file

Todo files live in `todo/` and are named `NN_short_slug.md`. Each starts with
YAML frontmatter carrying at least a status:

```markdown
---
status: todo        # todo | onhold | failed | done
---

# Short title

Work:
- what has to change, in enough detail to be the spec
```

Statuses:

- `todo`: ready to be implemented.
- `done`: implemented, verified, committed and merged into `main`.
- `failed`: stopped on a blocking ambiguity, a failed verification or a
  merge conflict; the todo file carries a "needs decision" note. Nothing is
  merged.
- `onhold`: deliberately parked by Andrea. Never started.

## Preconditions — refuse (politely, with the reason) if any fails

1. The argument resolves to exactly one `todo/NN_*.md` file.
2. That file's `status:` is `todo`. Never start `onhold`, `failed` or `done`
   items.
3. The working tree is clean (`git status --short` empty).
4. `main` has no uncommitted changes to tracked files: run
   `git -C <main worktree> status --short --untracked-files=no` (the main
   worktree is the first entry of `git worktree list`). Untracked files are
   fine.
5. The branch `todo_NN` does not already exist.

## Protocol

1. From current `main`, create and switch to branch `todo_NN`
   (e.g. `todo_02`).
2. Implement what the todo file's body ("Work:" section and context)
   specifies. The todo file is the spec; `README.md` and existing code idiom
   resolve details.
3. Verify continuously while implementing — after every meaningful change,
   not only at the end. See "Verification" below.
4. When implementation is complete, run the full verification for the areas
   you touched. If anything fails, go to "Failure" — no commit to `main`.
5. If green, on the branch:
   - set the todo file's `status:` to `done`;
   - update any docs the change makes stale (`README.md`, docstrings);
   - append the "Revert" section (below) at the very end of the todo file.
6. Commit everything on `todo_NN` in one commit (`git add -A`, then
   `git commit`). Message in Conventional Commits style: line 1
   `type(scope): summary` in English, imperative, max 72 characters; blank
   line; up to 5 bullet points of the main changes.
7. Merge into `main`, from the main worktree (`git -C <main worktree> ...`
   when running inside another worktree):
   - re-check precondition 4 (`main` may have moved while you worked);
   - `git merge --no-ff todo_NN -m "Merge branch 'todo_NN'"` — exactly this
     message: the Revert command finds the merge by it;
   - on conflicts: `git merge --abort`, then go to "Failure" (on the branch:
     status `failed`, note listing the conflicting files, one more commit on
     `todo_NN`). Never resolve conflicts yourself.
8. Show the merge commit (`git -C <main worktree> log -1 --oneline`) and
   report.

Never push. Never delete the `todo_NN` branch.

## The "Revert" section

Appended at the end of the todo file before the commit, in Italian without
accents like the rest of the todo. The command finds the merge commit by its
message, so it can be written before the merge exists:

````markdown
## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_NN'$" --format=%H -1)
```

Effetti fuori dal repo: <what the revert does NOT undo, or "nessuno">.

Dopo il revert, rifare il merge di `todo_NN` non riporta le modifiche (git le
considera gia' unite): per riaverle serve il revert del revert.
````

"Effetti fuori dal repo" lists anything the change writes outside git that a
code revert leaves behind: new tables or columns in `activities.db`, files
written into the data tree, downloaded data. Write "nessuno" when there are
none. Be concrete (e.g. "la tabella `health_daily` resta in `activities.db`:
e' innocua, il codice vecchio non la legge").

## Verification

This repo has no test suite. Verify with what it actually offers, in this
order:

- **Always**: the package still imports and the touched modules compile —
  `uv run python -c "import training"` plus an import of each module you
  changed (e.g. `uv run python -c "from training.interface import db"`).
- **Streamlit UI** (`src/training/interface/**`): `uv run streamlit run
  src/training/interface/app.py --server.headless true` in the background,
  confirm it serves without exceptions, then stop it. Read the console for
  tracebacks; do not leave the server running.
- **CLI entry points** (`training-fitness-status`, `training-activity-reports`):
  run the corresponding `make` target when it is read-only on local data.
- **Never run, unless the todo file explicitly asks for it**:
  `make update_activity`, `make backfill_activity_names`, `make
  backfill_health` and `make backfill`. They hit the Garmin API over the
  network and write into the data/summary tree — those are Andrea's to run,
  not yours.

If the todo file names a better check than these, that check wins.

## Autonomy rules — no questions, no confirmations

- **Resolvable ambiguity** (defaults, naming, placement, thresholds):
  take the smallest reasonable interpretation consistent with the todo
  file and code idiom. Proceed. Record every such call in the final report
  under "Decisions made".
- **Blocking ambiguity** — any of: widening scope beyond the todo file,
  a new dependency the todo file does not name, contradicting the documented
  design, or a change to previously agreed behaviour (see below): go to
  "Failure". Failure IS the question, asked asynchronously.
- The bar for stopping is "would Andrea plausibly veto this?", not "am I
  certain?". Stopping on trivia is a failure mode too.

## Integrity — never self-repair to green

If verification fails because a RESULT changed (a figure in a report, a
metric, what the UI shows) rather than because of an error, the expected
result may have legitimately changed — that decision is Andrea's. Do NOT
loosen a check, edit a config, or rewrite committed data to force green.
Go to "Failure" with a note "expected-result change: <old> → <new>, needs
decision".

## Failure

On the `todo_NN` branch: set `status: failed`, append a short "needs
decision" paragraph to the todo file (what blocked, options, recommendation),
commit everything on `todo_NN` (message `wip(todo): todo NN failed, needs
decision`), and stop. Do NOT merge. `main` stays untouched.

## Hard boundaries

- Implement only on the `todo_NN` branch. The only change ever made to
  `main` is the `--no-ff` merge of a green `todo_NN`.
- Never push, never force anything, never rewrite history, never delete the
  branch.
- Never start an `onhold` item.
- No new dependencies unless the todo file names the package explicitly
  (a named package counts as pre-authorization — add it to
  `pyproject.toml` via `uv add`, never install ad hoc only).
- Never edit other todo files' statuses.
- Never write into `summary/` or the exported data tree by hand; those are
  produced by the pipeline.

## Final report (chat only)

- Outcome: `done` and merged (with the merge commit hash), or `failed` and
  why.
- What was implemented, file by file, briefly.
- "Decisions made": every judgment call, one line each.
- Verification evidence: the commands run and their outcome.
- The revert command and the "Effetti fuori dal repo" line, as written in the
  todo.
