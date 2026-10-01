# Operação diária — casos novos só no RastroGlobus

**Vigência:** a partir de `DATA_CORTE` = **2026-10-06** (ver [programa-cutover-improcedentes.md](programa-cutover-improcedentes.md)).

## Regra

| Antes do corte | Depois do corte |
|----------------|-----------------|
| Excel + RG (transição) | **Só RG** para casos novos |
| Planilha pode receber lançamentos | Planilha **somente leitura** / arquivo; históricos via import BASE GERAL |

## Quem faz o quê

| Perfil | Ação no app |
|--------|-------------|
| Oficina | Nova garantia → `/garantias/nova` |
| Compras | Vincular NFs remessa/retorno na ficha |
| Manutenção | Fechar procedente / improcedente / cortesia |
| Direção | Dashboard + Relatórios + CSV (leitura) |

## Improcedente (checklist rápido)

1. Garantia em `em_analise`.
2. Laudo (resumo ou PDF) + motivo + causa.
3. Confirmar: **não** pede entrada no estoque Globus.
4. Conferir no Dashboard/Relatórios do ano.

## Excel

- Não criar linhas novas após a data de corte.
- Totais históricos: TI roda `scripts/import_planilha_real.ps1` com o arquivo oficial.

## Contato

Sponsor ops: Matheus (rubrica no programa de cutover).
