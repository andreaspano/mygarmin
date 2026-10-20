"""Report rule-based per singola attivita': un commento testuale derivato
solo dai dati campionati (nessuna chiamata esterna/LLM). Lo usa lo script
batch che scrive un file .md per attivita' in summary/00.activity/.
"""

from pathlib import Path

import pandas as pd

from training.garmin.config import DATA_DIR
from training.interface.db import list_activities, load_activity_records
from training.interface.sports import has_distance

OUT_DIR = Path("summary/00.activity")


# Le grandezze che dicono come e' stata corsa una seduta. Stanno qui perche'
# le frasi di questo report ci sono nate sopra, ma le legge anche
# `daily_data`, che le mette nel JSON del giorno (todo 43): il conto e' uno
# solo, e le due strade non possono piu' divergere.
_NUMBER_KEYS = (
    "speed_first_half_kmh",
    "speed_second_half_kmh",
    "speed_change_pct",
    "hr_first_half",
    "hr_second_half",
    "hr_change_pct",
    "cadence_mean",
    "cadence_variation_pct",
    "uphill_hr",
    "flat_hr",
)


# Le sole grandezze qui sopra che la distanza non la toccano: le due meta'
# sono meta' *di distanza*, quindi dove la distanza e' una stima del polso
# (il tapis roulant, todo 45) cade anche il confronto dei battiti, che non
# sarebbe fatto a meta' seduta ma in un punto deciso dalla stima.
NUMBERS_WITHOUT_DISTANCE = ("cadence_mean", "cadence_variation_pct")


def activity_numbers(records: pd.DataFrame) -> dict[str, float | None]:
    """Come e' stata corsa la seduta, in numeri: le medie della prima e della
    seconda meta' (per distanza) con la differenza in percento, la cadenza
    con la sua variabilita', e i battiti in salita contro quelli in piano.

    Grezzi, non arrotondati: `activity_comments()` ci scrive sopra le sue
    frasi e `daily_data` li arrotonda per il JSON, ognuno con i suoi
    decimali. `None` dove il dato non c'e' o non si puo' ricavare."""
    out: dict[str, float | None] = dict.fromkeys(_NUMBER_KEYS)

    has_distance = records["distance_km"].notna().any() and records["distance_km"].max() > 0
    if has_distance:
        half_distance = records["distance_km"].max() / 2
        first_half = records[records["distance_km"] <= half_distance]
        second_half = records[records["distance_km"] > half_distance]

        speed1, speed2 = first_half["speed_kmh"].mean(), second_half["speed_kmh"].mean()
        if pd.notna(speed1) and pd.notna(speed2) and speed1 > 0:
            out["speed_first_half_kmh"] = float(speed1)
            out["speed_second_half_kmh"] = float(speed2)
            out["speed_change_pct"] = (speed2 - speed1) / speed1 * 100

        hr1, hr2 = first_half["heart_rate"].mean(), second_half["heart_rate"].mean()
        if pd.notna(hr1) and pd.notna(hr2) and hr1 > 0:
            out["hr_first_half"] = float(hr1)
            out["hr_second_half"] = float(hr2)
            out["hr_change_pct"] = (hr2 - hr1) / hr1 * 100

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
        if pd.notna(uphill_hr):
            out["uphill_hr"] = float(uphill_hr)
        if pd.notna(flat_hr):
            out["flat_hr"] = float(flat_hr)

    if records["cadence"].notna().any():
        cadence = records["cadence"].dropna()
        cadence_mean = cadence.mean()
        if pd.notna(cadence_mean) and cadence_mean:
            variation = cadence.std() / cadence_mean * 100
            out["cadence_mean"] = float(cadence_mean)
            out["cadence_variation_pct"] = float(variation) if pd.notna(variation) else None

    return out


def activity_comments(records: pd.DataFrame, sport: str | None = None) -> list[str]:
    """Commento automatico rule-based sulla singola attivita', basato solo
    sui dati campionati (nessuna chiamata esterna): confronta prima e
    seconda meta' per ritmo/FC, mette in relazione FC e pendenza, e
    valuta la regolarita' della cadenza.

    I numeri li da' `activity_numbers()`; qui si scelgono le soglie e le
    parole. Degli sport senza distanza (il tapis roulant, todo 45) resta la
    sola cadenza: le due meta' sono meta' di distanza, e li' la distanza la
    indovina il polso."""
    numbers = activity_numbers(records)
    if not has_distance(sport):
        numbers = {
            name: (value if name in NUMBERS_WITHOUT_DISTANCE else None)
            for name, value in numbers.items()
        }
    comments = []

    delta_pct = numbers["speed_change_pct"]
    if delta_pct is not None:
        speed1 = numbers["speed_first_half_kmh"]
        speed2 = numbers["speed_second_half_kmh"]
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

    hr_delta_pct = numbers["hr_change_pct"]
    if hr_delta_pct is not None:
        hr1, hr2 = numbers["hr_first_half"], numbers["hr_second_half"]
        if hr_delta_pct >= 5:
            comments.append(
                f"Cardiac drift: average HR +{hr_delta_pct:.0f}% in the second half "
                f"({hr1:.0f} → {hr2:.0f} bpm) — possible fatigue or heat."
            )
        elif hr_delta_pct <= -5:
            comments.append(
                f"Average HR dropped in the second half ({hr1:.0f} → {hr2:.0f} bpm) — good recovery."
            )

    uphill_hr, flat_hr = numbers["uphill_hr"], numbers["flat_hr"]
    if uphill_hr is not None and flat_hr is not None and (uphill_hr - flat_hr) >= 5:
        comments.append(
            f"Uphill (slope > 3%) average HR rises to {uphill_hr:.0f} bpm vs "
            f"{flat_hr:.0f} bpm on flat ground (+{uphill_hr - flat_hr:.0f} bpm)."
        )

    cadence_cv = numbers["cadence_variation_pct"]
    if cadence_cv is not None:
        cadence_mean = numbers["cadence_mean"]
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
    ]
    # Gli sport senza distanza (il tapis roulant) non la dichiarano: al suo
    # posto le calorie, che li' sono la misura onesta dello sforzo.
    if has_distance(activity.sport):
        lines.append(f"- Distance: {activity.total_distance_km:.1f} km")
    elif pd.notna(activity.total_calories):
        lines.append(f"- Calories: {activity.total_calories:.0f} kcal")
    lines += [
        f"- Duration: {activity.total_time_min:.0f} min",
        f"- Avg HR: {activity.avg_heart_rate or '-'} bpm",
        f"- Elevation: {ascent}",
        "",
        "## Comment",
        "",
    ]
    lines.extend(f"- {comment}" for comment in activity_comments(records, activity.sport))
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


def generate_activity_reports(data_dir: Path = DATA_DIR, out_dir: Path = OUT_DIR) -> list[Path]:
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
