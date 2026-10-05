# Programa operacional — SGGI vs Excel (improcedentes)

Documento de orquestração (ChiefAIArchitect).  
**Não inventa dados.** Campos marcados `TBD — Matheus` só fecham na sessão com Matheus.

## ADRs vigentes

| ID | Decisão |
|----|---------|
| ADR-01 | Fonte de verdade de **improcedente** = SGGI |
| ADR-02 | Fonte de verdade de **estoque** = Globus (Oracle somente leitura no SGGI) |
| ADR-03 | Excel é legado; após cutover, casos **novos** só no SGGI |
| ADR-04 | Sem seed/demo para “preencher” anos sem garantia real |

---

## 1. Sessão Matheus — SOP improcedente

**Objetivo da reunião:** validar o que o app já faz contra a operação real e fechar cutover.

### 1.1 Já existe no produto (para validar, não redesenhar)

| Tema | Como está no SGGI |
|------|-----------------|
| Abrir garantia | Oficina; peça/veículo/fornecedor; busca Globus (espelho/live) |
| Remessa / retorno | NFs vinculadas na ficha |
| Fechar improcedente | Perfil manutenção (e admin); exige laudo + motivo + `causa_improcedente` |
| Causas | `erro_aplicacao`, `erro_operacao`, `falha_sistemica_veiculo`, `outro` |
| Responsável | tipo + nome; cobrança interna opcional |
| Estoque | Improcedente **nunca** grava lógica de estoque / `nf_entrada_globo` |
| KPIs | Dashboard + Relatórios (ano); ranking peças; custo por causa/responsável |
| Histórico planilha | Import CLI `import_planilha` → totais mensais (`HistoricoGarantiaMensal`), **não** cria `Garantia` |

### 1.2 Roteiro de perguntas (preencher na sessão)

| # | Pergunta | Resposta adotada (plano 100%; Matheus pode contrariar) |
|---|----------|------------------------------------------------------|
| Q1 | Quem pode **abrir** garantia no dia a dia? Perfis batem com a operação? | Oficina (+ admin). Compras não abre. |
| Q2 | Quem **fecha** improcedente? Só manutenção? Precisa segundo aprovador? | Manutenção (+ admin). Sem segundo aprovador no MVP. |
| Q3 | Causas atuais cobrem 100% dos casos? Falta alguma causa? | Manter as 4 causas; usar `outro` + texto até Matheus pedir novas. |
| Q4 | Cobrança interna: quando marcar? Quem vê? | Opcional no fechamento improcedente; visível na ficha para perfis com acesso à garantia. |
| Q5 | Remessa/retorno Globus: NF obrigatória antes de improcedente? | Recomendado vincular; **não** bloqueante no código atual. |
| Q6 | Prazo de garantia (regras peça/grupo/fornecedor/180d): valores oficiais? | Manter resolver atual + default 180d até Matheus informar tabela oficial. |
| Q7 | Reincidência (2 saídas): janela/dias e ação esperada estão corretos? | Manter detector atual; alertas → abrir garantia. |
| Q8 | Excel atual: é **linha a linha** (peça/NF/motivo) ou só **totais** tipo BASE GERAL? | Tratar BASE GERAL (totais) via `import_planilha`. |
| Q9 | Migrar casos antigos linha a linha? | **Não** no 100% mínimo — `SOMENTE_NOVOS`. |
| Q10 | Data de corte? | **2026-10-06**. |
| Q11 | Após o corte, papel da planilha? | **Opção A:** só consulta/histórico agregado (import); sem casos novos. |
| Q12 | Indicadores mínimos go-live? | Contagem por status, valor improcedente, top peças, histórico mensal (se importado). |

### 1.3 Critério de encerramento desta etapa

- Q1–Q12 respondidas (ou explicitamente “não se aplica”).
- Decisão binária em Q9 registrada na seção 3.
- Data de corte (Q10) ou justificativa de adiamento registrada na seção 2.

---

## 2. Playbook de cutover Excel → SGGI

### 2.1 Papel da planilha (escolher uma)

| Opção | Quando usar | Comportamento |
|-------|-------------|----------------|
| **A — Histórico agregado** | Planilha = BASE GERAL (totais mês/fornecedor/empresa) | Manter `import_planilha` para anos passados; Dashboard aba Histórico; **não** editar Excel para casos novos |
| **B — Desligar** | Operação aceita KPIs só do SGGI a partir da data de corte | Parar import; arquivar arquivo; só `Garantia` no app |

**Decisão adotada (plano 100%):** **Opção A — Histórico agregado**  
**Data de corte (`DATA_CORTE`):** **2026-10-06** (segunda-feira; ajustar só se Matheus exigir outra data)  
**Validação Matheus:** pendente de rubrica na seção 5 (defaults vigem até contradição explícita).

### 2.2 Passos operacionais

1. **Congelar Excel para escrita** na `DATA_CORTE` (permissão somente leitura ou arquivo em pasta arquivo).
2. **Comunicar** oficina/compras/manutenção: casos novos → SGGI (`/garantias/nova`).
3. Se Opção A: última importação `python manage.py import_planilha <arquivo.xlsx>` (dry-run antes).
4. Garantir `sync_globus` recente (compras/peças) para cruzamentos.
5. Semana 1 pós-corte: revisão diária — zero linhas novas no Excel; todos os novos casos no SGGI.
6. Após 30 dias: arquivar Excel; manter só SGGI (+ histórico importado se A).

### 2.3 Rollback

- Se bloqueio crítico de operação: reabrir Excel **somente** até correção, com registro de incidentes no SGGI quando possível.
- Não apagar dados do SGGI no rollback.

### 2.4 Responsáveis

| Papel | Nome | Contato |
|-------|------|---------|
| Sponsor ops | Matheus | `TBD` |
| Admin SGGI | `TBD` | |
| TI / sync Globus | `TBD` | |

---

## 3. Dados reais — decisão e especificação

### 3.1 Estado atual do banco (referência)

- Poucas `Garantia` reais (ex.: 1 improcedente em 2026 no ambiente local).
- `HistoricoGarantiaMensal` só existe após `import_planilha` com arquivo real.
- Filtro `/garantias?ano=2025` vazio = **sem registros daquele ano**, não bug de filtro.

### 3.2 Decisão padrão (recomendada até Matheus contrariar)

**Operar só casos novos no SGGI** + opcionalmente importar BASE GERAL (agregados).

- Não criar seed fake de 2024/2025.
- Não implementar import linha a linha sem arquivo/mapeamento real.

**Decisão final adotada (plano 100%):** `SOMENTE_NOVOS`  
(Migração linha a linha fica fora do 100% mínimo até existir arquivo mapeado.)

### 3.3 Se `SOMENTE_NOVOS` (caminho curto)

| Item | Ação |
|------|------|
| Código | Nenhuma mudança obrigatória |
| Ops | Cutover seção 2 |
| KPIs ano passado | Via aba Histórico (se Opção A) ou “não disponível linha a linha” |

### 3.4 Se `MIGRAR_LINHAS` (especificação para implementação futura)

Só inicia após Matheus fornecer **arquivo real** e confirmar colunas.

**Pré-requisitos**

- Arquivo Excel/CSV com uma linha = um caso.
- Mapeamento mínimo:

| Coluna origem (exemplo) | Campo SGGI |
|-------------------------|----------|
| Data / ano | `criado_em` / competência |
| Código peça | `Peca.codigo_interno` (+ espelho Globus) |
| Veículo | `Veiculo.codigo` |
| Fornecedor | `Fornecedor` |
| Status final | `improcedente` / outros |
| Motivo / causa | `motivo_improcedente`, `causa_improcedente` |
| NF remessa / retorno | `NotaFiscal` + vínculos |
| Valor | `valor_peca` |
| Protocolo legado (se houver) | `protocolo` ou observação |

**Regras de import**

- Dry-run obrigatório; rejeitados em CSV.
- Idempotência por chave estável (hash ou protocolo legado).
- Não movimentar estoque; não gravar no Oracle.
- `criado_em` = data real do caso (não “agora”).
- Agente executor: Backend Developer (após Domain Expert validar mapeamento).

**Fora de escopo até arquivo existir:** escrever o comando `import_*` de linhas.

---

## 4. Checklist de aceite operacional (volume real)

Usar após `DATA_CORTE` e com casos **reais** no SGGI (não seed).

### 4.1 Integridade improcedente

- [ ] Abrir garantia real com peça/veículo do espelho Globus
- [ ] Vincular remessa e retorno quando aplicável
- [ ] Fechar como **improcedente** com laudo + causa + motivo
- [ ] Confirmar: **não** preencheu `nf_entrada_globo` / não alterou estoque Globus
- [ ] Evento na timeline da ficha
- [ ] Perfil sem permissão **não** consegue fechar improcedente

### 4.2 Indicadores

- [ ] Dashboard ano corrente reflete a garantia criada
- [ ] KPI / ranking inclui a peça após o fechamento
- [ ] Relatório improcedentes × compras mostra cruzamento do espelho (quando houver compra)
- [ ] Filtro `ano` + `status=improcedente` lista só o ano filtrado
- [ ] Export CSV do ano ok (perfil direção/admin)

### 4.3 Globus read-only

- [ ] Badge / status: Oracle via `conf/` ok **ou** espelho SyncLog atualizado
- [ ] `sync_globus` sem erro nos tipos críticos (pelo menos `pecas`, `compras`)
- [ ] Nenhuma tentativa de escrita no Oracle no fluxo improcedente

### 4.4 Cutover Excel

- [ ] A partir de `DATA_CORTE`, zero casos novos no Excel (amostra / checklist semanal)
- [ ] Opção A ou B da seção 2 cumprida
- [ ] Equipe oficina/compras/manutenção treinada (roteiro curto)

### 4.5 Critério de go-live ops

Aceite = itens 4.1–4.4 marcados com evidência (protocolo SGGI + print/relatório) e assinatura Matheus (ou sponsor).

| Campo | Valor |
|-------|-------|
| Data aceite | `TBD` |
| Assinatura ops | `TBD — Matheus` |
| Observações | |

---

## 5. Rubrica Matheus (defaults já vigentes)

Os defaults da seção 1.2 e Opção A / `DATA_CORTE=2026-10-06` / `SOMENTE_NOVOS` **vigem para o go-live 100% mínimo**.

| Campo | Valor |
|-------|-------|
| Concordo com defaults | `TBD — Matheus` (Sim / Ajustes:) |
| Data da rubrica | `TBD` |
| Assinatura | `TBD — Matheus` |

Alterações pedidas por Matheus devem atualizar só as linhas conflitantes; o restante permanece.

---

## Próximo passo imediato

1. Matheus rubrica seção 5 (ou lista ajustes).  
2. Colocar o `.xlsx` BASE GERAL em `docs/ops/incoming/` e rodar `scripts/import_planilha_real.ps1`.  
3. Ativar tarefa agendada de sync (`scripts/register_sync_globus_task.ps1`).  
4. Rodar `scripts/aceite_golive_check.ps1` após primeiros casos reais.
