#!/usr/bin/env python3
"""
Gera docs/MANUAL_USUARIO_SGGI.pdf — POP operacional do aplicativo (usuário final).
Uso: python docs/gerar_manual_usuario_sggi.py
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    Flowable,
    KeepTogether,
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

# Paleta próxima do app (claro no PDF para impressão)
CYAN = colors.HexColor("#0e7490")
CYAN_SOFT = colors.HexColor("#cffafe")
INK = colors.HexColor("#0f172a")
MUTED = colors.HexColor("#64748b")
LINE = colors.HexColor("#cbd5e1")
PANEL = colors.HexColor("#f8fafc")
AMBER = colors.HexColor("#b45309")
AMBER_SOFT = colors.HexColor("#fef3c7")
RED = colors.HexColor("#b91c1c")
RED_SOFT = colors.HexColor("#fee2e2")
GREEN = colors.HexColor("#15803d")
GREEN_SOFT = colors.HexColor("#dcfce7")
SIDEBAR = colors.HexColor("#0f172a")
SIDEBAR_TXT = colors.HexColor("#e2e8f0")
WHITE = colors.white


def styles():
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "cover_title",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=30,
            textColor=CYAN,
            alignment=TA_CENTER,
            spaceAfter=10,
        ),
        "cover_sub": ParagraphStyle(
            "cover_sub",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=13,
            textColor=MUTED,
            alignment=TA_CENTER,
            leading=18,
            spaceAfter=6,
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            textColor=CYAN,
            spaceBefore=4,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            textColor=INK,
            spaceBefore=10,
            spaceAfter=5,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=INK,
            spaceAfter=6,
        ),
        "step": ParagraphStyle(
            "step",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=CYAN,
            spaceBefore=4,
            spaceAfter=4,
        ),
        "tip": ParagraphStyle(
            "tip",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=AMBER,
            spaceBefore=2,
            spaceAfter=6,
        ),
        "warn": ParagraphStyle(
            "warn",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=RED,
            spaceBefore=2,
            spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "small",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=MUTED,
        ),
        "screen_title": ParagraphStyle(
            "screen_title",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=INK,
        ),
        "screen_muted": ParagraphStyle(
            "screen_muted",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            textColor=MUTED,
            leading=9,
        ),
        "screen_btn": ParagraphStyle(
            "screen_btn",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=CYAN,
            alignment=TA_CENTER,
        ),
        "nav": ParagraphStyle(
            "nav",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            textColor=SIDEBAR_TXT,
            leading=11,
        ),
        "nav_on": ParagraphStyle(
            "nav_on",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            textColor=colors.HexColor("#67e8f9"),
            leading=11,
        ),
        "caption": ParagraphStyle(
            "caption",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceBefore=3,
            spaceAfter=8,
        ),
        "toc": ParagraphStyle(
            "toc",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=18,
            textColor=INK,
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
            textColor=INK,
        ),
    }


class StepBadge(Flowable):
    """Círculo com número do passo."""

    def __init__(self, n: int, label: str, st):
        super().__init__()
        self.n = n
        self.label = label
        self.st = st
        self.width = 16 * cm
        self.height = 18

    def draw(self):
        c = self.canv
        c.setFillColor(CYAN)
        c.circle(9, 7, 8, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(9, 4, str(self.n))
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(22, 4, self.label)


class ScreenFrame(Flowable):
    """Mock de tela do SGGI: sidebar + área principal."""

    def __init__(
        self,
        title: str,
        menu_active: str,
        body_lines: list[str],
        buttons: list[str] | None = None,
        highlight: str | None = None,
        width: float | None = None,
        height: float = 6.2 * cm,
    ):
        super().__init__()
        self.title = title
        self.menu_active = menu_active
        self.body_lines = body_lines
        self.buttons = buttons or []
        self.highlight = highlight
        self.width = width or (17 * cm)
        self.height = height
        self.menus = [
            "Minhas NFs",
            "Nova remessa",
            "Reincidências",
            "Relatórios",
        ]

    def draw(self):
        c = self.canv
        w, h = self.width, self.height
        # moldura
        c.setStrokeColor(LINE)
        c.setFillColor(PANEL)
        c.roundRect(0, 0, w, h, 4, fill=1, stroke=1)

        # sidebar
        sw = 3.4 * cm
        c.setFillColor(SIDEBAR)
        c.rect(0, 0, sw, h, fill=1, stroke=0)
        c.setFillColor(CYAN)
        c.roundRect(6, h - 22, 22, 14, 2, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 6)
        c.drawCentredString(17, h - 17, "SGGI")
        c.setFillColor(SIDEBAR_TXT)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(32, h - 16, "SGGI")

        y = h - 38
        for m in self.menus:
            on = m == self.menu_active
            if on:
                c.setFillColor(colors.HexColor("#164e63"))
                c.roundRect(4, y - 3, sw - 8, 12, 2, fill=1, stroke=0)
                c.setFillColor(colors.HexColor("#67e8f9"))
                c.setFont("Helvetica-Bold", 6.5)
            else:
                c.setFillColor(SIDEBAR_TXT)
                c.setFont("Helvetica", 6.5)
            c.drawString(8, y, m[:22])
            y -= 14

        # header
        c.setFillColor(WHITE)
        c.rect(sw, h - 22, w - sw, 22, fill=1, stroke=0)
        c.setStrokeColor(LINE)
        c.line(sw, h - 22, w, h - 22)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(sw + 8, h - 14, self.title)
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 7)
        c.drawRightString(w - 8, h - 14, "usuario · perfil   [ Sair ]")

        # body
        by = h - 36
        c.setFillColor(INK)
        for line in self.body_lines:
            if line.startswith("##"):
                c.setFont("Helvetica-Bold", 8)
                c.setFillColor(CYAN)
                c.drawString(sw + 8, by, line[2:].strip())
                c.setFillColor(INK)
            elif line.startswith(">>"):
                c.setFillColor(AMBER_SOFT)
                c.roundRect(sw + 6, by - 3, w - sw - 14, 12, 2, fill=1, stroke=0)
                c.setFillColor(AMBER)
                c.setFont("Helvetica-Bold", 7)
                c.drawString(sw + 10, by, line[2:].strip()[:70])
                c.setFillColor(INK)
            elif line.startswith("!!"):
                c.setFillColor(RED_SOFT)
                c.roundRect(sw + 6, by - 3, w - sw - 14, 12, 2, fill=1, stroke=0)
                c.setFillColor(RED)
                c.setFont("Helvetica", 7)
                c.drawString(sw + 10, by, line[2:].strip()[:70])
                c.setFillColor(INK)
            elif line.startswith("ok"):
                c.setFillColor(GREEN_SOFT)
                c.roundRect(sw + 6, by - 3, w - sw - 14, 12, 2, fill=1, stroke=0)
                c.setFillColor(GREEN)
                c.setFont("Helvetica", 7)
                c.drawString(sw + 10, by, line[2:].strip()[:70])
                c.setFillColor(INK)
            else:
                c.setFont("Helvetica", 7.5)
                c.setFillColor(MUTED if line.startswith("·") else INK)
                c.drawString(sw + 8, by, line[:78])
            by -= 11
            if by < 28:
                break

        # buttons
        if self.buttons:
            bx = sw + 8
            for btn in self.buttons:
                hot = self.highlight and btn == self.highlight
                tw = max(52, len(btn) * 4.2 + 16)
                c.setFillColor(CYAN_SOFT if hot else WHITE)
                c.setStrokeColor(CYAN if hot else LINE)
                c.roundRect(bx, 8, tw, 14, 3, fill=1, stroke=1)
                c.setFillColor(CYAN)
                c.setFont("Helvetica-Bold", 6.5)
                c.drawCentredString(bx + tw / 2, 12, btn)
                bx += tw + 6


def tip_box(text: str, st, kind="tip"):
    bg = AMBER_SOFT if kind == "tip" else RED_SOFT
    fg = st["tip"] if kind == "tip" else st["warn"]
    prefix = "Dica: " if kind == "tip" else "Atenção: "
    t = Table(
        [[Paragraph(prefix + text, fg)]],
        colWidths=[16.5 * cm],
    )
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), bg),
                ("BOX", (0, 0), (-1, -1), 0.5, AMBER if kind == "tip" else RED),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return t


def bullets(items: list[str], st):
    return ListFlowable(
        [ListItem(Paragraph(i, st["body"]), leftIndent=8, value="•") for i in items],
        bulletType="bullet",
        start="•",
        leftIndent=8,
        spaceAfter=6,
    )


def simple_table(headers, rows, st, widths):
    data = [[Paragraph(h, st["cell_h"]) for h in headers]]
    for r in rows:
        data.append([Paragraph(c, st["cell"]) for c in r])
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), PANEL),
                ("GRID", (0, 0), (-1, -1), 0.4, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return t


def page_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawCentredString(
        A4[0] / 2,
        1.15 * cm,
        f"SGGI — POP do aplicativo (usuário)  ·  v1.1  ·  página {doc.page}",
    )
    canvas.restoreState()


def build():
    st = styles()
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.8 * cm,
        title="SGGI — POP do aplicativo (usuário final)",
        author="SGGI",
    )
    story: list = []

    # —— CAPA ——
    story.append(Spacer(1, 2.6 * cm))
    story.append(Paragraph("SGGI", st["cover_title"]))
    story.append(
        Paragraph("Sistema de Gestão de Garantias Improcedentes", st["cover_sub"])
    )
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("POP do aplicativo", st["cover_title"]))
    story.append(
        Paragraph("Procedimento operacional — usuário final", st["cover_sub"])
    )
    story.append(Spacer(1, 6 * mm))
    story.append(
        Paragraph(
            "Guia visual passo a passo — com telas ilustradas —<br/>"
            "para cadastrar DANFE, conferir foto/anexos na ficha, ver histórico Globus,<br/>"
            "alertas de reincidência e o custo do erro interno.",
            st["cover_sub"],
        )
    )
    story.append(Spacer(1, 1.2 * cm))
    story.append(
        tip_box(
            "O SGGI não movimenta estoque do Globus. Ele só registra o rastro da garantia "
            "e consulta o Globus em modo leitura.",
            st,
            "tip",
        )
    )
    story.append(Spacer(1, 8 * mm))
    story.append(
        Paragraph(
            "Versão <b>1.1</b> · 14/10/2026 · Uso interno · Português (Brasil)",
            st["caption"],
        )
    )
    story.append(PageBreak())

    # —— SUMÁRIO ——
    story.append(Paragraph("Como usar este POP", st["h1"]))
    story.append(
        Paragraph(
            "Siga os passos na ordem. Cada etapa mostra uma <b>tela ilustrada</b> parecida "
            "com o aplicativo e indica onde clicar.",
            st["body"],
        )
    )
    story.append(Paragraph("Sumário", st["h2"]))
    for line in [
        "1. Entrar no sistema",
        "2. Menu lateral — onde fica cada coisa",
        "3. Quem faz o quê (perfis)",
        "4. Fluxo completo em 1 minuto",
        "5. Registrar DANFE (remessa)",
        "6. Minhas NFs — lista e abrir ficha",
        "7. Ficha — foto / anexos da nota",
        "8. Ficha — histórico Globus",
        "9. Avançar status e fechar o caso",
        "10. Encerrar improcedente em um passo",
        "11. Alertas de reincidência",
        "12. Custo do erro interno",
        "13. Problemas comuns",
    ]:
        story.append(Paragraph(line, st["toc"]))
    story.append(PageBreak())

    # —— 1 LOGIN ——
    story.append(Paragraph("1. Entrar no sistema", st["h1"]))
    story.append(StepBadge(1, "Abra o endereço do SGGI no navegador", st))
    story.append(Spacer(1, 4))
    story.append(
        Paragraph(
            "Peça o link ao TI (local: <b>http://localhost:5173</b> ou o servidor da empresa).",
            st["body"],
        )
    )
    story.append(StepBadge(2, "Informe usuário e senha → Entrar", st))
    story.append(Spacer(1, 4))
    story.append(
        ScreenFrame(
            "Login",
            "",
            [
                "## Tela de acesso",
                "· Campo Usuário",
                "· Campo Senha",
                "· Botão Entrar",
                "",
                ">> Após o login você cai em Minhas NFs",
            ],
            buttons=["Entrar"],
            highlight="Entrar",
            height=5.2 * cm,
        )
    )
    story.append(Paragraph("Figura — tela de login (ilustração)", st["caption"]))
    story.append(
        tip_box(
            "No canto superior direito aparecem seu nome e o perfil (oficina, compras, "
            "manutenção…). Use Sair ao terminar.",
            st,
        )
    )
    story.append(PageBreak())

    # —— 2 MENU ——
    story.append(Paragraph("2. Menu lateral — onde fica cada coisa", st["h1"]))
    story.append(
        ScreenFrame(
            "Minhas NFs",
            "Minhas NFs",
            [
                "## Lista de garantias / NFs",
                "· Protocolo · NF remessa · Peça · CARRO · Status",
                "· Botões Editar / Excluir (conforme perfil)",
                "",
                "ok Lista vazia = ainda não há caso real cadastrado",
            ],
            buttons=[],
            height=5.5 * cm,
        )
    )
    story.append(Paragraph("Figura — menu à esquerda + área principal", st["caption"]))
    story.append(
        simple_table(
            ["Menu", "Para quê"],
            [
                ["Minhas NFs", "Ver todas as garantias cadastradas"],
                ["Nova remessa", "Cadastrar a remessa (DANFE) — oficina/manutenção"],
                ["Reincidências", "Mesma peça no mesmo veículo no prazo"],
                [
                    "Relatórios",
                    "Abas: Custo do erro interno (padrão) e Rankings",
                ],
            ],
            st,
            [4.5 * cm, 12 * cm],
        )
    )
    story.append(PageBreak())

    # —— 3 PERFIS ——
    story.append(Paragraph("3. Quem faz o quê (perfis)", st["h1"]))
    story.append(
        Paragraph(
            "Se um botão não aparece, em geral é o perfil — não é erro do sistema.",
            st["body"],
        )
    )
    story.append(
        simple_table(
            ["Perfil", "Pode"],
            [
                ["Oficina", "Registrar DANFE, editar ficha aberta, anexar"],
                ["Compras", "Vincular NFs, marcar enviada / em análise"],
                ["Manutenção", "Fechar procedente / improcedente / cortesia + atalho direto"],
                ["Direção", "Só consultar (leitura)"],
                ["Admin", "Tudo"],
            ],
            st,
            [3.5 * cm, 13 * cm],
        )
    )
    story.append(Spacer(1, 6 * mm))

    # —— 4 FLUXO ——
    story.append(Paragraph("4. Fluxo completo em 1 minuto", st["h1"]))
    story.append(
        Paragraph(
            "<b>Oficina</b> registra DANFE → <b>Compras</b> avança (enviada → em análise) → "
            "<b>Manutenção</b> olha Histórico Globus e fecha (procedente / improcedente / cortesia).",
            st["body"],
        )
    )
    story.append(
        Paragraph(
            "Status: <b>aberta</b> → <b>enviada</b> → <b>em análise</b> → "
            "<b>procedente</b> / <b>improcedente</b> / <b>cortesia</b>",
            st["body"],
        )
    )
    story.append(
        tip_box(
            "Improcedente = custo interno da empresa (erro de aplicação, operação, etc.), "
            "não do fornecedor.",
            st,
        )
    )
    story.append(PageBreak())

    # —— 5 DANFE ——
    story.append(Paragraph("5. Registrar DANFE (remessa)", st["h1"]))
    story.append(
        Paragraph(
            "Use quando a DANFE de remessa em garantia foi emitida. Menu → <b>Nova remessa</b>.",
            st["body"],
        )
    )
    story.append(StepBadge(1, "Digite o número da NF de remessa", st))
    story.append(Spacer(1, 3))
    story.append(StepBadge(2, "Buscar no Globus (ou preencher na mão se não achar)", st))
    story.append(Spacer(1, 3))
    story.append(StepBadge(3, "Confira peça, CARRO, fornecedor, valor e NF origem", st))
    story.append(Spacer(1, 3))
    story.append(
        StepBadge(4, "Observação (opcional) e anexe a foto/PDF — confira a prévia", st)
    )
    story.append(Spacer(1, 3))
    story.append(StepBadge(5, "Clique em Registrar remessa", st))
    story.append(Spacer(1, 6))
    story.append(
        ScreenFrame(
            "Nova remessa",
            "Nova remessa",
            [
                "## Remessa em garantia (DANFE)",
                "· Nº NF remessa: [ 87002____________ ]",
                "· [ Buscar no Globus ]",
                "· Peça / CARRO / Fornecedor / Valor",
                "· NF origem (compra) — outro número!",
                "· Observação (opcional)",
                "· Anexo: prévia da foto/PDF antes de enviar",
                "",
                ">> Confira a prévia — troque ou remova se estiver errado",
            ],
            buttons=["Buscar no Globus", "Registrar remessa"],
            highlight="Registrar remessa",
            height=7.2 * cm,
        )
    )
    story.append(Paragraph("Figura — cadastro da DANFE", st["caption"]))
    story.append(
        tip_box(
            "Código de peça ou CARRO: digitar e salvar basta — não precisa clicar na sugestão. "
            "A prévia do anexo aparece na própria tela de cadastro (antes de gravar).",
            st,
        )
    )
    story.append(PageBreak())

    # —— 6 LISTA ——
    story.append(Paragraph("6. Minhas NFs — lista e abrir ficha", st["h1"]))
    story.append(
        Paragraph(
            "Menu → <b>Minhas NFs</b>. Clique na linha ou em <b>Editar</b> para abrir a ficha completa.",
            st["body"],
        )
    )
    story.append(
        ScreenFrame(
            "Minhas NFs",
            "Minhas NFs",
            [
                "## Suas garantias",
                "· Protocolo | NF remessa | Peça | CARRO | Valor | Status",
                "· GAR-2026-xxxx | 87002 | 0111… | 47624 | R$ … | Enviada",
                "",
                "ok Clique na linha para abrir a Ficha da NF",
            ],
            buttons=["Editar", "Excluir"],
            highlight="Editar",
            height=5.5 * cm,
        )
    )
    story.append(Paragraph("Figura — lista Minhas NFs", st["caption"]))
    story.append(PageBreak())

    # —— 7 ANEXOS NA FICHA ——
    story.append(Paragraph("7. Ficha — foto / anexos da nota", st["h1"]))
    story.append(
        Paragraph(
            "Ao abrir a ficha, logo após o banner <b>O que fazer agora</b>, confira o bloco "
            "<b>Foto / anexos da nota</b>. A foto fica visível no topo — não precisa rolar "
            "até o fim da página.",
            st["body"],
        )
    )
    story.append(StepBadge(1, "Veja a prévia (imagem ou PDF) no topo da ficha", st))
    story.append(Spacer(1, 3))
    story.append(
        StepBadge(2, "Use Abrir, Trocar ou Excluir (perfil com permissão de anexar)", st)
    )
    story.append(Spacer(1, 3))
    story.append(
        StepBadge(3, "Se aparecer “Nenhuma foto anexada”, envie pelo picker com prévia", st)
    )
    story.append(Spacer(1, 6))
    story.append(
        ScreenFrame(
            "Ficha da NF",
            "Minhas NFs",
            [
                "## O que fazer agora",
                "· Próximo passo sugerido…",
                "",
                "## Foto / anexos da nota",
                "· [ prévia da imagem / PDF ]",
                "· Abrir  ·  Trocar  ·  Excluir",
                "",
                "!! Sem anexo → aviso amarelo + campo para enviar",
            ],
            buttons=["Abrir", "Trocar", "Excluir", "Enviar anexo"],
            highlight="Trocar",
            height=7.0 * cm,
        )
    )
    story.append(Paragraph("Figura — bloco Foto / anexos no topo da ficha", st["caption"]))
    story.append(
        bullets(
            [
                "<b>Abrir</b> — abre o arquivo em nova aba.",
                "<b>Trocar</b> — escolhe um novo arquivo; o sistema remove o antigo e grava o novo.",
                "<b>Excluir</b> — pede confirmação e apaga o anexo (e o arquivo).",
                "Anexos DOC/outros: cartão com nome + Abrir (sem prévia fiel).",
            ],
            st,
        )
    )
    story.append(
        tip_box(
            "Quem não tem permissão de anexar só visualiza/abre. Em Ações, há um lembrete "
            "apontando para esta seção no topo.",
            st,
        )
    )
    story.append(PageBreak())

    # —— 8 HISTÓRICO ——
    story.append(Paragraph("8. Ficha — Histórico Globus", st["h1"]))
    story.append(
        Paragraph(
            "Na ficha, <b>antes</b> de fechar o caso, role até o bloco "
            "<b>Histórico Globus (peça / veículo)</b>.",
            st["body"],
        )
    )
    story.append(
        ScreenFrame(
            "Ficha da NF",
            "Minhas NFs",
            [
                "## ▸ Consultar histórico no Globus (opcional)",
                "· Recolhido por padrão — abra se precisar",
                "· Peça · Veículo · reincidências",
                "· Saídas e compras (espelho)",
                "",
                "ok Consulta só leitura — não altera estoque",
            ],
            buttons=["Atualizar espelho", "Ao vivo"],
            highlight="Atualizar espelho",
            height=6.5 * cm,
        )
    )
    story.append(Paragraph("Figura — painel Histórico Globus na ficha", st["caption"]))
    story.append(bullets([
        "<b>Atualizar espelho</b> — lê o MariaDB (sync_globus).",
        "<b>Atualizar do Globus (ao vivo)</b> — tenta Oracle; se falhar, mantém o espelho.",
        "Isso ajuda a ver se a peça já saiu neste CARRO — o <b>laudo</b> continua sendo da manutenção.",
    ], st))
    story.append(PageBreak())

    # —— 9 FECHAR ——
    story.append(Paragraph("9. Avançar status e fechar o caso", st["h1"]))
    story.append(Paragraph("Compras / manutenção — seção Ações", st["h2"]))
    story.append(bullets([
        "Com NF remessa: <b>Marcar como enviada</b>",
        "Depois: <b>Marcar em análise</b>",
        "Em análise (só manutenção/admin): preencher laudo e fechar",
    ], st))
    story.append(
        ScreenFrame(
            "Ficha da NF — Ações",
            "Minhas NFs",
            [
                "## Ações",
                "· Laudo (resumo) — obrigatório para improcedente",
                "· Descrição / observação",
                "",
                "## Em análise — decisão",
                "· Fechar procedente (NF espelho Globo — texto)",
                "· Fechar improcedente / cortesia",
            ],
            buttons=["Marcar em análise", "Improcedente", "Procedente", "Cortesia"],
            highlight="Improcedente",
            height=6.6 * cm,
        )
    )
    story.append(Paragraph("Figura — seção Ações na ficha", st["caption"]))
    story.append(
        tip_box(
            "Procedente: informe só o número espelho da NF de entrada no Globo. "
            "O SGGI não dá entrada no estoque.",
            st,
        )
    )
    story.append(
        tip_box(
            "Improcedente exige laudo (texto e/ou PDF) + causa + responsável.",
            st,
            "warn",
        )
    )
    story.append(PageBreak())

    # —— 10 DIRETO ——
    story.append(Paragraph("10. Encerrar improcedente em um passo", st["h1"]))
    story.append(
        Paragraph(
            "Quando o fornecedor <b>já respondeu</b> e o status ainda é <b>aberta</b> ou "
            "<b>enviada</b>, a manutenção pode usar o atalho (sem clicar etapa a etapa).",
            st["body"],
        )
    )
    story.append(
        ScreenFrame(
            "Ficha da NF — Ações",
            "Minhas NFs",
            [
                "## Encerrar como improcedente",
                "## (fornecedor já respondeu)",
                "· Causa · Responsável · Cobrança interna",
                "· Laudo PDF (opcional) · NF retorno + data",
                "",
                "!! Exige NF de remessa + laudo",
            ],
            buttons=["Fechar improcedente agora"],
            highlight="Fechar improcedente agora",
            height=6.2 * cm,
        )
    )
    story.append(Paragraph("Figura — atalho improcedente direto", st["caption"]))
    story.append(
        Paragraph(
            "O sistema gera a timeline completa (enviada → em análise → improcedente) "
            "sozinho. Continua sem gravar estoque Globus.",
            st["body"],
        )
    )
    story.append(PageBreak())

    # —— 11 ALERTAS ——
    story.append(Paragraph("11. Alertas de reincidência", st["h1"]))
    story.append(
        Paragraph(
            "Mesma peça aplicada de novo no <b>mesmo veículo</b> dentro do prazo. "
            "Menu → <b>Reincidências</b> (badge com quantidade de novos).",
            st["body"],
        )
    )
    story.append(
        ScreenFrame(
            "Reincidências",
            "Reincidências",
            [
                "## KPIs: Novos | Garantias abertas | Valor estimado",
                "· Filtros: status, peça, fornecedor, empresa",
                "· Lista: CARRO · peça · dias entre · valor",
                "· Dias ≤ 30 em destaque",
                "",
                "ok Abrir garantia · Descartar (motivo obrigatório)",
            ],
            buttons=["Filtrar", "Abrir garantia", "Descartar"],
            highlight="Abrir garantia",
            height=6.2 * cm,
        )
    )
    story.append(Paragraph("Figura — tela de alertas", st["caption"]))
    story.append(PageBreak())

    # —— 12 ERRO INTERNO ——
    story.append(Paragraph("12. Custo do erro interno", st["h1"]))
    story.append(
        Paragraph(
            "Menu → <b>Relatórios</b> (aba Custo do erro interno). Soma as garantias "
            "já fechadas como <b>improcedente</b> no ano (custo da empresa).",
            st["body"],
        )
    )
    story.append(
        ScreenFrame(
            "Custo do erro interno",
            "Relatórios",
            [
                "## Abas: Custo do erro interno | Rankings",
                "· Ano [ 2026 ▼ ]  [ Imprimir ]",
                "· Custo total · Quantidade · % cobrado",
                "· Gráficos e tops",
                "",
                "ok Só entra caso real fechado como improcedente",
            ],
            buttons=["Imprimir"],
            height=6.0 * cm,
        )
    )
    story.append(Paragraph("Figura — relatório Custo do erro interno", st["caption"]))
    story.append(
        tip_box(
            "Se o total estiver R$ 0,00, ainda não há improcedente real no ano — "
            "está correto.",
            st,
        )
    )
    story.append(PageBreak())

    # —— 13 FAQ ——
    story.append(Paragraph("13. Problemas comuns", st["h1"]))
    story.append(
        simple_table(
            ["Situação", "O que fazer"],
            [
                [
                    "Não vejo Registrar DANFE",
                    "Perfil compras/direção não cria. Use oficina, manutenção ou admin.",
                ],
                [
                    "Não consigo fechar",
                    "Só manutenção/admin. Em aberta/enviada use o atalho improcedente direto.",
                ],
                [
                    "Pede NF de remessa",
                    "Vincule a remessa na ficha (compras) antes de avançar ou encerrar.",
                ],
                [
                    "Pede laudo",
                    "Preencha o resumo ou anexe o PDF na seção Ações.",
                ],
                [
                    "Não vejo a foto na ficha",
                    "Olhe o bloco Foto / anexos no topo (após O que fazer agora). Use Abrir se a prévia falhar.",
                ],
                [
                    "Nenhuma foto anexada",
                    "Envie pelo picker no mesmo bloco (com prévia) ou no cadastro da remessa.",
                ],
                [
                    "Globus não acha a NF",
                    "Preencha na mão. Remessa muitas vezes só existe na DANFE.",
                ],
                [
                    "Histórico Globus vazio",
                    "Peça ao TI para rodar sync_globus / detectar_reincidencia.",
                ],
                [
                    "Lista Minhas NFs vazia",
                    "Normal se ainda não cadastrou caso real. Use Registrar DANFE.",
                ],
            ],
            st,
            [4.8 * cm, 11.7 * cm],
        )
    )
    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph("Lembrete final", st["h2"]))
    story.append(bullets([
        "Globus = estoque. SGGI = rastro da garantia.",
        "Improcedente nunca grava estoque / NF de entrada Globo.",
        "Confira a foto/anexo no topo da ficha antes de avançar o status.",
        "Use o Histórico Globus na ficha para apoiar a decisão — o laudo é humano.",
    ], st))
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("— Fim do POP do aplicativo. Bom trabalho! —", st["caption"]))

    doc.build(story, onFirstPage=page_footer, onLaterPages=page_footer)
    print(f"OK: {OUT}")
    return OUT


if __name__ == "__main__":
    build()
