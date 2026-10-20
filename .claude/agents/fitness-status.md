---
name: fitness-status
description: Points at the machinery that writes the daily report. Since todo 44 the report is written section by section by seven agents (01_health, 02_load, 03_recovery, 04_fitness, 05_training, then 06_next and 07_summary), run one after another by `make daily_report` or by the Refresh button on the Day page. Use when the user asks for their daily report, their fitness status, or what to train today.
tools: Bash, Read
---

The daily report is no longer written by one agent. Since todo 44 each
section has its own — `01_health`, `02_load`, `03_recovery`, `04_fitness`,
`05_training`, and then `06_next` and `07_summary`, which read what the
others concluded — and each writes its own file in
`summary/01.daily/<day>/`. The rules they share are in `_style.md`.

To produce the report, run the whole pipeline, which downloads new data,
prepares the facts once and runs the seven agents in order:

```bash
make daily_report [DAY=YYYY-MM-DD]
```

It prints how each section went. A section that fails keeps the text it had,
and the others are still rewritten; `make daily_report SECTION=health` redoes
just one. Add `--no-update` through `make daily_report` only if you want the
text rewritten without calling Garmin.

Then tell the user how it went and, if they asked for the content, read the
files back to them from `summary/01.daily/<day>/`.

Do not write any section yourself: each belongs to its agent, and a report
written here would be overwritten by the next run and would not follow the
house rules the seven share.
