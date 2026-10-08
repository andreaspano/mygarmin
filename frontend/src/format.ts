// Date e numeri come li scrive la pagina Day di Streamlit.
//
// I giorni restano stringhe "YYYY-MM-DD": `new Date("2026-10-07")` li legge
// in UTC, e intorno alla mezzanotte il giorno cambierebbe. Per i conti sui
// giorni si passa da `Date.UTC`, che non dipende dal fuso. Le ore dell'API
// sono locali e senza fuso ("2026-10-07T12:28:50"): si leggono dalla stringa.

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const DAY_MS = 24 * 60 * 60 * 1000;

function parts(day: string): [number, number, number] {
  const [y, m, d] = day.split("-").map(Number);
  return [y, m, d];
}

function utc(day: string): number {
  const [y, m, d] = parts(day);
  return Date.UTC(y, m - 1, d);
}

function fromUtc(ms: number): string {
  return new Date(ms).toISOString().slice(0, 10);
}

/** Oggi, nel fuso del browser. */
export function today(): string {
  const now = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

export function addDays(day: string, days: number): string {
  return fromUtc(utc(day) + days * DAY_MS);
}

/** I giorni da `end` a `start`, compresi, dal piu' recente. */
export function daysBetween(start: string, end: string): string[] {
  const days: string[] = [];
  for (let ms = utc(end); ms >= utc(start); ms -= DAY_MS) days.push(fromUtc(ms));
  return days;
}

/** "Wed 7 Oct 2026", come la colonna Date della tabella. */
export function dayLabel(day: string): string {
  const [y, m, d] = parts(day);
  return `${WEEKDAYS[new Date(utc(day)).getUTCDay()]} ${d} ${MONTHS[m - 1]} ${y}`;
}

/** Il giorno di un orario dell'API. */
export function dayOf(timestamp: string): string {
  return timestamp.slice(0, 10);
}

/** "12:28". */
export function timeOf(timestamp: string): string {
  return timestamp.slice(11, 16);
}

/** "07 Oct 2026, 12:28", come il titolo della scheda. */
export function dateTimeLabel(timestamp: string): string {
  const [y, m, d] = parts(dayOf(timestamp));
  return `${String(d).padStart(2, "0")} ${MONTHS[m - 1]} ${y}, ${timeOf(timestamp)}`;
}

/** L'arrotondamento di `round` di Python: a meta' strada, al pari. La
 * Streamlit lo usa per le durate, e `Math.round` darebbe un minuto in piu'
 * sui 30 secondi (todo 33, verifica 5). */
export function roundHalfEven(value: number): number {
  const floor = Math.floor(value);
  const diff = value - floor;
  if (diff > 0.5) return floor + 1;
  if (diff < 0.5) return floor;
  return floor % 2 === 0 ? floor : floor + 1;
}

/** Minuti in "hh:mm" (114 -> "01:54"), o "-". */
export function hm(minutes: number | null | undefined): string {
  if (minutes == null || Number.isNaN(minutes)) return "-";
  const total = roundHalfEven(minutes);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(Math.floor(total / 60))}:${pad(total % 60)}`;
}

/** Un numero con `digits` decimali, o "-" se manca. */
export function fixed(value: number | null | undefined, digits: number, suffix = ""): string {
  return value == null ? "-" : `${value.toFixed(digits)}${suffix}`;
}
