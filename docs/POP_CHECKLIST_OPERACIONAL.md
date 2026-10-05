# Checklist operacional — SGGI

Documento curto derivado de [`POP_DESENVOLVIMENTO_E_OPERACAO.md`](POP_DESENVOLVIMENTO_E_OPERACAO.md).  
Versão: 1.0.0 · Data: 2026-10-05

---

## 1. Início de desenvolvimento

- [ ] `git pull` / branch atualizada a partir de `main`
- [ ] `.env` local existe (raiz para Docker e/ou `backend/.env`) — **não** versionado
- [ ] Portas livres: `8888` (Compose) **ou** `5173` + `8000` (local)
- [ ] Serviços sobem: `docker compose up -d` **ou** `runserver` + `npm run dev`
- [ ] Login funciona (seed ou usuário local)
- [ ] `python manage.py check_db` OK se usar MariaDB

---

## 2. Antes de abrir Pull Request

- [ ] Diff revisado — sem `.env`, `conf/`, senhas, tokens
- [ ] Migrations Django incluídas se models mudaram
- [ ] `.env.example` / `backend/.env.example` atualizados se novas variáveis
- [ ] `npm run build` OK
- [ ] Testes: `python manage.py test apps.core` (recomendado) ou justificativa
- [ ] Docs/ops atualizados se fluxo do usuário mudou
- [ ] PR com objetivo, riscos e plano de rollback (se crítico)
- [ ] Regra: SGGI **não** movimenta estoque Globus

---

## 3. Antes de executar script SQL ou migration

- [ ] Identificar alvo: **MariaDB do SGGI** (migrations) **ou** **Oracle Globus** (`SQL/`) — nunca misturar
- [ ] Script/migration revisado por segunda pessoa se destrutivo
- [ ] Backup confirmado (dump/volume/`db.sqlite3`)
- [ ] Validado em local/homologação
- [ ] Impacto e locks analisados
- [ ] Plano de rollback escrito
- [ ] Janela comunicada (se produção)
- [ ] Preferir `import_planilha … --dry-run` antes de import real

---

## 4. Antes de deploy (`srv-af-des01` / Compose)

- [ ] Código sincronizado em `/var/www/rastroglobus` (procedimento formal PENDENTE se não for git pull)
- [ ] `.env` no servidor conferido (`SECRET_KEY`, `DB_*`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`)
- [ ] Backup se mudança de dados/schema
- [ ] Build local ou CI mental: frontend `tsc` não quebra
- [ ] Comando planejado: `docker compose up -d --build`
- [ ] Seed só se ambiente novo/vazio
- [ ] Responsável de deploy definido; janela ok

---

## 5. Após deploy

- [ ] `docker compose ps` — `db` healthy; `backend`/`web` Up
- [ ] `http://srv-af-des01:8888` → HTTP 200
- [ ] Login API / UI OK
- [ ] `docker compose exec backend python manage.py check_db` → OK
- [ ] Smoke: listar garantias / abrir ficha / (se aplicável) fluxo DANFE
- [ ] `docker compose logs --tail=50 backend web` sem erros recorrentes
- [ ] Registrar versão/data/responsável

---

## 6. Rollback

- [ ] Confirmar sintoma (build, 5xx, restart loop, DB)
- [ ] Preservar logs: `docker compose logs > …` se necessário
- [ ] Restaurar código/imagem anterior (procedimento de tag/imagem: PENDENTE DE DEFINIÇÃO)
- [ ] Se DB: restore backup — **não** usar `down -v` sem autorização
- [ ] `docker compose up -d --build` com versão estável
- [ ] Repetir checklist “Após deploy”
- [ ] Abrir incidente / post-mortem se SEV1–SEV2

---

## 7. Resposta inicial a incidente

- [ ] Registrar horário, sintoma, URL/ambiente
- [ ] Classificar SEV1–SEV4 (ver POP §17)
- [ ] Mitigar: estabilizar serviço / comunicar usuários
- [ ] Coletar evidências (`compose ps`, logs, `check_db`)
- [ ] Decidir: correção rápida vs rollback
- [ ] Comunicar responsável (lista: PENDENTE DE DEFINIÇÃO)
- [ ] Não apagar evidências antes do registro

---

## 8. Rotação de segredo vazado

- [ ] Revogar/rotacionar imediatamente (DB, OpenAI, Oracle, SSH, JWT secret)
- [ ] Avaliar impacto (quem teve acesso, por quanto tempo)
- [ ] Remover segredo de arquivos, tickets e chat
- [ ] Atualizar `.env` nos ambientes e reiniciar backend (`compose up -d --force-recreate backend`)
- [ ] Se entrou no Git: limpar histórico + force-safe com aprovação
- [ ] Alterar senha MariaDB **no servidor e** no `.env` (ALTER USER se volume já existia)
- [ ] Registrar incidente SEV1 e ação preventiva
- [ ] Validar app após rotação (`check_db`, login)
