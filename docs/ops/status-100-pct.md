# Status execução — plano 100%

Atualizado na implementação dos scripts/docs (sem inventar dados).

| Todo | Status | Evidência |
|------|--------|-----------|
| SOP + DATA_CORTE | Fechado com defaults do plano | `programa-cutover-improcedentes.md` Q1–Q12, Opção A, `DATA_CORTE=2026-10-06`, rubrica Matheus pendente §5 |
| Import planilha real | Feito | `GARANTIA 2026.xlsx` → 1589 linhas Historico + 127 fornecedores; API historico 2025/2026 OK |
| Ops diária novos no RG | Entregue | `operacao-diaria-novos-rg.md` |
| Sync + cron | Entregue | Tarefa Windows `RastroGlobus-SyncGlobus` 06:30; job `sync_globus_job.ps1`; sync `saidas` em andamento (espelho >2M linhas) |
| Aceite go-live | Script + checks auto | `aceite_golive_check.ps1`; manuais (treino/Excel/rubrica) com ops |

## Ação humana restante

1. Matheus: rubrica §5 do programa cutover.  
2. Copiar `GARANTIA-*.xlsx` → `docs/ops/incoming/` e rodar `.\scripts\import_planilha_real.ps1`.  
3. Comunicar cutover 2026-10-06.  
4. Rodar `.\scripts\aceite_golive_check.ps1` de novo após import + primeiros casos reais.
