# IT Asset Manager — Istruzioni d'Uso

## Prerequisiti

- **Python** installato (con `.venv` già creato nella cartella del progetto)
- **PostgreSQL** installato e in esecuzione
- Database: `it_asset_db` (utente: `postgres`, porta: `5432`)

---

## Installazione su un nuovo PC (da zero)

> Seguire questa sezione solo se è la prima volta che si avvia il progetto su questo computer.

### Fase A — Installare i programmi obbligatori (manuale, fatto una sola volta)

Questi due passaggi richiedono un'installazione con clic e non possono essere automatizzati:

#### 1. Installare Python 3.12

Scaricare da: https://www.python.org/downloads/release/python-3122/  
Durante l'installazione, spuntare l'opzione **"Add Python to PATH"**.

#### 2. Installare PostgreSQL

Scaricare da: https://www.postgresql.org/download/windows/  
Durante l'installazione:
- Annotare la password impostata per l'utente `postgres`
- Mantenere la porta predefinita `5432`

#### 3. Aggiungere PostgreSQL al PATH di sistema

Affinché l'agente possa eseguire i comandi del database, aggiungere la cartella `bin` di PostgreSQL al PATH:

1. Aprire **Variabili d'ambiente** (`Win + R` → `sysdm.cpl` → scheda **Avanzate** → **Variabili d'ambiente**)
2. In **Variabili di sistema**, cliccare su **Path** → **Modifica** → **Nuovo**
3. Aggiungere il percorso (adattare la versione se necessario):
   ```
   C:\Program Files\PostgreSQL\17\bin
   ```
4. Cliccare OK e **riavviare VS Code**.

---

### Fase B — Lasciare all'agente IA il resto (automatico)

Dopo aver installato Python e PostgreSQL, l'agente GitHub Copilot in VS Code può eseguire automaticamente tutti gli altri passaggi (creare il virtualenv, installare le dipendenze, ripristinare il database e avviare il server).

**Come usarlo:**

1. Aprire VS Code nella cartella del progetto
2. Aprire il pannello chat di Copilot (`Ctrl + Alt + I`)
3. Assicurarsi che la modalità **Agent** sia selezionata (non "Ask" o "Edit")
4. Digitare `/` e selezionare **Configurar IT Asset Manager**
5. L'agente guiderà l'utente attraverso tutta la configurazione, eseguendo i comandi nel terminale automaticamente

> Il file dell'agente si trova in `.github/prompts/configurar-projeto.prompt.md`

---

### Installazione manuale (alternativa senza agente)

Se si preferisce configurare manualmente senza usare l'agente:

<details>
<summary>Cliccare per espandere i passaggi manuali</summary>

**Copiare la cartella del progetto nel PC**, ad esempio in:
```
C:\Users\TuoUtente\Desktop\it-asset-manager
```

**Creare il database** — aprire SQL Shell (psql) ed eseguire:
```sql
CREATE DATABASE it_asset_db;
```

**Ripristinare il backup** tramite PowerShell (nella cartella del progetto):
```powershell
psql -U postgres -d it_asset_db -f "BKP-Banco-20-06-2025-ComSedes - JA COM USUARIOS MODIFICADO.sql"
```

**Creare e attivare l'ambiente virtuale:**
```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

**Installare le dipendenze:**
```powershell
pip install -r requirements.txt
```

**Applicare le migrazioni:**
```powershell
python manage.py migrate
```

> **Non è necessario creare il superutente** — gli utenti sono già inclusi nel backup ripristinato.

</details>

Dopo aver completato la configurazione, seguire la sezione **"Come avviare il sistema"** qui sotto.

---

## Come avviare il sistema

### 1. Aprire il terminale nella cartella del progetto

```
C:\Users\DU2KI57\Desktop\it-asset-manager
```

### 2. Attivare l'ambiente virtuale

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

> Il terminale deve mostrare `(.venv)` all'inizio della riga dopo l'attivazione.

### 3. Verificare che PostgreSQL sia in esecuzione

Aprire **Servizi** di Windows (`Win + R` → `services.msc`) e confermare che il servizio **postgresql-x64-XX** sia attivo. Oppure eseguire:

```powershell
Get-Service -Name postgresql*
```

### 4. Avviare il server Django

```powershell
python manage.py runserver
```

### 5. Accedere dal browser

```
http://127.0.0.1:8000/
```

- Pannello principale (dashboard): `http://127.0.0.1:8000/`
- Admin Django: `http://127.0.0.1:8000/admin/`

---

## Comandi utili

| Scopo | Comando |
|---|---|
| Avviare il server | `python manage.py runserver` |
| Applicare le migrazioni (dopo modifiche al model) | `python manage.py migrate` |
| Creare un superutente (admin) | `python manage.py createsuperuser` |
| Importare dati da SCCM | `python manage.py import_sccm` |
| Importare lo storico (Storico.CSV) | `python manage.py import_historico` |
| Fermare il server | `Ctrl + C` nel terminale |

---

## Database

| Parametro | Valore |
|---|---|
| Engine | PostgreSQL |
| Nome del database | `it_asset_db` |
| Utente | `postgres` |
| Host | `127.0.0.1` |
| Porta | `5432` |
| Password | vedere `asset_manager/settings.py` |

---

## Struttura del progetto

```
it-asset-manager/
├── manage.py              ← punto di ingresso Django
├── asset_manager/         ← configurazioni del progetto (settings, urls)
├── gestao/                ← app principale (models, views, forms)
│   ├── templates/         ← pagine HTML
│   ├── migrations/        ← storico del database
│   └── management/commands/  ← comandi di importazione
└── static/                ← CSS e JS (Bootstrap)
```

---

## Risoluzione dei problemi comuni

**Errore: "could not connect to server" (database)**
→ Verificare che PostgreSQL sia in esecuzione (`services.msc`).

**Errore: "No module named django"**
→ L'ambiente virtuale non è attivo. Eseguire nuovamente il passo 2.

**La pagina non si apre dopo l'avvio**
→ Attendere il messaggio `Starting development server at http://127.0.0.1:8000/` nel terminale prima di aprire il browser.

**Modifiche al model non visibili**
→ Eseguire `python manage.py makemigrations` e poi `python manage.py migrate`.
