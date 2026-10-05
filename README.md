# SGGI — Sistema de Gestão de Garantias Improcedentes

Rastreia o ciclo de garantia de peças da frota **sem movimentar estoque**.

> O Globo controla estoque. O SGGI controla o rastro da garantia.

## Regra inegociável

SGGI **não** dá entrada, **não** dá baixa e **não** altera saldo.  
Status `improcedente` e `cortesia` nunca gravam lógica de estoque.  
O campo `nf_entrada_globo` é **somente texto** e só faz sentido em `procedente`.

## Stack

- **Backend:** Django 5 + DRF + SimpleJWT + CORS + SQLite (dev) ou MariaDB
- **Frontend:** Vite + React 18 + TypeScript + Tailwind + React Router

## Como subir (Docker — servidor)

Na raiz do monorepo:

```bash
cp .env.example .env
# edite SECRET_KEY, DB_PASSWORD, DB_ROOT_PASSWORD, ALLOWED_HOSTS

docker compose up -d --build
docker compose exec backend python manage.py seed   # opcional, 1ª vez
```

App em `http://srv-af-des01:8888` (nginx → frontend + `/api` + `/media`).

Código no servidor: `/var/www/sggi` (projeto Docker Compose: `sggi`).

### Backend (local sem Docker)

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
# source .venv/bin/activate

pip install -r requirements.txt
python manage.py migrate
python manage.py seed
python manage.py runserver
```

API em `http://localhost:8000/api/`

### Banco MariaDB

Por padrão o app usa **SQLite** (`backend/db.sqlite3`) se `DB_ENGINE` não estiver definido.

Para usar MariaDB:

1. Criar o database com charset utf8mb4:

```sql
CREATE DATABASE sggi
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

2. Configurar ambiente (sem versionar senhas):

```bash
cd backend
copy .env.example .env
# edite .env — exemplo:
# DB_ENGINE=django.db.backends.mysql
# DB_HOST=127.0.0.1
# DB_PORT=3306
# DB_NAME=sggi
# DB_USER=...
# DB_PASSWORD=...
# DB_ALLOW_LEGACY_MARIADB=1   # so se o servidor for MariaDB < 10.5 (ex.: 10.2)
```

3. Instalar deps (inclui `mysqlclient`), migrar e validar:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed
python manage.py check_db
```

`check_db` deve imprimir `OK` com a versão do MariaDB/MySQL.

### Importar planilha histórica (BASE GERAL)

Totais mensais por fornecedor/empresa (não cria `Garantia`):

```bash
cd backend
python manage.py import_planilha caminho\GARANTIA-2026.xlsx --dry-run
python manage.py import_planilha caminho\GARANTIA-2026.xlsx
```

- Aba obrigatória: **BASE GERAL**
- Rodar de novo não duplica (`hash_linha`)
- Linhas inválidas → `{arquivo}_rejeitados.csv`
- Nomes parecidos (difflib > 0.85) → `{arquivo}_similares.txt` + stdout
- API: `GET /api/relatorios/historico/?ano=&empresa=&fornecedor=`
- Dashboard → aba **Historico (planilha)**

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App em `http://localhost:5173` (proxy `/api` → backend).

## Login Samba / AD (LDAPS)

Autenticação corporativa é opcional e **não altera** o Samba.

1. Coloque a CA UCS em `certs/ucs-ca.crt`
2. Configure no `.env` as variáveis `AD_LDAP_*` (ver `.env.example`)
3. Deixe `AD_LDAP_ENABLED=0` até homologar; depois `1` e rebuild do backend

Checklist: [`docs/CHECKLIST_HOMOLOG_LDAP.md`](docs/CHECKLIST_HOMOLOG_LDAP.md) · Pedido à infra: [`docs/SOLICITACAO_INFRA_LDAP_SGGI.md`](docs/SOLICITACAO_INFRA_LDAP_SGGI.md)

## Usuários seed

| Usuário     | Senha        | Perfil      | Pode |
|-------------|--------------|-------------|------|
| admin       | admin123     | admin       | Tudo |
| oficina     | oficina123   | oficina     | Criar garantia, anexar |
| compras     | compras123   | compras     | Vincular NFs, avançar status |
| manutencao  | manut123     | manutencao  | Fechar (procedente/improcedente/cortesia) |
| direcao     | direcao123   | direcao     | Somente leitura + export CSV |

O seed também cria **1 garantia exemplo** (`GAR-2026-0131`, peça Globus `01111011`) para o cruzamento com compras. Demais garantias vêm de **Nova garantia** com busca Globus.

## Status do fluxo

```
aberta → enviada → em_analise → procedente | improcedente | cortesia
aberta / enviada → cancelada
```

Protocolo: `GAR-AAAA-000001`. Toda mudança de status gera `EventoGarantia` (timeline imutável).  
Garantias **não** podem ser apagadas pela API (protege a timeline).

## Integração Globus (somente leitura)

O Oracle Globus é lido **só pelo job** `sync_globus` (SELECT). As telas usam tabelas espelho locais.  
**Não grava** nada no Globo e **não movimenta estoque**. Busca de NF por número continua ao vivo (timeout 15s).

Arquivos esperados na pasta `conf/` (raiz do monorepo):

- `chave.key`
- `erp.dat` (fallback: `erp_BD.dat`, `erp_Old.dat`)

Credenciais vêm de `conf/` (raiz do monorepo): `chave.key` + `erp.dat`.

Instant Client (obrigatório — servidor com Native Network Encryption):

1. Crie `conf/oracle_client_dir.txt` com uma linha = pasta do Instant Client (ex. `...\instantclient_21_14`), **ou**
2. Defina `ORACLE_CLIENT_LIB_DIR` no `.env`

Variáveis (também em `backend/.env.example`):

```bash
set RASTROGLOBUS_CONF_DIR=C:\caminho\para\conf
set ORACLE_CLIENT_LIB_DIR=C:\caminho\instantclient
set GLOBUS_CALL_TIMEOUT_MS=60000
set GLOBUS_GRUPOS_PECAS=01
```

### sync_globus

```bash
cd backend
python manage.py sync_globus
python manage.py sync_globus --full
python manage.py sync_globus --tipo compras
python manage.py sync_globus --tipo saidas
python manage.py detectar_reincidencia
```

Apos sync de saidas, rode `detectar_reincidencia` para gerar `AlertaReincidencia` (sem duplicar).

**Agendador de Tarefas (Windows) — scripts prontos:**

```powershell
# Job manual (log em logs\sync_globus_YYYYMMDD.log)
.\scripts\sync_globus_job.ps1 -DetectarReincidencia

# Registrar tarefa diaria 06:30 (pode pedir admin na 1a vez)
.\scripts\register_sync_globus_task.ps1

# Import BASE GERAL (arquivo em docs\ops\incoming\ ou -Path)
.\scripts\import_planilha_real.ps1

# Checklist go-live (checks automaticos)
.\scripts\aceite_golive_check.ps1
```

Cutover ops: `docs/ops/programa-cutover-improcedentes.md` e `docs/ops/operacao-diaria-novos-rg.md`.

Endpoints:

- `GET /api/globus/status/` — ultimo SyncLog por tipo (badge no frontend)
- `GET /api/globus/local/pecas/?q=` / `local/veiculos/?q=` — espelho local
- `GET /api/globus/pecas/?q=` / `veiculos/?q=` — Oracle ao vivo (alternativa)
- `GET /api/globus/nf/?numero=` — NF ao vivo (`BGM_NOTAFISCAL`, 15s)
- `GET /api/globus/movimentos/...` / `compras/` — ainda podem consultar Oracle
- `GET /api/relatorios/improcedentes-compras/?ano=&peca=` — improcedentes SGGI × `CompraGlobus` local
- `POST /api/pecas/ensure/`, `/api/veiculos/ensure/`, `/api/fornecedores/ensure/` — cadastro SGGI sob demanda

Na UI: **Nova garantia** busca peça/veículo/NF no Globus; **Movimentos Globus** inclui tipo Compras/aquisição; Relatórios com **Improcedentes × compras Globus**.

## Estrutura

```
backend/     Django (apps/core)
frontend/    Vite React
conf/        credenciais Oracle (não versionar)
```
