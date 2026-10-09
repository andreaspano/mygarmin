// Le chiamate all'API (todo 32), una funzione per endpoint. I tipi vengono
// da `schema.ts`, generato dall'OpenAPI con `npm run gen:api`: qui non si
// scrive a mano nessun tipo di risposta.
import type { components } from "./schema";

type Schemas = components["schemas"];
export type Activity = Schemas["Activity"];
export type ActivityDetail = Schemas["ActivityDetail"];
export type DailyData = Schemas["DailyData"];
export type Measure = Schemas["Measure"];
export type Report = Schemas["Report"];
export type ReportSection = Schemas["ReportSection"];
export type Route = Schemas["Route"];
export type Sport = Schemas["Sport"];
export type SportList = Schemas["SportList"];

// La specifica Vega-Lite del grafico non ha un modello: e' quella di Altair.
export type VegaSpec = Record<string, unknown>;

export class ApiError extends Error {
  constructor(
    readonly status: number,
    url: string,
  ) {
    super(`${url}: HTTP ${status}`);
  }
}

async function getJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(url, { signal });
  if (!response.ok) throw new ApiError(response.status, url);
  return (await response.json()) as T;
}

// Per gli endpoint dove il 404 vuol dire "non c'e'" (il report di un giorno,
// il grafico di un'attivita' senza dati), non un errore.
async function getOrNull<T>(url: string, signal?: AbortSignal): Promise<T | null> {
  try {
    return await getJson<T>(url, signal);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

export function iconUrl(file: string): string {
  return `/icons/${encodeURIComponent(file)}`;
}

export const api = {
  sports: (signal?: AbortSignal) => getJson<SportList>("/api/sports", signal),

  activities: (start: string, end: string, sports: string[], signal?: AbortSignal) => {
    const params = new URLSearchParams({ start, end });
    for (const sport of sports) params.append("sport", sport);
    return getJson<Activity[]>(`/api/activities?${params}`, signal);
  },

  activity: (id: number, signal?: AbortSignal) => getJson<ActivityDetail>(`/api/activities/${id}`, signal),

  chartVega: (id: number, theme: "light" | "dark", signal?: AbortSignal) =>
    getOrNull<VegaSpec>(`/api/activities/${id}/chart/vega?theme=${theme}`, signal),

  route: (id: number, signal?: AbortSignal) => getJson<Route>(`/api/activities/${id}/route`, signal),

  daily: (day: string, signal?: AbortSignal) => getJson<DailyData>(`/api/daily/${day}`, signal),

  dailyReport: (day: string, signal?: AbortSignal) => getOrNull<Report>(`/api/reports/daily/${day}`, signal),
};
