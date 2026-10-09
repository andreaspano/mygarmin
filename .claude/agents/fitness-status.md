---
name: fitness-status
description: Writes the daily report for one day — that day's training, recovery, health, training load and a concrete suggestion for the next session — from this repo's daily-data script, and saves it to summary/01.daily/<day>.md, where the Day page shows it. Use when the user asks how their training/fitness/recovery is going, for their fitness status, for a "daily report", or what to train today.
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
  days earlier, for the direction). `targets`: Garmin's target range (`min`/`max`) for each of
  the three monthly loads, or `null`; a load below its `min` is a shortage, above its `max`
  more than needed. `vo2max_change` is present only if VO2max moved by 0.5 or more in 28
  days.
- `sessions`: `yesterday` and `today` (already done), each activity with time, sport, name,
  distance, duration, ascent, average and max HR, Garmin's aerobic and anaerobic Training
  Effect, grade-adjusted speed, `effect_minutes` (minutes of low aerobic, high aerobic and
  anaerobic work, estimated from heart rate; when the watch saved no anaerobic threshold, as
  on the bike, activities from August 2026 borrow the threshold of the latest run, so the
  split of a ride leans to low aerobic; `null` only when there are no zones at all, as in
  older files) and `minutes_above_z3` (minutes above the top of Z3, i.e. the harder work; it
  exists even when `effect_minutes` is `null` — use it then).
- `recent`: `trained_today` (an activity is already done on `day`), the last activity
  **before** `day` and days since it, the last hard session **before** `day`
  (`hard_session_rule` says what counts) and days since it, rest days in the last 7, and the
  last 14 days of activities in one line each. The "before today" counts ignore what was done
  on `day` on purpose: when `trained_today` is true, never write "N days since your last
  activity" as if today were still a rest day — say "before today's run, the last one was…".
  `consecutive_training_days_before_today` and `consecutive_rest_days_before_today` are the
  runs of training or rest days up to the day before; `last_7_days` lists those 7 days one by
  one with their activities. **Every calendar statement** ("three days in a row", "after two
  rest days", "back-to-back", "the first run since…") must come from these fields — never
  count days yourself.
- `hr_zones`: the heart-rate zones in bpm in force on `day` (from the latest run, hike or walk
  up to that day, `as_of`; bike zones are lower and are not used): `zones` Z1–Z5 with `min`/`max`, `threshold_hr` (the anaerobic
  threshold), and `effects`, the bpm ranges of low aerobic, high aerobic and anaerobic work.
  `null` if no activity has them.
- `missing`: the measures with no value for the day.

## Step 2 — write the report

### Format

- **In English**, for an athlete, not an analyst: what happened and what it means. Few
  numbers. No jargon: never "ACWR", "acute load", "chronic load", "AEROBIC_HIGH_SHORTAGE",
  "PRODUCTIVE_3", "OPTIMAL". Say it in plain words ("your training load is back in a healthy
  range", "almost no harder efforts").
- Exactly five sections, each a `## <Title>` heading followed by one short paragraph (at
  most about 80 words; `Next` has its own layout, below), in this order and with these exact titles — the same layout as the
  weekly report, so the Day page shows each section with its icon:
  - `## Training` — The training of the report's day (`sessions.today`), which is what the
    report is about: what it was, when (`start_time`), the minutes per effect from
    `effect_minutes`, Garmin's Training Effect, and what it trained. With more than one
    session, each in turn. If `sessions.today` is empty, the day had no training (so far, if
    `day` is today): say so, and how many days it has been since the last activity before
    it. The day before (`sessions.yesterday`) gets at most one clause of context, e.g. "after
    a rest day".
  - `## Recovery` — How ready was the body that morning? Readiness and what moves it, compared
    with its own averages; how many rest days and how long since the last hard session. Mention HRV, sleep
    and resting HR here only as readiness factors: their detail goes in Health.
  - `## Health` — Is my body OK, regardless of training? It catches early illness, accumulated
    stress or poor sleep. Compare each measure with its own averages, never with population
    norms. In this order: resting HR, HRV (the weekly average against `hrv_baseline`, not a
    single night), breathing rate during sleep, sleep (hours, score, short nights), stress
    and body battery, SpO2 (only if recorded; if it is in `missing`, one short clause). Every
    entry in `alerts` must be mentioned, with its numbers. If `alerts` is empty and nothing
    moved, say plainly "no warning signs".
  - `## Load` — Where the training load stands and which way it moved since `week_ago`, the
    balance between easy, hard and anaerobic work in plain words, and VO2max only if
    `vo2max_change` is present.
  - `## Next` — One concrete suggestion for the next session, with the reason from the
    paragraphs above and an example session (duration, structure, heart-rate target in bpm,
    taken from `hr_zones` — e.g. high aerobic work is `effects["High aerobic"]`; if
    `hr_zones` is `null`, name the zone instead of inventing bpm):
    a hard session, an easy one or rest. If the day already has its training
    (`trained_today` true), the suggestion is for **tomorrow**; if not, it is for the day
    itself.

    `Next` is laid out in three parts, because the Day page shows them apart (a title, the
    reason, and the steps of the session as chips):
    1. a title alone on the first line, in bold, a few words naming the session
       (`**High aerobic run**`, `**Easy ride**`, `**Rest day**`);
    2. a blank line, then one short paragraph with the reason (at most about 50 words);
    3. a blank line, then the steps of the example session as a bullet list, one step per
       bullet, each at most about 6 words (`- 15 min easy under 142 bpm`). For a rest day,
       one or two bullets (`- No training`, `- Walk if you like`).

    ```markdown
    ## Next

    **High aerobic run**

    Tomorrow, run at tempo: you recovered well and you are short on harder aerobic work.

    - 15 min easy under 142 bpm
    - 3 × 8 min at 143–154 bpm
    - 3 min easy jog between efforts
    - 10 min easy to cool down
    - Never above 155 bpm
    ```
- Header, exactly:

  ```markdown
  # Daily report — <day>

  Data: local cache, health up to <health_data_up_to>
  ```

  then the five sections:

  ```markdown
  ## Training

  ## Recovery

  ## Health

  ## Load

  ## Next
  ```

  The paragraph under each heading starts directly with the text (no bold label), except
  the title line of `Next`. No other headings, no tables.

- **Times of day** come from each session's `start_time`, never assumed: morning before
  12:00, afternoon 12:00–18:00, evening from 18:00. When in doubt, give the time ("the run at
  12:28") instead of a part of the day.

### Check before saving

1. The header and the five `##` sections (`Training`, `Recovery`, `Health`, `Load`,
   `Next`), with these exact titles, in this order.
2. Every number is in the JSON: nothing computed, nothing rounded differently.
3. Every entry of `alerts` is in Health; with `alerts` empty, no warning is invented.
4. Measures in `missing` are not commented as if they existed; averages on few `days` are
   called thin.
5. No jargon (see the list above).
6. Every "this morning / this afternoon / this evening" matches the session's `start_time`;
   with `trained_today` true, no sentence implies today is a rest day.
7. Every "in a row", "back-to-back", "after N rest days", "first … since" matches
   `consecutive_*_before_today` or `last_7_days`.
8. `Next` has its bold title line, the reason paragraph and the bullet list of steps.

## Step 3 — save the report (always, every time step 1 succeeded)

Save to `/home/andrea/dev/mygarmin/summary/01.daily/<day>.md`. That is the name the app's Day
page looks for.

One report per day: running it again overwrites the file. If the file already exists, Read it
first (required before Write can overwrite it), then Write the new version over it. Never
create a second file or append.

Before finishing, confirm that the Write call for this file actually happened in this turn —
do not report the report as saved unless it was. Then tell the user, in a line or two, which
day it covers and where it was saved, and give them the Next suggestion.
