# RastroGlobus (RG)

Rastreia o ciclo de garantia de peças da frota **sem movimentar estoque**.

> O Globo controla estoque. O RastroGlobus controla o rastro da garantia.

## Regra inegociável

RastroGlobus **não** dá entrada, **não** dá baixa e **não** altera saldo.  
Status `improcedente` e `cortesia` nunca gravam lógica de estoque.  
O campo `nf_entrada_globo` é **somente texto** e só faz sentido em `procedente`.

## Stack

- **Backend:** Django 5 + DRF + SimpleJWT + CORS + SQLite
- **Frontend:** Vite + React 18 + TypeScript + Tailwind + React Router

## Como subir

### Backend

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

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App em `http://localhost:5173` (proxy `/api` → backend).

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

O RG **consulta** o Oracle Globus via `conf/` (mesmo padrão corporativo Fernet).  
**Não grava** nada no Globo e **não movimenta estoque**.

Arquivos esperados na pasta `conf/` (raiz do monorepo):

- `chave.key`
- `erp.dat` (fallback: `erp_BD.dat`, `erp_Old.dat`)

Variáveis opcionais:

```bash
# pasta conf alternativa
set RASTROGLOBUS_CONF_DIR=C:\caminho\para\conf

# Instant Client (se thin mode falhar / Native Network Encryption)
set ORACLE_CLIENT_LIB_DIR=C:\caminho\instantclient
```

Endpoints:

- `GET /api/globus/status/` — ping + resumo sem senha
- `GET /api/globus/nf/?numero=` — espelho de NF (`BGM_NOTAFISCAL`)
- `GET /api/globus/veiculos/?q=` — frota (`FRT_CADVEICULOS`)
- `GET /api/globus/pecas/?q=` — materiais (`EST_CADMATERIAL`)
- `GET /api/globus/movimentos/?peca=&veiculo=&tipo=&data_ini=&data_fim=` — entrada/saída (`EST_MOVTO`)
- `GET /api/globus/compras/?peca=` — aquisições (padrão relatório compras peças)
- `GET /api/globus/nfs-garantia/?numero=&peca=` — NFs Globus tipo NEG/NFG (garantia)
- `GET /api/relatorios/improcedentes-compras/?ano=&peca=` — cruzamento improcedentes RG × compras Globus
- `POST /api/pecas/ensure/`, `/api/veiculos/ensure/`, `/api/fornecedores/ensure/` — espelho local sob demanda (não grava no Oracle)

Na UI: **Nova garantia** busca peça/veículo/NF no Globus; **Movimentos Globus** inclui tipo Compras/aquisição; Relatórios com **Improcedentes × compras Globus**.

## Estrutura

```
backend/     Django (apps/core)
frontend/    Vite React
conf/        credenciais Oracle (não versionar)
```
