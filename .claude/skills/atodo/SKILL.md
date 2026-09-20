---
name: atodo
description: Autonomously implement todo item N from ./todo — branch todo_NN, implement, verify, status → 'to commit'. Usage - /atodo 2
---

Implement one todo item from `./todo` in full autonomy. The argument is the
todo number (e.g. `/atodo 2` → `todo/02_week_filters.md`).

## The todo file

Todo files live in `todo/` and are named `NN_short_slug.md`. Each starts with
YAML frontmatter carrying at least a status:

```markdown
---
status: todo        # todo | onhold | failed | to commit | done
---

# Short title

Work:
- what has to change, in enough detail to be the spec
```

## Preconditions — refuse (politely, with the reason) if any fails

1. The argument resolves to exactly one `todo/NN_*.md` file.
2. That file's `status:` is `todo`. Never start `onhold` (deliberate holds),
   `failed`, `to commit`, or `done` items.
3. The working tree is clean (`git status --short` empty).
4. The branch `todo_NN` does not already exist.

## Protocol

1. From current `main`, create and switch to branch `todo_NN`
   (e.g. `todo_02`).
2. Implement what the todo file's body ("Work:" section and context)
   specifies. The todo file is the spec; `README.md` and existing code idiom
   resolve details.
3. Verify continuously while implementing — after every meaningful change,
   not only at the end. See "Verification" below.
4. When implementation is complete, run the full verification for the areas
   you touched.
5. If green: set the todo file's `status:` to `to commit`, update any docs
   the change makes stale (`README.md`, docstrings), and report.
6. Do NOT commit, do NOT merge, do NOT push. Andrea's manual close-out is:
   his own check → status 'done' → /acommit → /amerge.

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
  `make update_activity` and `make backfill_activity_names`. They hit the
  Garmin API over the network and write into the data/summary tree — those
  are Andrea's to run, not yours.

If the todo file names a better check than these, that check wins.

## Autonomy rules — no questions, no confirmations

- **Resolvable ambiguity** (defaults, naming, placement, thresholds):
  take the smallest reasonable interpretation consistent with the todo
  file and code idiom. Proceed. Record every such call in the final report
  under "Decisions made".
- **Blocking ambiguity** — any of: widening scope beyond the todo file,
  a new dependency the todo file does not name, contradicting the documented
  design, or a change to previously agreed behaviour (see below): set
  `status: failed`, append a short "needs decision" paragraph to the todo
  file (what blocked, options, recommendation), and stop. Failure IS the
  question, asked asynchronously.
- The bar for stopping is "would Andrea plausibly veto this?", not "am I
  certain?". Stopping on trivia is a failure mode too.

## Integrity — never self-repair to green

If verification fails because a RESULT changed (a figure in a report, a
metric, what the UI shows) rather than because of an error, the expected
result may have legitimately changed — that decision is Andrea's. Do NOT
loosen a check, edit a config, or rewrite committed data to force green.
Set `status: failed` with a note "expected-result change: <old> → <new>,
needs decision" and stop.

## Hard boundaries

- Work only on the `todo_NN` branch; never touch `main`.
- Never commit, merge, or push.
- Never start an `onhold` item.
- No new dependencies unless the todo file names the package explicitly
  (a named package counts as pre-authorization — add it to
  `pyproject.toml` via `uv add`, never install ad hoc only).
- Never edit other todo files' statuses.
- Never write into `summary/` or the exported data tree by hand; those are
  produced by the pipeline.

## Final report (chat only — this is the handoff)

- What was implemented, file by file, briefly.
- "Decisions made": every judgment call, one line each.
- Verification evidence: the commands run and their outcome.
- Reminder: "After your own check, flip `status: to commit` → `done`
  in todo/NN_*.md, then /acommit and /amerge."
