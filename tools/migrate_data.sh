#!/usr/bin/env bash
# Il trasloco dei dati nella cartella sola del todo 65.
#
# Da `~/adrive/data/garmin-export`, dove FIT, JSON, salute e database stavano
# piatti insieme, e dal repo, dove stavano `summary/`, `plan/` e `user/`, a
# sette cartelle sotto una radice sola.
#
# Si lancia una volta. Di suo **non fa niente**: stampa quello che farebbe e
# si ferma. Serve `--go` per muovere i file.
#
#   tools/migrate_data.sh                 # il giro a vuoto
#   tools/migrate_data.sh --go            # il trasloco
#
# Non cancella niente, e **non tocca i file `.conflict1`/`.conflict2`** che la
# sincronizzazione ha lasciato nella cartella vecchia: restano dove sono,
# perche' vanno guardati e non spazzati via (uno di loro ha 971 nomi di
# attivita' contro i 15 del file vivo).
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OLD="${OLD:-$HOME/adrive/data/garmin-export}"
NEW="${NEW:-$HOME/adrive/data/training}"

GO=0
[ "${1:-}" = "--go" ] && GO=1
if [ "$GO" = 0 ]; then
  echo "=== GIRO A VUOTO: non muovo niente. Con --go lo faccio davvero. ==="
fi
echo "da:    $OLD"
echo "e da:  $REPO"
echo "a:     $NEW"
echo

run() {
  if [ "$GO" = 1 ]; then
    "$@"
  else
    echo "    $*"
  fi
}

# Quanti file muoveremmo, per sapere se il conto torna dopo.
count() { find "$1" -maxdepth 1 -name "$2" 2>/dev/null | wc -l; }

echo "1. le sette cartelle"
for dir in fit health json db user summary plan; do
  run mkdir -p "$NEW/$dir"
done

echo "2. i FIT  ($(count "$OLD" '*_ACTIVITY.fit') file)"
if [ "$GO" = 1 ]; then
  find "$OLD" -maxdepth 1 -name '*_ACTIVITY.fit' -exec mv -n -t "$NEW/fit/" {} +
else
  echo "    mv $OLD/*_ACTIVITY.fit -> $NEW/fit/"
fi

echo "3. i quattro JSON"
for f in activity_names.json activity_types.json activity_terrain.json activity_run_type.json; do
  [ -f "$OLD/$f" ] && run mv -n "$OLD/$f" "$NEW/json/$f"
done

echo "4. il database"
[ -f "$OLD/activities.db" ] && run mv -n "$OLD/activities.db" "$NEW/db/activities.db"
# Il WAL e l'indice, se ci sono: senza di loro sqlite riaprirebbe un database
# a cui manca l'ultima transazione.
for ext in -wal -shm; do
  [ -f "$OLD/activities.db$ext" ] && run mv -n "$OLD/activities.db$ext" "$NEW/db/activities.db$ext"
done

echo "5. la salute (una cartella sola, gia' nella forma giusta)"
if [ -d "$OLD/health" ]; then
  if [ "$GO" = 1 ]; then
    rmdir "$NEW/health" 2>/dev/null || true
    mv -n "$OLD/health" "$NEW/health"
  else
    echo "    mv $OLD/health -> $NEW/health"
  fi
fi

echo "6. dal repo: summary, plan, user"
for dir in summary plan user; do
  if [ -d "$REPO/$dir" ]; then
    if [ "$GO" = 1 ]; then
      rmdir "$NEW/$dir" 2>/dev/null || true
      mv -n "$REPO/$dir" "$NEW/$dir"
    else
      echo "    mv $REPO/$dir -> $NEW/$dir"
    fi
  fi
done

echo
if [ "$GO" = 1 ]; then
  echo "Fatto. Nella cartella vecchia restano:"
  ls -A "$OLD" 2>/dev/null | sed 's/^/    /'
  echo
  echo "Sono i file di conflitto della sincronizzazione e quello che il"
  echo "trasloco non conosce. Guardali prima di cancellare la cartella."
else
  echo "Giro a vuoto finito. Con --go muovo davvero."
fi
