---
name: weekly-report
description: Writes the weekly report for one Monday-to-Sunday week — training, recovery and the four-week trend, in plain language for the athlete — from this repo's weekly-data script, and saves it to summary/02.weekly/<monday>.md, where the Week page shows it. Use when the user asks "how did my week go", for a "weekly report", or for a "report for the week of ..." (any week, past or current).
tools: Bash, Read, Write
---

This task has three mandatory steps, in order. Do not stop after step 2: saving the report
(step 3) is not optional and is not conditional on how the user phrased their question.

## Step 1 — get the data

Work out which week is wanted and translate it into its **Monday** (YYYY-MM-DD):

- nothing specific, "my week", "last week" → no `--week` argument: the script takes the last
  **closed** week (the one before the current week);
- "this week" → the Monday of the current week (the week will be partial);
- "the week of 21 September" or any date → the Monday of the week containing that date.

Then run:

```bash
cd /home/andrea/dev/mygarmin && uv run training-weekly-data [--week YYYY-MM-DD]
```

`--week` must be a Monday: a different day is an error, not rounded. The script reads only
local data; it never calls Garmin. If the command fails, say so plainly with the error and
stop: no data means nothing to write and nothing to save.

The JSON:

- `week`: `start` (Monday), `end` (Sunday), `partial` (the week isn't over yet) and
  `last_day` (the last day with data, today for a partial week).
- `health_days`: days with sleep recorded, i.e. days the watch was worn. Goes in the header.
- `activities`: one row per activity — date, weekday, start time, sport, name, distance,
  duration (minutes), ascent, average and max heart rate.
- `days`: the 7 days, each with its activities (or none) and that **morning's** recovery
  values (readiness, resting HR, HRV of the night, sleep hours and score, stress, body
  battery). `future: true` marks days after `last_day`. `sleep_night` spells out which night
  the sleep belongs to.
- `training`: sessions and total time, then sessions, time, distance and ascent **per sport**,
  active days, and the names of the rest days.
- `load`: Garmin's training load from the last day of the week that has it (`as_of`): acute
  and chronic load, their ratio (`acwr`) and its status, training status, load balance and
  Garmin's phrase for it. `null` if Garmin has none.
- `vo2max`: the VO2max measurements taken during the week (date, value).
- `coverage`: **per metric**, how many of the 7 days have a value.
- `four_weeks`: this week and the three before it (oldest first), with the same totals,
  recovery averages (each with the number of days it is based on: `mean` is `null` on zero
  days), end-of-week acute load and the latest VO2max.

## Step 2 — write the report

The facts always come from the JSON. The example at the bottom shows tone and length only:
never copy its facts.

### Format

- **In English.**
- **For an athlete, not an analyst**: tell what happened and what it means. Few numbers — the
  tables and charts in the app carry those. No jargon: never "ACWR", "acute load", "chronic
  load", "aerobic-high shortage", "PRODUCTIVE_3", "OPTIMAL". Say it in plain words ("your
  training load is back in a healthy range", "almost no harder efforts").
- Exactly this header, then three sections, in this order, with these exact titles:

  ```markdown
  # Weekly report — <start> to <end>

  Week: <start> to <end> · Health data: <health_days>/7 days

  ## Training

  ## Recovery

  ## Trend
  ```

  For a partial week the `Week:` line reads
  `Week: <start> to <end> (partial, up to <last_day>) · Health data: <health_days>/7 days`,
  and the text says the week isn't over: no "the whole week", no verdict on days that haven't
  happened.
- **Training**: the sessions, how they are spread through the week, the intensity, the load
  compared with the week before. Never add distances (or ascent) across different sports:
  running, cycling and walking kilometres don't sum to anything meaningful.
- **Recovery**: readiness, resting heart rate, HRV, sleep, stress — how the body responded day
  by day.
- **Trend**: the last four weeks — what is rising, what is falling, what is stable. Small
  changes are noise and are said to be noise.
- Two or three short paragraphs per section, like the example.
- **No** plans, no suggestions for next week, no "next week" at all, no references to
  `summary/05.plan/`, no tables.

### Check before saving

Go through your draft and fix it before step 3:

1. The header and the three sections, with the exact titles, in order.
2. No plans, no "next week", no tables, no jargon (see the list above).
3. **Every calendar statement** ("the long run on Friday", "rest days on Tuesday and
   Thursday", "back to back", "the biggest outing") checked against `days` and `activities`.
4. **Nights**: Garmin files a night's sleep under the morning you wake up. The sleep dated
   Monday is the night between Sunday and Monday: write "the night going into Monday", never
   "Monday night" (use `sleep_night`).
5. **Coverage**: a metric with few days in `coverage` is not commented as if it were the whole
   week — say the data is thin ("the watch was only worn on one night"). Readiness and load
   exist even without the watch; HRV, sleep, resting HR and stress do not. A week with no
   health data at all: Recovery says there is no data, and Trend compares only what exists.
   In `four_weeks`, an average based on one or two days is not compared with full weeks as
   if it were equivalent.

## Step 3 — save the report (always, every time step 1 succeeded)

Save to `/home/andrea/dev/mygarmin/summary/02.weekly/<week.start>.md` (the Monday). That is
the name the app's Week page looks for.

One report per week: running it again overwrites the file. If the file already exists, Read
it first (required before Write can overwrite it), then Write the new version over it. Never
create a second file or append.

Before finishing, confirm that the Write call for this file actually happened in this turn —
do not report the report as saved unless it was. Then tell the user, in a line or two, which
week it covers and where it was saved.

## Example (tone and length only — the facts come from the JSON)

```markdown
# Weekly report — 2026-09-21 to 2026-09-27

Week: 2026-09-21 to 2026-09-27 · Health data: 7/7 days

## Training

A well-balanced week: three runs and two road rides, with two
rest days placed so that no two demanding days came back to back. Friday's run
was the longest of the week and Sunday's ride the biggest outing, with an easy
run in between. Wednesday's ride was a gentle recovery spin. Everything stayed
comfortable and aerobic: there was no really hard effort anywhere.

After the hilly, demanding week before, this one was lighter, and it brought
your training load back into a healthy range. The one thing missing over the
past month is harder work. Almost all of your training is easy, and Garmin
also notes the shortage of tempo or faster efforts.

## Recovery

You started the week tired. Monday's readiness was very low, the
clear echo of the previous hilly weekend, and the night going into Monday was
the poorest sleep of the week. From there your body bounced back steadily: by
Thursday you were fully fresh, and you stayed in good shape through the
weekend. Resting heart rate went down day by day, ending the week at its
lowest, a good sign that the fatigue had cleared. Heart rate variability was
in your normal range every night.

Sleep was good overall. There were a couple of shorter nights (Tuesday and
Friday), but they didn't knock you back, and a long, restful Saturday night
closed the week well. Day-to-day stress stayed low.

## Trend

The month tells a clear story: a gradual build, one big
hilly week that pushed you hard, and this week to absorb it. Your body handled
the cycle well: you dipped after the big week, but recovered within a few days.
Resting heart rate has stayed steady all month.

Your VO2max has been creeping up a little each week. Each step is small, but
the direction is consistent, and it fits a growing aerobic base. Heart rate
variability is a touch lower than in early September, but it has been stable
for the last three weeks, so it is something to keep an eye on rather than a
concern.

The first week of September is hard to compare: the watch wasn't worn for most
of it.
```
