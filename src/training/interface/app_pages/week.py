"""Week page: weekly training totals, with a per-sport breakdown of the
week(s) selected in the table.

La macchina sta in period_page.py, condivisa con la pagina Month: qui c'e' solo
cosa vuol dire "settimana"."""

import pandas as pd

from training.interface.period_page import PeriodSpec, render


def _bucket(start_time: pd.Series) -> pd.Series:
    """Ogni attivita' al lunedi' della sua settimana: e' la chiave con cui
    raggruppiamo (e anche l'etichetta mostrata all'utente)."""
    return (start_time - pd.to_timedelta(start_time.dt.weekday, unit="D")).dt.normalize()


def _label(period_start: pd.Timestamp) -> str:
    """L'intervallo della settimana, con il trattino medio degli intervalli:
    quello lungo separa le frasi nei sottotitoli, e i due ruoli non vanno
    confusi ora che compaiono nella stessa riga."""
    return f"{period_start:%d %b %Y} – {period_start + pd.Timedelta(days=6):%d %b %Y}"


def _point_label(period_start: pd.Series) -> pd.Series:
    """Il numero di settimana ISO, w01..w53: e' quello che l'asse mostra, e nel
    tooltip fa da riscontro."""
    return "w" + period_start.dt.isocalendar().week.astype(int).map("{:02d}".format)


WEEK = PeriodSpec(
    name="week",
    title="Week",
    unit="week",
    adjective="Weekly",
    bucket=_bucket,
    bucket_end=lambda starts: starts + pd.Timedelta(days=6),
    freq="W-MON",
    label=_label,
    axis_format="w%V",
    axis_interval="week",
    point_label=_point_label,
    # "w38" non dice l'anno: la riga "Starting" lo aggiunge.
    tooltip_start_format="%d %b %Y",
    # Sull'asse a settimane il riferimento utile e' il mese: senza, "w31" non
    # dice a nessuno che e' fine luglio.
    boundary_freq="MS",
    boundary_format="%b",
    boundary_min_share=0.04,
    column_header="Week",
    column_format="D MMM YYYY",
    column_width=130,
    column_help="Monday that opens the week (Mon-Sun).",
    presets="weeks",
)

render(WEEK)
