# Operação diária — casos novos só no SGGI

**Vigência:** a partir de `DATA_CORTE` = **2026-10-06** (ver [programa-cutover-improcedentes.md](programa-cutover-improcedentes.md)).

## Superfície do app (MVP)

| Onde | Uso |
|------|-----|
| **Menu** | Só **Dashboard** (`/`) |
| **SGGI ao vivo** | Fila, KPIs · CTAs: Abrir fila · Todas as garantias · **Registrar DANFE** · Nova garantia |
| **Histórico e export** | Planilha + cruzamento improcedentes × compras + CSV / Imprimir PDF |
| **Rotas** | `/garantias`, `/garantias/nova-danfe`, `/garantias/nova`, `/garantias/:id` |

Fora do app (redirect): reincidência Globus, regras de prazo, movimentos Globus, relatórios soltos.

## Fluxo DANFE (remessa em garantia)

1. Emitiu DANFE de remessa (ex. CFOP 5949, “REMESSA EM GARANTIA”) → Dashboard → **Registrar DANFE**.
2. Digite o **nº da NF** → **Buscar no Globus** (ou Enter): só NFs de garantia (NEG/NFG). Se houver várias, escolha na lista.
3. Se **não** achar no Globus (comum em remessa só na DANFE), **digite** valor, peça, CARRO, fornecedor, NF origem — não preenche NF de compra com o mesmo número.
4. **Registrar remessa** → cria `Garantia` no MariaDB com status **enviada** e NF remessa vinculada.
5. Seguir na ficha até **em análise**.
6. Se o fornecedor negar → manutenção fecha **improcedente** (laudo + causa). Isso **não** é automático na remessa.

Códigos de peça / CARRO: digitar e salvar basta (não é obrigatório clicar na sugestão).

## Regra

| Antes do corte | Depois do corte |
|----------------|-----------------|
| Excel + SGGI (transição) | **Só SGGI** para casos novos |
| Planilha pode receber lançamentos | Planilha **somente leitura** / arquivo; históricos via import BASE GERAL |

## Quem faz o quê

| Perfil | Ação no app |
|--------|-------------|
| Oficina / Compras | Dashboard → **Registrar DANFE** (ou Nova garantia) |
| Compras | Ficha: avançar / NFs retorno |
| Manutenção | Fechar procedente / improcedente / cortesia na ficha |
| Direção | Dashboard (vivo + histórico/export) — leitura |

## Improcedente (checklist rápido)

1. Caso já em `em_analise` (Dashboard → Abrir fila).
2. Laudo + motivo + causa na seção **Ações**.
3. **Não** pede entrada no estoque Globus.
4. Conferir KPIs / Histórico e export.

## Excel

- Não criar linhas novas após a data de corte.
- Totais históricos: TI roda `scripts/import_planilha_real.ps1`.
- No app: **Dashboard → Histórico e export**.

## Contato

Sponsor ops: Matheus (rubrica no programa de cutover).
