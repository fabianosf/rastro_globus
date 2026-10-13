#!/usr/bin/env python3
"""Gera docs/MANUAL_USUARIO_SGGI.pdf — manual de uso do aplicativo SGGI."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUT = Path(__file__).resolve().parent / "MANUAL_USUARIO_SGGI.pdf"

CYAN = colors.HexColor("#0e7490")
INK = colors.HexColor("#0f172a")
MUTED = colors.HexColor("#475569")
LINE = colors.HexColor("#cbd5e1")
PANEL = colors.HexColor("#f1f5f9")
AMBER = colors.HexColor("#b45309")
RED = colors.HexColor("#b91c1c")


def styles():
    base = getSampleStyleSheet()
    s = {
        "cover_title": ParagraphStyle(
            "cover_title",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=28,
            textColor=CYAN,
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
        "cover_sub": ParagraphStyle(
            "cover_sub",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=14,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            textColor=CYAN,
            spaceBefore=16,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            textColor=INK,
            spaceBefore=12,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=INK,
            alignment=TA_JUSTIFY,
            spaceAfter=6,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            textColor=INK,
            leftIndent=4,
        ),
        "note": ParagraphStyle(
            "note",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=9,
            leading=12,
            textColor=AMBER,
            spaceBefore=4,
            spaceAfter=8,
        ),
        "warn": ParagraphStyle(
            "warn",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=RED,
            spaceBefore=4,
            spaceAfter=8,
        ),
        "caption": ParagraphStyle(
            "caption",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            textColor=MUTED,
            alignment=TA_CENTER,
        ),
        "cell": ParagraphStyle(
            "cell",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=INK,
        ),
        "cell_h": ParagraphStyle(
            "cell_h",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=INK,
        ),
        "footer": ParagraphStyle(
            "footer",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            textColor=MUTED,
            alignment=TA_CENTER,
        ),
        "toc": ParagraphStyle(
            "toc",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=18,
            textColor=INK,
            leftIndent=10,
        ),
    }
    return s


def bullets(items: list[str], st) -> ListFlowable:
    return ListFlowable(
        [ListItem(Paragraph(i, st["bullet"]), leftIndent=12, value="•") for i in items],
        bulletType="bullet",
        start="•",
        leftIndent=10,
        spaceBefore=2,
        spaceAfter=8,
    )


def table(headers: list[str], rows: list[list[str]], st, col_widths=None) -> Table:
    data = [[Paragraph(h, st["cell_h"]) for h in headers]]
    for row in rows:
        data.append([Paragraph(c, st["cell"]) for c in row])
    t = Table(data, colWidths=col_widths, hAlign="LEFT", repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), PANEL),
                ("TEXTCOLOR", (0, 0), (-1, -1), INK),
                ("GRID", (0, 0), (-1, -1), 0.4, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


def add_page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawCentredString(
        A4[0] / 2,
        1.2 * cm,
        f"SGGI — Manual do Usuário  ·  página {doc.page}",
    )
    canvas.restoreState()


def build():
    st = styles()
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.8 * cm,
        bottomMargin=2 * cm,
        title="SGGI — Manual do Usuário",
        author="SGGI",
    )
    story = []
    W = A4[0] - 4 * cm

    # —— Capa ——
    story.append(Spacer(1, 4 * cm))
    story.append(Paragraph("SGGI", st["cover_title"]))
    story.append(Paragraph("Sistema de Gestão de Garantias Improcedentes", st["cover_sub"]))
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("Manual do Usuário", st["cover_title"]))
    story.append(Spacer(1, 6 * mm))
    story.append(
        Paragraph(
            "Como utilizar o aplicativo no dia a dia:<br/>"
            "cadastro de DANFE, ficha da garantia, alertas de reincidência e relatórios.",
            st["cover_sub"],
        )
    )
    story.append(Spacer(1, 2 * cm))
    story.append(
        Paragraph(
            "Versão alinhada às entregas de valor (alertas, custo do erro interno "
            "e encerramento improcedente em um passo).",
            st["caption"],
        )
    )
    story.append(Paragraph("Uso interno · PT-BR", st["caption"]))
    story.append(PageBreak())

    # —— Sumário ——
    story.append(Paragraph("Sumário", st["h1"]))
    for line in [
        "1. O que é o SGGI",
        "2. Acesso e login",
        "3. Perfis e permissões",
        "4. Menu e telas principais",
        "5. Status da garantia (fluxo)",
        "6. Registrar DANFE (remessa)",
        "7. Ficha da garantia — ações do dia a dia",
        "8. Fechar como improcedente",
        "9. Encerrar improcedente em um passo",
        "10. Procedente e cortesia",
        "11. Alertas de reincidência",
        "12. Relatórios e Custo do erro interno",
        "13. Regras importantes",
        "14. Problemas comuns",
    ]:
        story.append(Paragraph(line, st["toc"]))
    story.append(PageBreak())

    # —— 1 ——
    story.append(Paragraph("1. O que é o SGGI", st["h1"]))
    story.append(
        Paragraph(
            "O <b>SGGI</b> (Sistema de Gestão de Garantias Improcedentes) registra e acompanha "
            "garantias de peças enviadas ao fornecedor. O foco operacional é a <b>DANFE de remessa</b>, "
            "a análise da resposta do fornecedor e o fechamento do caso — em especial quando a "
            "garantia é <b>improcedente</b> (erro interno da empresa, não do fornecedor).",
            st["body"],
        )
    )
    story.append(
        Paragraph(
            "O sistema <b>não grava estoque no Globus</b>. Consultas ao Globus são somente leitura "
            "(busca de NF, peça, veículo). Decisões e laudos ficam no banco do SGGI.",
            st["body"],
        )
    )

    # —— 2 ——
    story.append(Paragraph("2. Acesso e login", st["h1"]))
    story.append(
        Paragraph(
            "Abra o endereço do SGGI no navegador (ex.: servidor interno da empresa). "
            "Na tela de login, informe usuário e senha. Após autenticar, o menu lateral "
            "mostra as opções disponíveis para o seu perfil.",
            st["body"],
        )
    )
    story.append(bullets([
        "No canto superior direito aparecem seu nome e o <b>perfil</b> (oficina, compras, manutenção, direção ou admin).",
        "Use <b>Sair</b> para encerrar a sessão.",
        "Se a tela pedir login de novo, a sessão expirou — entre novamente.",
    ], st))

    # —— 3 ——
    story.append(Paragraph("3. Perfis e permissões", st["h1"]))
    story.append(
        Paragraph(
            "Cada perfil vê o mesmo aplicativo, mas com botões e ações diferentes:",
            st["body"],
        )
    )
    story.append(
        table(
            ["Perfil", "Pode fazer"],
            [
                [
                    "Oficina",
                    "Registrar DANFE / nova garantia; editar ficha aberta; anexar arquivos.",
                ],
                [
                    "Compras",
                    "Editar ficha; vincular NFs; avançar status (enviada / em análise); cancelar (aberta/enviada).",
                ],
                [
                    "Manutenção",
                    "Criar/editar; avançar status; <b>fechar</b> procedente, improcedente ou cortesia; improcedente direto.",
                ],
                [
                    "Direção",
                    "Somente leitura (consultar listas, fichas, alertas e relatórios).",
                ],
                [
                    "Admin",
                    "Todas as ações acima.",
                ],
            ],
            st,
            col_widths=[3.2 * cm, W - 3.2 * cm],
        )
    )
    story.append(Spacer(1, 4 * mm))
    story.append(
        Paragraph(
            "Se um botão não aparece, em geral é porque o seu perfil não tem permissão — "
            "não é erro do sistema.",
            st["note"],
        )
    )

    # —— 4 ——
    story.append(Paragraph("4. Menu e telas principais", st["h1"]))
    story.append(
        table(
            ["Menu", "Para quê"],
            [
                ["Minhas NFs", "Lista de garantias / NFs cadastradas. Ponto de partida do dia a dia."],
                ["Registrar DANFE", "Cadastro rápido da remessa em garantia (oficina / manutenção / admin)."],
                ["Alertas de reincidência", "Mesma peça aplicada de novo no mesmo veículo no prazo de garantia."],
                ["Relatórios", "Rankings e visão consolidada."],
                ["Custo do erro interno", "Relatório dos casos improcedentes (custo da empresa)."],
            ],
            st,
            col_widths=[4.2 * cm, W - 4.2 * cm],
        )
    )
    story.append(Spacer(1, 3 * mm))
    story.append(
        Paragraph(
            "Ao clicar em uma linha da lista ou em “Abrir garantia”, você entra na "
            "<b>Ficha da NF</b> — tela completa com dados, histórico (timeline) e ações.",
            st["body"],
        )
    )

    # —— 5 ——
    story.append(Paragraph("5. Status da garantia (fluxo)", st["h1"]))
    story.append(
        Paragraph(
            "Cada garantia passa por status. O avanço normal é:",
            st["body"],
        )
    )
    story.append(
        Paragraph(
            "<b>aberta</b> → <b>enviada</b> → <b>em_analise</b> → "
            "<b>procedente</b> / <b>improcedente</b> / <b>cortesia</b>",
            st["body"],
        )
    )
    story.append(
        table(
            ["Status", "Significado"],
            [
                ["aberta", "Cadastrada; ainda falta marcar envio (NF de remessa)."],
                ["enviada", "Remessa ao fornecedor registrada."],
                ["em_analise", "Aguardando / em análise da resposta do fornecedor."],
                ["procedente", "Fornecedor aceitou — espelho de NF Globo (texto); sem estoque Globus."],
                ["improcedente", "Negada — custo interno (erro de aplicação, operação etc.)."],
                ["cortesia", "Fechamento comercial com observação."],
                ["cancelada", "Caso cancelado (em geral a partir de aberta/enviada)."],
            ],
            st,
            col_widths=[3.2 * cm, W - 3.2 * cm],
        )
    )
    story.append(Spacer(1, 3 * mm))
    story.append(
        Paragraph(
            "Para marcar <b>enviada</b> ou <b>em análise</b> é obrigatório ter a "
            "<b>NF de remessa</b> vinculada.",
            st["note"],
        )
    )

    story.append(PageBreak())

    # —— 6 ——
    story.append(Paragraph("6. Registrar DANFE (remessa)", st["h1"]))
    story.append(
        Paragraph(
            "Use quando a DANFE de remessa em garantia foi emitida (ex.: CFOP de remessa). "
            "Menu → <b>Registrar DANFE</b>.",
            st["body"],
        )
    )
    story.append(Paragraph("Passo a passo", st["h2"]))
    story.append(bullets([
        "Informe o <b>número da NF</b> de remessa.",
        "Use <b>Buscar no Globus</b> quando disponível (consulta somente leitura). Se houver várias NFs, escolha a correta na lista.",
        "Se <b>não</b> achar no Globus (comum quando a remessa existe só na DANFE), preencha manualmente: valor, peça, veículo (CARRO), fornecedor, NF de origem / compra e datas.",
        "Códigos de peça e veículo: digitar e salvar basta — não é obrigatório clicar na sugestão da lista.",
        "Confira os dados e clique em <b>Registrar remessa</b> (ou equivalente na tela).",
        "O sistema cria a garantia (em geral já em <b>enviada</b> com NF remessa) e abre a ficha.",
    ], st))
    story.append(
        Paragraph(
            "Não use o número da remessa como se fosse a NF de compra. A NF de origem "
            "é outro documento (compra / aplicação).",
            st["warn"],
        )
    )

    # —— 7 ——
    story.append(Paragraph("7. Ficha da garantia — ações do dia a dia", st["h1"]))
    story.append(
        Paragraph(
            "Na ficha você vê protocolo, status, peça, veículo, fornecedor, NFs, laudo, "
            "anexos e a <b>timeline</b> (histórico de mudanças de status).",
            st["body"],
        )
    )
    story.append(Paragraph("Seção Ações (resumo)", st["h2"]))
    story.append(bullets([
        "<b>Laudo (resumo)</b> — texto técnico; obrigatório para improcedente (ou PDF de laudo).",
        "<b>Marcar como enviada / em análise</b> — avanço do fluxo (compras / manutenção / admin).",
        "<b>Vincular NF</b> — remessa ou retorno (compras / admin).",
        "<b>Anexar PDF</b> — documentos da garantia.",
        "<b>Fechar procedente / improcedente / cortesia</b> — só manutenção / admin, em geral com status <b>em análise</b>.",
        "<b>Encerrar como improcedente (fornecedor já respondeu)</b> — atalho em <b>aberta</b> ou <b>enviada</b> (ver seção 9).",
    ], st))

    # —— 8 ——
    story.append(Paragraph("8. Fechar como improcedente", st["h1"]))
    story.append(
        Paragraph(
            "<b>Improcedente</b> significa: o custo é da empresa (erro interno), não do fornecedor. "
            "Causas típicas: erro de aplicação (oficina), erro de operação (motorista), "
            "falha sistêmica do veículo, ou outro.",
            st["body"],
        )
    )
    story.append(Paragraph("Checklist (fluxo normal)", st["h2"]))
    story.append(bullets([
        "Garantia em status <b>em análise</b>.",
        "Preencher o <b>laudo</b> (resumo e/ou PDF).",
        "Informar <b>causa</b>, <b>tipo de responsável</b> e <b>nome do responsável</b> "
        "(nome obrigatório, exceto quando o tipo for “sistema”).",
        "Opcional: cobrança interna e observação.",
        "Clicar em <b>Improcedente</b>.",
        "Conferir a timeline e, se for o caso, o relatório <b>Custo do erro interno</b>.",
    ], st))
    story.append(
        Paragraph(
            "Improcedente <b>nunca</b> grava lógica de estoque nem NF de entrada Globo.",
            st["warn"],
        )
    )

    # —— 9 ——
    story.append(Paragraph("9. Encerrar improcedente em um passo", st["h1"]))
    story.append(
        Paragraph(
            "Quando o fornecedor <b>já respondeu</b> e o caso ainda está <b>aberta</b> ou "
            "<b>enviada</b>, a manutenção (ou admin) pode usar o botão "
            "<b>Encerrar como improcedente (fornecedor já respondeu)</b>.",
            st["body"],
        )
    )
    story.append(
        Paragraph(
            "O sistema avança sozinho a timeline completa "
            "(enviada → em análise → improcedente, conforme o status atual), "
            "sem precisar clicar etapa por etapa.",
            st["body"],
        )
    )
    story.append(Paragraph("Exige", st["h2"]))
    story.append(bullets([
        "NF de remessa vinculada (o botão fica desabilitado sem remessa).",
        "Laudo: resumo e/ou arquivo PDF.",
        "Causa e responsável (mesmas regras do fechamento normal).",
    ], st))
    story.append(Paragraph("Opcional", st["h2"]))
    story.append(bullets([
        "Número e <b>data própria</b> da NF de retorno do fornecedor.",
        "Cobrança interna e observações.",
    ], st))

    story.append(PageBreak())

    # —— 10 ——
    story.append(Paragraph("10. Procedente e cortesia", st["h1"]))
    story.append(Paragraph("Procedente", st["h2"]))
    story.append(
        Paragraph(
            "Use quando o fornecedor aceitou a garantia. Informe o número espelho da "
            "<b>NF de entrada no Globo</b> (campo texto). Isso <b>não movimenta estoque</b> "
            "no Globus — é apenas registro no SGGI.",
            st["body"],
        )
    )
    story.append(Paragraph("Cortesia", st["h2"]))
    story.append(
        Paragraph(
            "Fechamento comercial. Exige observação. Também não grava estoque Globus.",
            st["body"],
        )
    )

    # —— 11 ——
    story.append(Paragraph("11. Alertas de reincidência", st["h1"]))
    story.append(
        Paragraph(
            "<b>Reincidência</b> = a mesma peça aplicada de novo no <b>mesmo veículo</b> "
            "dentro do prazo de garantia. O menu mostra um <b>badge</b> com a quantidade "
            "de alertas novos.",
            st["body"],
        )
    )
    story.append(bullets([
        "KPIs no topo: novos, garantias abertas a partir de alertas, valor estimado.",
        "Filtros por status, peça, fornecedor e empresa.",
        "Dias entre aplicações em destaque quando ≤ 30.",
        "<b>Abrir garantia</b> — vai para a ficha (quando houver vínculo).",
        "<b>Descartar</b> — exige motivo (ex.: falso positivo).",
        "Lista vazia: em geral ainda não houve sync Globus / detecção — não significa erro da tela.",
    ], st))

    # —— 12 ——
    story.append(Paragraph("12. Relatórios e Custo do erro interno", st["h1"]))
    story.append(Paragraph("Relatórios", st["h2"]))
    story.append(
        Paragraph(
            "Menu <b>Relatórios</b>: rankings e visão consolidada para acompanhamento gerencial.",
            st["body"],
        )
    )
    story.append(Paragraph("Custo do erro interno", st["h2"]))
    story.append(
        Paragraph(
            "Menu <b>Custo do erro interno</b>. Consolida garantias <b>improcedentes</b> do ano "
            "(total, valor, por causa, por mês, cobrança, vínculo com reincidência). "
            "Escolha o ano no filtro da tela.",
            st["body"],
        )
    )
    story.append(
        Paragraph(
            "Use este relatório para acompanhar quanto a empresa perdeu com erro interno "
            "e onde concentrar correção (oficina, motorista, peça, veículo).",
            st["note"],
        )
    )

    # —— 13 ——
    story.append(Paragraph("13. Regras importantes", st["h1"]))
    story.append(bullets([
        "<b>Nunca</b> o SGGI escreve no Oracle Globus (estoque / movimentos).",
        "Casos novos devem ser lançados no SGGI (não na planilha Excel legada).",
        "Improcedente = custo interno; procedente = fornecedor aceitou (espelho texto).",
        "Laudo é obrigatório para improcedente.",
        "NF de remessa é obrigatória para avançar enviada / em análise e para improcedente direto.",
        "Preserve anexos e laudos — não apagar pastas de mídia no servidor.",
    ], st))

    # —— 14 ——
    story.append(Paragraph("14. Problemas comuns", st["h1"]))
    story.append(
        table(
            ["Situação", "O que fazer"],
            [
                [
                    "Não vejo “Registrar DANFE”",
                    "Seu perfil pode ser compras ou direção. Peça a oficina/manutenção ou use perfil com permissão de criar.",
                ],
                [
                    "Botão de fechar não aparece",
                    "Só manutenção/admin fecham. Em análise: use procedente/improcedente/cortesia. Em aberta/enviada: use improcedente direto (manutenção).",
                ],
                [
                    "Erro pedindo NF de remessa",
                    "Vincule a NF de remessa na ficha (compras) ou informe o número antes de avançar / encerrar.",
                ],
                [
                    "Erro pedindo laudo",
                    "Preencha o resumo do laudo ou anexe o PDF antes de marcar improcedente.",
                ],
                [
                    "Busca Globus não acha a NF",
                    "Preencha manualmente. Remessa muitas vezes existe só na DANFE.",
                ],
                [
                    "Lista de alertas vazia",
                    "Aguarde o espelho/sync Globus e a detecção de reincidência; filtre por status “Novo”.",
                ],
            ],
            st,
            col_widths=[4.5 * cm, W - 4.5 * cm],
        )
    )
    story.append(Spacer(1, 8 * mm))
    story.append(
        Paragraph(
            "Em caso de dúvida operacional, fale com o responsável de manutenção / sponsor "
            "do processo de garantias na empresa.",
            st["body"],
        )
    )
    story.append(Spacer(1, 6 * mm))
    story.append(
        Paragraph(
            "— Fim do manual —",
            st["caption"],
        )
    )

    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    print(f"OK: {OUT}")


if __name__ == "__main__":
    build()
