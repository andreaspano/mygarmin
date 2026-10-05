"""Pendenza e velocita' equivalente in piano, dai record di un'attivita'.

La velocita' equivalente e' quella che in piano costerebbe la stessa energia
spesa sulla pendenza reale: serve a confrontare uscite con dislivelli diversi.

Il costo viene da Minetti et al. 2002, "Energy cost of walking and running at
extreme uphill and downhill slopes" (J Appl Physiol 93:1039-1046): il
polinomio del costo della corsa in J/kg/m, con la pendenza come frazione,
valido fra -45% e +45%. E' misurato in laboratorio sulla corsa: per camminata
ed escursione e' un'approssimazione. In salita e' piu' severo del GAP di
Strava (che e' tarato sulla frequenza cardiaca), quindi i numeri non
coincidono con quelli di Strava.
"""

import numpy as np
import pandas as pd

# Gli sport per cui il modello ha senso: la bici dipende soprattutto
# dall'aria e lo sci dalla neve, e li' la cella resta vuota.
EQUIV_SPEED_SPORTS = {"running", "hiking", "walking"}

# L'intervallo in cui Minetti ha misurato il polinomio: fuori si estrapola.
_MODEL_SLOPE_LIMIT_PCT = 45
_FLAT_COST = 3.6


def slope_pct(records: pd.DataFrame) -> pd.Series:
    """La pendenza in percentuale, campione per campione, senza clip.

    Dislivello diviso distanza fra due campioni consecutivi; dove la distanza
    non cambia (fermi) la pendenza e' NaN invece di un infinito. La media
    mobile di 30s centrata toglie il grosso del rumore dell'altimetro. La clip
    la fa chi chiama: il modello e il grafico vogliono limiti diversi."""
    altitude_diff_m = records["altitude_m"].astype(float).diff()
    distance_diff_m = (records["distance_km"].astype(float).diff() * 1000).mask(lambda s: s == 0)
    raw = (altitude_diff_m / distance_diff_m) * 100
    return raw.rolling("30s", min_periods=1, center=True).mean()


def minetti_cost(i):
    """Il costo energetico della corsa (J/kg/m) alla pendenza `i` (frazione)."""
    return 155.4 * i**5 - 30.4 * i**4 - 43.3 * i**3 + 46.3 * i**2 + 19.5 * i + _FLAT_COST


def _cost_factor(records: pd.DataFrame) -> pd.Series:
    """Il costo di ogni campione relativo alla pianura (1 = come in piano).

    Dove la pendenza non si sa (quota mancante in quel tratto) il campione
    vale come in piano: meglio che buttarlo."""
    limit = _MODEL_SLOPE_LIMIT_PCT
    slope = slope_pct(records).clip(-limit, limit) / 100
    return (minetti_cost(slope) / _FLAT_COST).fillna(1.0)


def equivalent_speed_series(records: pd.DataFrame) -> pd.Series:
    """La velocita' equivalente in piano campione per campione, in km/h.

    Grezza, non lisciata: il rumore dell'altimetro passa nel fattore, e la
    media mobile la fa chi la disegna. Una media nel tempo di questa serie e'
    vicina ma non uguale a `equivalent_speed_kmh`, che pesa i tratti per la
    distanza e parte dalla velocita' media di Garmin."""
    return records["speed_kmh"].astype(float) * _cost_factor(records)


def equivalent_speed_kmh(records: pd.DataFrame, avg_speed_kmh: float | None) -> float | None:
    """La velocita' equivalente in piano dell'attivita', in km/h, o None.

    Si sommano i tratti di distanza pesati per il costo relativo alla
    pianura: il rapporto fra la distanza equivalente e quella vera e' il
    fattore che porta `avg_speed_kmh` in piano. Si moltiplica la velocita'
    media dell'attivita' invece di ridividere per un tempo in movimento
    stimato dai record: il divisore resta quello di Garmin (vedi
    `fit._avg_speed_kmh`), e in piano le due velocita' coincidono. Pesare per
    la distanza fa contare ogni tratto per quanto e' lungo; le soste (distanza
    ferma) non pesano. Senza quota, distanza o velocita' media non c'e'
    valore."""
    if (
        avg_speed_kmh is None
        or pd.isna(avg_speed_kmh)
        or records.empty
        or records["altitude_m"].isna().all()
    ):
        return None

    distance_diff_m = (records["distance_km"].astype(float).diff() * 1000).clip(lower=0)
    total_m = float(np.nansum(distance_diff_m))
    if total_m <= 0:
        return None

    equivalent_m = float(np.nansum(distance_diff_m * _cost_factor(records)))
    return avg_speed_kmh * equivalent_m / total_m
