---
status: done
---

# I sette giorni del piano, da leggere e non da decifrare

Il todo 60 ha portato il piano della settimana nella pagina, e il contenuto
era giusto: la tabella Day/Session dice le sette sedute col perche' dentro.
Era la forma a non reggere — una tabella Markdown qualunque, con la colonna
del testo strizzata.

## Il difetto vero

`.prose table` sta a misura del contenuto. Con due colonne di cui una e' un
paragrafo, il risultato e' che **la colonna della seduta si stringe e va a
capo tre volte mentre a destra resta bianco**: il testo piu' importante della
vista nello spazio piu' piccolo. `width: 100%` e' il grosso della correzione.

Il resto e' smettere di trattare le due colonne come due celle uguali, che non
lo sono: la prima e' la chiave della riga — il giorno — la seconda un
paragrafo. Il giorno diventa un'etichetta su fondo tenue, in cima alla sua
riga e larga quanto la parola; la seduta prende aria e interlinea 1.55, che a
riga alta un paragrafo si legge e una cella no. L'intestazione stacca con un
bordo `--border-strong`.

## Perche' sotto una classe sua

Lo stile sta sotto `.week-plan-card` e non su `.plan-prose`, che vestirebbe
anche i piani di `plan/`: la' le tabelle sono di sei colonne di numeri — le
diciotto settimane, i ritmi, i tempi di passaggio — e una prima colonna a
fondo tinto le farebbe leggere come una cosa che non sono. La regola vale dove
la prima colonna e' davvero un'etichetta.

Dentro il piano settimanale la prende anche la tabella **Paces**, e va bene:
"Easy", "Steady", "Race pace" sono chiavi di riga esattamente come i giorni.

## Quello che non si e' fatto

Non si e' marcato **il giorno di oggi**, che sarebbe la cosa piu' utile della
vista. Il CSS non sa che giorno e', e saperlo vuole o le sette sedute del
front matter dall'API (`sessions`, che il todo 60 non manda per scelta) o la
tabella letta dal testo. Si fa quando si fa il confronto previsto/fatto del
`todo/14_plan_vs_done.md`, che quella struttura la vuole comunque: due volte
la stessa fatica, una volta sola.
