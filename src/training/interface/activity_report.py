"""Report rule-based per singola attivita': un commento testuale derivato
solo dai dati campionati (nessuna chiamata esterna/LLM). Usato sia
dall'app Streamlit (mostrato nel dettaglio attivita') sia dallo script
batch che scrive un file .md per attivita' in summary/00.activity/.
"""

from pathlib import Path

import pandas as pd

from training.interface.db import list_activities, load_activity_records

OUT_DIR = Path("summary/00.activity")


def activity_comments(records: pd.DataFrame) -> list[str]:
    """Commento automatico rule-based sulla singola attivita', basato solo
    sui dati campionati (nessuna chiamata esterna): confronta prima e
    seconda meta' per ritmo/FC, mette in relazione FC e pendenza, e
    valuta la regolarita' della cadenza."""
    comments = []

    has_distance = records["distance_km"].notna().any() and records["distance_km"].max() > 0
    speed1 = speed2 = hr1 = hr2 = None
    if has_distance:
        half_distance = records["distance_km"].max() / 2
        first_half = records[records["distance_km"] <= half_distance]
        second_half = records[records["distance_km"] > half_distance]

        speed1, speed2 = first_half["speed_kmh"].mean(), second_half["speed_kmh"].mean()
        if pd.notna(speed1) and pd.notna(speed2) and speed1 > 0:
            delta_pct = (speed2 - speed1) / speed1 * 100
            if delta_pct >= 5:
                comments.append(
                    f"Negative split: average speed {delta_pct:.0f}% higher in the second "
                    f"half ({speed2:.1f} km/h vs {speed1:.1f} km/h) — good pacing."
                )
            elif delta_pct <= -5:
                comments.append(
                    f"Positive split: average speed {abs(delta_pct):.0f}% lower in the second "
                    f"half ({speed2:.1f} km/h vs {speed1:.1f} km/h) — likely pace drop-off."
                )
            else:
                comments.append(
                    f"Steady pace between first and second half ({speed1:.1f} vs {speed2:.1f} km/h)."
                )

        hr1, hr2 = first_half["heart_rate"].mean(), second_half["heart_rate"].mean()
        if pd.notna(hr1) and pd.notna(hr2) and hr1 > 0:
            hr_delta_pct = (hr2 - hr1) / hr1 * 100
            if hr_delta_pct >= 5:
                comments.append(
                    f"Cardiac drift: average HR +{hr_delta_pct:.0f}% in the second half "
                    f"({hr1:.0f} → {hr2:.0f} bpm) — possible fatigue or heat."
                )
            elif hr_delta_pct <= -5:
                comments.append(
                    f"Average HR dropped in the second half ({hr1:.0f} → {hr2:.0f} bpm) — good recovery."
                )

    if (
        records["altitude_m"].notna().any()
        and has_distance
        and records["heart_rate"].notna().any()
    ):
        altitude_diff = records["altitude_m"].astype(float).diff()
        distance_diff_m = (records["distance_km"].astype(float).diff() * 1000).mask(lambda s: s == 0)
        slope_pct = ((altitude_diff / distance_diff_m) * 100).clip(-30, 30)
        uphill_hr = records.loc[slope_pct > 3, "heart_rate"].mean()
        flat_hr = records.loc[slope_pct.between(-1, 1), "heart_rate"].mean()
        if pd.notna(uphill_hr) and pd.notna(flat_hr) and (uphill_hr - flat_hr) >= 5:
            comments.append(
                f"Uphill (slope > 3%) average HR rises to {uphill_hr:.0f} bpm vs "
                f"{flat_hr:.0f} bpm on flat ground (+{uphill_hr - flat_hr:.0f} bpm)."
            )

    if records["cadence"].notna().any():
        cadence = records["cadence"].dropna()
        cadence_mean = cadence.mean()
        cadence_cv = (cadence.std() / cadence_mean * 100) if cadence_mean else None
        if cadence_cv is not None:
            if cadence_cv <= 5:
                comments.append(
                    f"Very steady cadence (mean {cadence_mean:.0f}, variation {cadence_cv:.0f}%)."
                )
            elif cadence_cv >= 15:
                comments.append(
                    f"Fairly variable cadence (mean {cadence_mean:.0f}, variation {cadence_cv:.0f}%)."
                )

    if not comments:
        comments.append("Not enough data for an automatic comment on this activity.")

    return comments


def build_activity_report_markdown(activity: pd.Series, records: pd.DataFrame) -> str:
    ascent = (
        f"+{activity.total_ascent_m:.0f} / -{activity.total_descent_m:.0f} m"
        if pd.notna(activity.total_ascent_m)
        else "-"
    )
    lines = [
        f"# {activity.sport or '?'} — {activity.start_time:%d %b %Y, %H:%M}",
        "",
        f"- Activity ID: {activity.activity_id}",
        f"- Distance: {activity.total_distance_km:.1f} km",
        f"- Duration: {activity.total_time_min:.0f} min",
        f"- Avg HR: {activity.avg_heart_rate or '-'} bpm",
        f"- Elevation: {ascent}",
        "",
        "## Comment",
        "",
    ]
    lines.extend(f"- {comment}" for comment in activity_comments(records))
    return "\n".join(lines) + "\n"


def load_activity_comments(activity_id: int, out_dir: Path = OUT_DIR) -> list[str] | None:
    """Legge i commenti dal report .md gia' salvato per questa attivita'
    (nessun ricalcolo). None se il report non e' ancora stato generato."""
    path = Path(out_dir) / f"{activity_id}.md"
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    if "## Comment" not in text:
        return []
    section = text.split("## Comment", 1)[1]
    return [line[2:].strip() for line in section.splitlines() if line.startswith("- ")]


def generate_activity_reports(data_dir: Path = Path("data"), out_dir: Path = OUT_DIR) -> list[Path]:
    """Genera un file .md per ogni attivita' non ancora presente in out_dir
    (nominato per activity_id). Un'attivita' passata non cambia, quindi un
    report gia' scritto non viene mai rigenerato. Ritorna i path scritti."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    activities = list_activities(data_dir)
    written = []
    for _, activity in activities.iterrows():
        path = out_dir / f"{activity.activity_id}.md"
        if path.exists():
            continue
        records = load_activity_records(activity.activity_id, data_dir)
        if records.empty:
            continue
        report = build_activity_report_markdown(activity, records)
        path.write_text(report, encoding="utf-8")
        written.append(path)
    return written


def main() -> None:
    written = generate_activity_reports()
    print(f"Scritti {len(written)} report in {OUT_DIR}/")


if __name__ == "__main__":
    main()
