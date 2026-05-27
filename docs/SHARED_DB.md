# Condivisione semplice del DB per sviluppo

Obiettivo: quando un collega fa `git pull`, il suo DB di sviluppo rispecchia lo stato del tuo DB locale (dati rilevanti per lo sviluppo), con il minimo sforzo manuale.

Soluzione adottata qui (veloce, semplice, sicura):

- Il flusso crea automaticamente un file `db.sqlite3` (binario) nel repository contenente schema e dati di sviluppo. Questo file viene rigenerato prima del `push` e committato insieme al codice.
- `asset_manager/settings.py` è stato aggiornato per preferire il DB `db.sqlite3` quando è presente nel repo, in modo che chi fa `git pull` ottenga immediatamente lo stesso DB senza ulteriori comandi.
- Manteniamo il fixture JSON `gestao/fixtures/devdata.json` e il comando `python manage.py dump_devdata` come sorgente dei dati; un hook `pre-push` rigenera il fixture e poi crea `db.sqlite3` applicando le migration e caricando il fixture.
- Il `pre-push` esegue anche `git fetch` + `git rebase --autostash origin/<branch>` automaticamente prima di generare il DB: questo riduce i conflitti sui file binari. Se il rebase fallisce, sarà necessario risolvere i conflitti manualmente.
- Il `post-merge` salva una copia del DB locale precedente in `.db_backups/` con timestamp prima di applicare migrations/fixtures, così non si perde lo stato locale in caso di problemi.

Vantaggi:

- Il collega deve solo eseguire `git pull` per avere lo stesso DB (dopo aver installato gli hook una volta).
- Funziona attraverso GitHub (nessun DB remoto richiesto), quindi non tocca il proxy/firewall aziendale.
- Il processo è automatico per chi effettua il `push` (tramite `pre-push`) e automatico al `pull` per chi ha gli hook installati (`post-merge`).

Limitazioni e avvertenze:

- Non è adatto a DB di produzione o dataset molto grandi (il file `db.sqlite3` è binario e cresce con i dati).
- Evitare di includere dati sensibili nelle fixture o nel DB (password, PII). Tenere `gestao/fixtures/devdata.json` pulito.
- Il flusso è bidirezionale ma **richiede che entrambi** gli sviluppatori installino una volta gli hook locali. Senza gli hook, il comportamento automatico non si attiverà su quella macchina.

Istruzioni rapide

1) Prima volta (solo chi effettua i `push` e chi effettua i `pull`, una tantum):

Unix / WSL / macOS:
```bash
./scripts/install-hooks.sh
```

Windows PowerShell:
```powershell
.\scripts\install-hooks.ps1
```

2) Aggiornare i dati e pushare (chi cambia i dati):

Se hai installato l'hook, basta fare le modifiche e `git push`:

```bash
git add .
git commit -m "feat: aggiornamenti"
git push
```

L'hook `pre-push` eseguirà automaticamente:

- `git fetch origin <branch>` e `git rebase --autostash origin/<branch>` (se il rebase fallisce, risolvere i conflitti manualmente)
- `python manage.py dump_devdata` (rigenera `gestao/fixtures/devdata.json`)
- `python scripts/generate_sqlite.py` (genera `db.sqlite3` applicando migrations e fixture)
- committare eventuali file generati e consentire il push

3) Sul PC del collega (dopo `git pull`):

Nulla da fare: dopo il `git pull` (se ha installato l'hook) il `post-merge` salverà automaticamente una copia del DB precedente in `.db_backups/`, applicherà le migrations ed eventualmente caricherà i fixture solo se il DB non è stato aggiornato dal merge.

Quindi, nella normale operatività, il collega deve solo eseguire `git pull` e riavviare l'app: vedrà lo stesso DB.

Come funziona il `dump_devdata`
- È un management command presente in `gestao/management/commands/dump_devdata.py`.
- Di default esporta l'app `gestao` in `gestao/fixtures/devdata.json`. Puoi cambiare app o percorso con `--apps` e `--output`.

Alternative (se preferite):
- Docker Compose: replica l'intero ambiente (Postgres + Adminer). Ho incluso `docker-compose.yml` nella root. Con Docker potete avere un DB identico tra macchine; tuttavia su reti aziendali con proxy/firewall può essere più complicato.
- DB centrale: mettere Postgres su una VM/host accessibile (richiede permessi di rete e sicurezza).

Note finali
- `asset_manager/settings.py` usa `db.sqlite3` se presente nel repo, a meno che non sia impostata la variabile d'ambiente `FORCE_POSTGRES=1` (oppure `USE_REPO_SQLITE=1` forzi l'uso dello sqlite).
- Non memorizzare credenziali reali nel repository. Usare variabili d'ambiente o `.env` gestiti localmente.
- Se vuoi, posso:
  - aggiungere ulteriori backup/rotazione in `post-merge`, o
  - creare e pubblicare un'immagine Docker con il DB precaricato (utile come artefatto condiviso).
