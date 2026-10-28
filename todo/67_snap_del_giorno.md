---
status: done
---

# Il Report del giorno si chiama Snap

La prima vista della Day si chiamava **Report**, quella della Week **Snap**.
Dal todo 66 le due mostrano la stessa cosa — il verdetto in cima e le card
delle misure, col testo dentro — e il nome giusto era gia' stato scelto una
volta, per la Week.

## Perche' Snap, come diceva il todo 59

Il todo 59 spiegava la scelta: quella vista **non e' un documento**. Sono i
numeri con le loro fasce, le sedute, il grafico, e il report sta *dentro* le
card. E' l'istantanea del periodo com'e' andato, non il report. Sotto Day
valeva anche prima — le quattro card sono misure, non prosa — e dal todo 66
vale di piu': il report del giorno adesso e' sparso fra due pagine, il corpo
qui e la seduta nella Training, quindi chiamare "Report" una delle due e'
proprio il nome sbagliato.

## La chiave e' la stessa della Week

`snap` esisteva gia' come vista, quella della Week. Il giorno prende **la
stessa chiave**, non una nuova: `VIEWS.day = ["snap", "training", "trend"]`
accanto a `VIEWS.week = ["snap", "trend", "plan"]`. Due conseguenze, tutte e
due volute:

- **lo Snap e' la vista di partenza di tutti e due i periodi**, quindi
  `?day=...` e `?period=week` nudi aprono l'istantanea, come prima;
- **cambiando periodo si resta sull'istantanea**: `vistaSu` in `TopBar` porta
  la vista dove quel periodo ce l'ha, e lo Snap ce l'hanno entrambi. Prima da
  Week/Snap si cadeva su Day/Report, che era la stessa cosa con un altro
  nome.

`report` sparisce dall'unione `View`. I link vecchi con `?view=report` non si
rompono: `viewFromUrl` valida contro `VIEWS[page]` e, non trovandola, ricade
sulla vista di partenza — che e' la stessa pagina.

## Work

- `navigation.ts`: `View` senza `report`, `VIEWS.day` con `snap` in testa,
  `ETICHETTE` senza la voce di troppo, e i commenti.
- `DayPage.tsx` e `TopBar.tsx`: il valore di partenza della prop e i tre
  confronti `view === "snap"`.
- I commenti che nominavano il Report, anche in `TrendPanels.tsx` (il clic su
  un punto apre lo Snap di quel giorno).
- `README.md`: le viste, l'URL, e una riga che dice come si chiamava prima.

## Verifica

Fatta in Firefox headless, leggendo il menu e le card dal DOM:

| url | menu | card |
|---|---|---|
| `?` nudo | `Snap* Training Trend` | Summary (oggi, senza report) |
| `?day=2026-10-27` | `Snap* Training Trend` | Summary, Health, Load, Recovery, Fitness |
| `?day=...&view=snap` | `Snap*` | le stesse cinque |
| `?day=...&view=report` | `Snap*` | le stesse cinque — il link vecchio regge |
| `?day=...&view=training` | `Training*` | Plan, Session, Comment |
| `?period=week` | `Snap* Trend Plan` | la Week invariata |

Il titolo della scheda non nomina lo Snap, che e' la vista di partenza
(`Training · 2026-10-27`), e lo nomina per le altre
(`Training · 2026-10-27 · Training`). Da Day/Snap il collegamento alla Week e'
`?day=2026-10-27&period=week`, senza `view`: lo Snap e' la partenza anche la',
quindi la vista viaggia senza che il parametro debba comparire.

`npm run typecheck` e `npm run build` puliti.

## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_67'$" --format=%H -1)
```

Effetti fuori dal repo: nessuno. E' un rinominare: niente scritture, niente
chiamate a Garmin, nessun dato toccato. I link con `?view=snap` scritti nel
frattempo, dopo il revert, ricadrebbero sul Report — di nuovo la stessa
pagina con l'altro nome.

Dopo il revert, rifare il merge di `todo_67` non riporta le modifiche (git le
considera gia' unite): per riaverle serve il revert del revert.
