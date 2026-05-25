# IT Asset Manager — Instruções de Uso

## Pré-requisitos

- **Python** instalado (com `.venv` já criado na pasta do projeto)
- **PostgreSQL** instalado e em execução
- Banco de dados: `it_asset_db` (usuário: `postgres`, porta: `5432`)

---

## Instalação em um PC novo (do zero)

> Siga esta seção apenas se for a primeira vez rodando o projeto neste computador.

### Etapa A — Instalar os programas obrigatórios (manual, feito uma única vez)

Estes dois passos exigem instalação com clique e não podem ser automatizados:

#### 1. Instalar o Python 3.12

Baixe em: https://www.python.org/downloads/release/python-3122/  
Durante a instalação, marque a opção **"Add Python to PATH"**.

#### 2. Instalar o PostgreSQL

Baixe em: https://www.postgresql.org/download/windows/  
Durante a instalação:
- Anote a senha que definir para o usuário `postgres`
- Mantenha a porta padrão `5432`

#### 3. Adicionar o PostgreSQL ao PATH do sistema

Para que o agente consiga executar os comandos do banco, adicione a pasta `bin` do PostgreSQL ao PATH:

1. Abra **Variáveis de Ambiente** (`Win + R` → `sysdm.cpl` → aba **Avançado** → **Variáveis de Ambiente**)
2. Em **Variáveis do sistema**, clique em **Path** → **Editar** → **Novo**
3. Adicione o caminho (ajuste a versão se necessário):
   ```
   C:\Program Files\PostgreSQL\17\bin
   ```
4. Clique em OK e **reinicie o VS Code**.

---

### Etapa B — Deixar o agente de IA fazer o resto (automático)

Após instalar Python e PostgreSQL, o agente do GitHub Copilot no VS Code pode executar automaticamente todos os demais passos (criar o ambiente virtual, instalar dependências, restaurar o banco e iniciar o servidor).

**Como usar:**

1. Abra o VS Code na pasta do projeto
2. Abra o painel de chat do Copilot (`Ctrl + Alt + I`)
3. Certifique-se de que o modo **Agent** está selecionado (não "Ask" ou "Edit")
4. Digite `/` e selecione **Configurar IT Asset Manager**
5. O agente guiará você por toda a configuração, executando os comandos no terminal automaticamente

> O arquivo do agente está em `.github/prompts/configurar-projeto.prompt.md`

---

### Instalação manual (alternativa sem agente)

Se preferir configurar manualmente sem usar o agente:

<details>
<summary>Clique para expandir os passos manuais</summary>

**Copie a pasta do projeto para o PC**, por exemplo em:
```
C:\Users\SeuUsuario\Desktop\it-asset-manager
```

**Crie o banco de dados** — abra o SQL Shell (psql) e execute:
```sql
CREATE DATABASE it_asset_db;
```

**Restaure o backup** via PowerShell (na pasta do projeto):
```powershell
psql -U postgres -d it_asset_db -f "BKP-Banco-20-06-2025-ComSedes - JA COM USUARIOS MODIFICADO.sql"
```

**Crie e ative o ambiente virtual:**
```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

**Instale as dependências:**
```powershell
pip install -r requirements.txt
```

**Aplique as migrações:**
```powershell
python manage.py migrate
```

> **Não é necessário criar superusuário** — os usuários já estão incluídos no backup restaurado.

</details>

Após concluir a configuração, siga a seção **"Como iniciar o sistema"** abaixo.

---

## Como iniciar o sistema

### 1. Abrir o terminal na pasta do projeto

```
C:\Users\DU2KI57\Desktop\it-asset-manager
```

### 2. Ativar o ambiente virtual

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

> O terminal deve mostrar `(.venv)` no início da linha após a ativação.

### 3. Verificar se o PostgreSQL está rodando

Abra o **Services** do Windows (`Win + R` → `services.msc`) e confirme que o serviço **postgresql-x64-XX** está em execução. Ou rode:

```powershell
Get-Service -Name postgresql*
```

### 4. Iniciar o servidor Django

```powershell
python manage.py runserver
```

### 5. Acessar no navegador

```
http://127.0.0.1:8000/
```

- Painel principal (dashboard): `http://127.0.0.1:8000/`
- Admin do Django: `http://127.0.0.1:8000/admin/`

---

## Comandos úteis

| Finalidade | Comando |
|---|---|
| Iniciar servidor | `python manage.py runserver` |
| Aplicar migrações (após mudanças no model) | `python manage.py migrate` |
| Criar superusuário (admin) | `python manage.py createsuperuser` |
| Importar dados do SCCM | `python manage.py import_sccm` |
| Importar histórico (Storico.CSV) | `python manage.py import_historico` |
| Parar o servidor | `Ctrl + C` no terminal |

---

## Banco de dados

| Parâmetro | Valor |
|---|---|
| Engine | PostgreSQL |
| Nome do banco | `it_asset_db` |
| Usuário | `postgres` |
| Host | `127.0.0.1` |
| Porta | `5432` |
| Senha | ver `asset_manager/settings.py` |

---

## Estrutura resumida do projeto

```
it-asset-manager/
├── manage.py              ← ponto de entrada Django
├── asset_manager/         ← configurações do projeto (settings, urls)
├── gestao/                ← app principal (models, views, forms)
│   ├── templates/         ← páginas HTML
│   ├── migrations/        ← histórico do banco de dados
│   └── management/commands/  ← comandos de importação
└── static/                ← CSS e JS (Bootstrap)
```

---

## Resolução de problemas comuns

**Erro: "could not connect to server" (banco de dados)**
→ Verifique se o PostgreSQL está em execução (`services.msc`).

**Erro: "No module named django"**
→ O ambiente virtual não está ativado. Execute o passo 2 novamente.

**Página não carrega após iniciar**
→ Aguarde a mensagem `Starting development server at http://127.0.0.1:8000/` no terminal antes de abrir o navegador.

**Mudanças no model não aparecem**
→ Execute `python manage.py makemigrations` e depois `python manage.py migrate`.
