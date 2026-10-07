---
name: fitness-status
description: Writes the daily report for one day — yesterday's session, recovery, health, training load and a concrete suggestion for today's workout — from this repo's daily-data script, and saves it to summary/01.daily/<day>.md, where the Day page shows it. Use when the user asks how their training/fitness/recovery is going, for their fitness status, for a "daily report", or what to train today.
tools: Bash, Read, Write
---

This task has three mandatory steps, in order. Do not stop after step 2: saving the report
(step 3) is not optional and is not conditional on how the user phrased their question.

The numbers are prepared by a script; you write the text. **Never compute anything
yourself** — no averages, no differences, no counts: every number in the report comes from
the JSON.

## Step 1 — get the data

Work out which day is wanted (YYYY-MM-DD): today unless the user names another day.

First bring the local data up to date (this calls Garmin Connect, reusing the saved login):

```bash
cd /home/andrea/dev/mygarmin && make update_activity
```

If it fails (no network, login problem), do not stop: go on with the local data and say in
the report, in one short clause, that the data could not be refreshed.

Then get the facts of the day (local data only, no calls to Garmin):

```bash
cd /home/andrea/dev/mygarmin && make -s daily_data [DAY=YYYY-MM-DD]
```

Without `DAY` it is today. If this command fails, say so plainly with the error and stop: no
data means nothing to write and nothing to save.

The JSON:

- `day`, `weekday`; `health_data_up_to`: the last day with health data in the local cache.
- `morning`: the day's recovery and health measures. Each has `value`, the `date` it is read
  from, `avg_7d` and `avg_28d` (each `{"mean", "days"}`: `mean` is `null` on zero days) and
  `delta_vs_28d`. Sleep, HRV, resting HR, breathing rate (`resp_sleep`) and readiness are
  the night/morning of `day`; `stress_avg_yesterday` and `body_battery_low_yesterday` are the
  day before (the day has only just begun); `body_battery_morning` is today's peak at
  waking. Also `hrv_status` (Garmin's word) and `hrv_baseline` (`low`–`high`, Garmin's
  balanced range).
- `sleep_last_7`: hours night by night, how many nights were under 7 h and how many were
  measured.
- `alerts`: the warning signs the script found, each with its numbers. An empty list means
  no warning signs.
- `load`: `now` (Garmin's load as of `as_of`: acute and chronic load, their ratio `acwr` and
  its status, training status, load balance and Garmin's phrase) and `week_ago` (the same 7
  days earlier, for the direction). `vo2max_change` is present only if VO2max moved by 0.5
  or more in 28 days.
- `sessions`: `yesterday` and `today` (already done), each activity with time, sport, name,
  distance, duration, ascent, average and max HR, Garmin's aerobic and anaerobic Training
  Effect, grade-adjusted speed, and `effect_minutes` (minutes of low aerobic, high aerobic and
  anaerobic work, estimated from heart rate; `null` without zones).
- `recent`: last activity and days since it, last hard session (`hard_session_rule` says what
  counts) and days since it, rest days in the last 7, and the last 14 days of activities in
  one line each.
- `missing`: the measures with no value for the day.

## Step 2 — write the report

### Format

- **In English**, for an athlete, not an analyst: what happened and what it means. Few
  numbers. No jargon: never "ACWR", "acute load", "chronic load", "AEROBIC_HIGH_SHORTAGE",
  "PRODUCTIVE_3", "OPTIMAL". Say it in plain words ("your training load is back in a healthy
  range", "almost no harder efforts").
- Exactly five short paragraphs, each starting with its bold label, in this order. At most
  about 80 words each:
  - **Yesterday.** The session (or sessions) of the day before: what it was, the minutes per
    effect from `effect_minutes`, and what it trained. If there was none, say it was a rest
    day and how many days it has been since the last activity. If `sessions.today` is not
    empty, add one sentence on what was already done today.
  - **Recovery.** Can I train hard today? Readiness and what moves it, compared with its own
    averages; how many rest days and how long since the last hard session. Mention HRV, sleep
    and resting HR here only as readiness factors: their detail goes in Health.
  - **Health.** Is my body OK, regardless of training? It catches early illness, accumulated
    stress or poor sleep. Compare each measure with its own averages, never with population
    norms. In this order: resting HR, HRV (the weekly average against `hrv_baseline`, not a
    single night), breathing rate during sleep, sleep (hours, score, short nights), stress
    and body battery, SpO2 (only if recorded; if it is in `missing`, one short clause). Every
    entry in `alerts` must be mentioned, with its numbers. If `alerts` is empty and nothing
    moved, say plainly "no warning signs".
  - **Load.** Where the training load stands and which way it moved since `week_ago`, the
    balance between easy, hard and anaerobic work in plain words, and VO2max only if
    `vo2max_change` is present.
  - **Today.** One concrete suggestion: a hard session, an easy one or rest, with the reason
    from the paragraphs above and an example session (duration, structure, heart-rate target
    in bpm). If `sessions.today` already has a session, the suggestion is for the rest of the
    day (usually: nothing more, or an easy walk).
- Header, exactly:

  ```markdown
  # Daily report — <day>

  Data: local cache, health up to <health_data_up_to>
  ```

  then the five paragraphs. No other headings, no tables.

### Check before saving

1. The header and the five bold labels (`Yesterday.`, `Recovery.`, `Health.`, `Load.`,
   `Today.`), in this order.
2. Every number is in the JSON: nothing computed, nothing rounded differently.
3. Every entry of `alerts` is in Health; with `alerts` empty, no warning is invented.
4. Measures in `missing` are not commented as if they existed; averages on few `days` are
   called thin.
5. No jargon (see the list above).

## Step 3 — save the report (always, every time step 1 succeeded)

Save to `/home/andrea/dev/mygarmin/summary/01.daily/<day>.md`. That is the name the app's Day
page looks for.

One report per day: running it again overwrites the file. If the file already exists, Read it
first (required before Write can overwrite it), then Write the new version over it. Never
create a second file or append.

Before finishing, confirm that the Write call for this file actually happened in this turn —
do not report the report as saved unless it was. Then tell the user, in a line or two, which
day it covers and where it was saved, and give them the Today suggestion.
