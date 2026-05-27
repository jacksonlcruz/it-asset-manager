# Condivisione semplice del DB per sviluppo

Obiettivo: quando un collega fa `git pull`, il suo DB di sviluppo rispecchia lo stato del tuo DB locale (dati rilevanti per lo sviluppo).

Soluzione adottata qui (veloce, semplice, sicura):

- Ora il flusso crea automaticamente un file `db.sqlite3` nel repository (binario SQLite) contenente schema e dati di sviluppo. Questo file viene rigenerato prima del `push` e committato insieme al codice.
- `asset_manager/settings.py` è stato aggiornato per preferire il DB `db.sqlite3` quando è presente nel repo, in modo che chi fa `git pull` ottenga immediatamente lo stesso DB senza ulteriori comandi.
- Manteniamo comunque il fixture JSON `gestao/fixtures/devdata.json` e il comando `python manage.py dump_devdata` come sorgente dei dati; un hook `pre-push` rigenera il fixture e poi crea `db.sqlite3` applicando le migration e caricando il fixture.

Vantaggi:
- Il collega deve solo eseguire `git pull` per avere lo stesso DB (zero altri comandi).
- Funziona attraverso GitHub (nessun DB remoto richiesto), quindi non tocca il proxy/firewall aziendale.
- Il processo è automatico per chi effettua il `push` (tramite hook locale che rigenera il DB), e ripetibile.

Limitazioni e avvertenze:
- Non è adatto a DB di produzione o a dataset molto grandi (il file `db.sqlite3` è binario e cresce con i dati).
- Evitare di includere dati sensibili nelle fixture o nel DB (password, PII). Tenere `gestao/fixtures/devdata.json` pulito.
- Il workflow automatizza tutto per il collega, ma chi effettua i `push` deve installare localmente gli hook una sola volta (vedi installazione sotto) affinché il `db.sqlite3` venga generato automaticamente prima del push.

Istruzioni rapide

1) Prima volta (su ogni macchina):

Unix / WSL / macOS:
```bash
./scripts/install-hooks.sh
```

Windows PowerShell:
```powershell
.\scripts\install-hooks.ps1
```

2) Aggiornare il fixture e pushare (chi cambia i dati):

```bash
python manage.py dump_devdata
git add gestao/fixtures/devdata.json
git commit -m "Aggiorna dev fixtures"
git push
```

Se hai installato l'hook, il `pre-push` automatizza i primi due passaggi.

3) Sul PC del collega (dopo `git pull`):

Se ha installato l'hook, `post-merge` applicherà automaticamente le migration e caricherà il fixture.
Altrimenti eseguire manualmente:

```bash
python manage.py migrate
python manage.py loaddata gestao/fixtures/devdata.json
```

Come funziona il `dump_devdata`
- È un management command presente in `gestao/management/commands/dump_devdata.py`.
- Di default esporta l'app `gestao` in `gestao/fixtures/devdata.json`. Puoi cambiare app o percorso con `--apps` e `--output`.

Alternative (se preferite):
- Docker Compose: replica l'intero ambiente (Postgres + Adminer). Ho incluso `docker-compose.yml` nella root. Con Docker potete avere un DB identico tra macchine; tuttavia su reti aziendali con proxy/firewall può essere più complicato.
- DB centrale: mettere Postgres su una VM/host accessibile (richiede permessi di rete e sicurezza).

Note finali
- Non memorizzare credenziali reali nel repository. Usare variabili d'ambiente o `.env` gestiti localmente.
- Se vuoi, posso:
  - aggiungere un `post-merge` più robusto che esegue backup automatici prima del `loaddata`, o
  - creare e pubblicare un'immagine Docker con il DB precaricato (utile come artefatto condiviso).
