---
name: "Configurar IT Asset Manager"
description: "Configura o ambiente do projeto IT Asset Manager do zero: cria o virtualenv, instala dependências, cria e restaura o banco de dados PostgreSQL e aplica as migrações."
agent: "agent"
tools: [run_in_terminal, create_file, read_file, file_search]
---

Você é um assistente de configuração do projeto **IT Asset Manager**. Siga os passos abaixo em ordem, executando os comandos necessários no terminal. Informe o usuário sobre o progresso em cada etapa e, se ocorrer algum erro, explique o que fazer.

## Contexto do projeto
- Framework: Django 5.2 + PostgreSQL
- Python necessário: 3.12
- Banco de dados: `it_asset_db` (usuário `postgres`, porta `5432`)
- O arquivo de backup do banco está na raiz do projeto: `BKP-Banco-20-06-2025-ComSedes - JA COM USUARIOS MODIFICADO.sql`

---

## Passo 1 — Verificar Python

Execute o comando abaixo e confirme que a versão é 3.12.x:

```powershell
python --version
```

Se Python não estiver instalado ou a versão for diferente de 3.12, informe o usuário para baixar em https://www.python.org/downloads/release/python-3122/ e reiniciar este processo após a instalação.

---

## Passo 2 — Criar o ambiente virtual

Verifique se a pasta `.venv` já existe. Se não existir, crie-a:

```powershell
python -m venv .venv
```

---

## Passo 3 — Instalar as dependências

Ative o ambiente virtual e instale os pacotes do `requirements.txt`:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Confirme que todos os pacotes foram instalados sem erros.

---

## Passo 4 — Verificar PostgreSQL e criar o banco de dados

Verifique se o PostgreSQL está acessível:

```powershell
psql -U postgres -c "\l"
```

Se o comando falhar, informe o usuário que o PostgreSQL precisa estar instalado e em execução, e que o executável `psql` precisa estar no PATH do sistema (normalmente em `C:\Program Files\PostgreSQL\<versão>\bin`).

Se funcionar, verifique se o banco `it_asset_db` já existe. Se não existir, crie-o:

```powershell
psql -U postgres -c "CREATE DATABASE it_asset_db;"
```

---

## Passo 5 — Restaurar o backup do banco de dados

Pergunte ao usuário se deseja restaurar o backup (recomendado para ter todos os dados e usuários). Se sim, execute:

```powershell
psql -U postgres -d it_asset_db -f "BKP-Banco-20-06-2025-ComSedes - JA COM USUARIOS MODIFICADO.sql"
```

> Se o terminal pedir senha, é a senha do usuário `postgres` definida na instalação do PostgreSQL.

---

## Passo 6 — Verificar configuração do banco em settings.py

Leia o arquivo `asset_manager/settings.py` e verifique o bloco `DATABASES`. Confirme com o usuário se a senha (`PASSWORD`) corresponde à senha do PostgreSQL instalado neste PC. Se for diferente, atualize o valor no arquivo.

---

## Passo 7 — Aplicar migrações

```powershell
.\.venv\Scripts\python.exe manage.py migrate
```

Se a mensagem for `No migrations to apply.`, está correto (o backup já continha o esquema).

---

## Passo 8 — Iniciar o servidor

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

Informe o usuário que o sistema está disponível em: **http://127.0.0.1:8000/**

Aguarde confirmação do usuário de que a página carregou corretamente antes de considerar a configuração concluída.
