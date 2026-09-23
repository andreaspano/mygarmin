"""Month page: monthly training totals, with a per-sport breakdown of the
month selected in the table.

La Week con un'unita' piu' larga: stessa macchina (period_page.py), stessa
disposizione, stessi comandi. Qui c'e' solo cosa vuol dire "mese"."""

import pandas as pd

from training.interface.period_page import PeriodSpec, render


def _bucket(start_time: pd.Series) -> pd.Series:
    """Ogni attivita' al primo del suo mese."""
    return start_time.dt.to_period("M").dt.start_time


def _label(period_start: pd.Timestamp) -> str:
    """Il mese per esteso e l'anno. Non un intervallo con due date come nella
    Week: un mese ha gia' un nome, e "September 2025" e' quello."""
    return f"{period_start:%B %Y}"


MONTH = PeriodSpec(
    name="month",
    title="Month",
    unit="month",
    adjective="Monthly",
    bucket=_bucket,
    # I mesi non sono lunghi uguali, quindi l'ultimo giorno lo chiede a pandas
    # invece di sommare giorni: `MonthEnd(0)` su un primo del mese porta alla
    # fine di *quel* mese, non del successivo.
    bucket_end=lambda starts: starts + pd.offsets.MonthEnd(0),
    freq="MS",
    label=_label,
    axis_format="%b",
    axis_interval="month",
    point_label=lambda period_start: period_start.dt.strftime("%b %Y"),
    # "Sep 2026" porta gia' l'anno: una riga "Starting 01 Sep 2026" non
    # aggiungerebbe niente.
    tooltip_start_format=None,
    # Un livello sopra il mese c'e' l'anno. La soglia e' piu' alta di quella
    # della Week perche' "2026" e' piu' largo di "Sep".
    boundary_freq="YS",
    boundary_format="%Y",
    boundary_min_share=0.07,
    column_header="Month",
    column_format="MMMM YYYY",
    column_width=145,
    column_help="First day of the month.",
    presets="months",
)

render(MONTH)
