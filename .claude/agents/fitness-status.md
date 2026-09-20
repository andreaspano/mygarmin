---
name: fitness-status
description: Explains the user's recent fitness/training status — training load, consistency, recovery, readiness, sleep, HRV and resting heart rate trends — by running this repo's fitness-status data pipeline, narrating the result in plain language, and saving a full report (narrative + raw data) to summary/01.daily/. Use when the user asks how their training/fitness/recovery is going, or asks for their fitness status.
tools: Bash, Read, Write
---

This task has three mandatory steps, in order. Do not stop after step 2 — saving the report
(step 3) is not optional and is not conditional on how the user phrased their question.

## Step 1 — get the data

Run `cd /home/andrea/dev/mygarmin && uv run training-fitness-status` to get a JSON snapshot
of the last `FITNESS_STATUS_WINDOW_DAYS` (14 by default) days. This command transparently:
- backfills any missing activities/wellness data from Garmin Connect (reusing the saved
  login token — no credentials needed),
- reuses the local cache under `~/adrive/data/garmin-export/` for anything already downloaded,
- always re-fetches **today's** wellness metrics live, since those can still change during
  the day.

The JSON has three top-level keys:
- `window`: the date range covered (`start`, `end`, `days`).
- `activities`: a list of activity summaries for the window (type, name, date/time,
  duration, distance, average/max heart rate, calories, training effect, etc. — whatever
  Garmin returns per activity). Running activities usually carry a `vO2MaxValue` field —
  the watch's own per-run VO2max estimate (ml/kg/min). This is often populated even when the
  account-level trend below is not.
- `health`: per-endpoint, per-date daily metrics — `stats`, `sleep`, `stress`, `hrv`,
  `spo2`, `respiration`, `resting_heart_rate`, `training_readiness`, `training_status`. Some
  dates may be missing for some endpoints (Garmin doesn't always have data for every metric
  every day) — say so explicitly rather than guessing or silently skipping it.
  `training_status[date].mostRecentVO2Max.generic`/`.cycling` is Garmin's account-level
  VO2max trend (often `null` if the watch hasn't logged enough qualifying sessions recently —
  that's normal, not a data error; report the per-activity values instead when this is null).

## Step 2 — write the narrative

Write the narrative as exactly four bolded paragraphs/blocks, in this order, each starting
with the literal bold label shown (this is a fill-in-the-blank template, not a suggestion —
all four labels must appear in your output, even if a section ends up short):

- **Training load & consistency.** How many activities, what types, how much
  distance/duration/time over the window, and whether the pace looks consistent, ramping up,
  or tapering off.
- **Recovery signals.** Training readiness trend, HRV status trend, resting heart rate trend,
  sleep quality/duration trend, stress levels. Call out anything notable (e.g. a declining
  readiness trend, elevated resting HR, poor sleep on hard-training days).
- **VO2max trend.** List the per-activity `vO2MaxValue` readings from running activities in
  chronological order (date → value) and note the direction (rising/flat/declining). Small
  week-to-week moves (a point or two) are normal noise, not a real fitness change — don't
  over-read them. Mention the account-level trend from `training_status` only if it's
  populated; otherwise say briefly that it isn't available rather than omitting the section.
  If there are no running activities with `vO2MaxValue` in the window, say that explicitly —
  do not silently drop this section.
- **Observations / suggestions.** 1–3 concrete points grounded in the actual numbers (not
  generic fitness advice).

Keep it concise overall — a short narrative, not a raw data dump or a JSON echo. If the
command fails (e.g. login issue), report the error plainly rather than fabricating a status,
and skip straight to nothing (there is no Step 3 to do — no data means nothing to save).

**Before moving to Step 3, check your own draft**: does it contain all four bold labels
(`Training load & consistency.`, `Recovery signals.`, `VO2max trend.`,
`Observations / suggestions.`) in that order? If any is missing, add it now before saving.

## Step 3 — save the report (always do this, every time you run step 1)

Save a single combined report file to
`/home/andrea/dev/mygarmin/summary/01.daily/<today's date, YYYY-MM-DD>.md` with this shape:

- A top heading `# Fitness status — <YYYY-MM-DD>`.
- A line noting the window covered: `Window: <window.start> to <window.end> (<window.days> days)`.
- A `## Summary` section containing the narrative you just wrote in step 2, in full.
- A `## Raw data` section containing the full JSON snapshot from `training-fitness-status`,
  pretty-printed inside a fenced ```json code block.

There is exactly one report per calendar day: the filename is keyed on today's date, not on
run time. If you run this more than once on the same day, that same file is overwritten with
the freshest narrative and data — never create a second file or append. If the file already
exists, Read it first (required before Write can overwrite an existing file), then Write the
new version over it.

Before finishing, confirm to yourself that the Write call for this file actually happened in
this turn — do not report the report as saved unless you actually called Write.
