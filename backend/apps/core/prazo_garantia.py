"""Resolucao de prazo de garantia e data_fim."""

from __future__ import annotations

from datetime import date, timedelta

from .models import Fornecedor, Peca, PecaGlobus, RegraPrazoGarantia

FALLBACK_PRAZO_DIAS = 180
ESCOPO_ORDEM = (
    RegraPrazoGarantia.Escopo.PECA,
    RegraPrazoGarantia.Escopo.GRUPO_PECA,
    RegraPrazoGarantia.Escopo.FORNECEDOR,
    RegraPrazoGarantia.Escopo.TIPO_SERVICO,
)


def calcular_data_fim_garantia(data_aplicacao: date, prazo_dias: int) -> date:
    return data_aplicacao + timedelta(days=int(prazo_dias))


def _grupo_peca(peca: Peca | None, peca_codigo: str = "") -> str:
    codigo = ""
    if peca is not None:
        codigo = (peca.codigo_interno or "").strip()
    if not codigo:
        codigo = (peca_codigo or "").strip()
    if not codigo:
        return ""
    pg = PecaGlobus.objects.filter(codigo_interno__iexact=codigo).only("codigo_grupo").first()
    return (pg.codigo_grupo or "").strip() if pg else ""


def resolver_prazo_dias(
    *,
    peca: Peca | None = None,
    peca_codigo: str = "",
    fornecedor: Fornecedor | None = None,
    fornecedor_chave: str = "",
    tipo_servico: str = RegraPrazoGarantia.TipoServico.EXTERNO,
) -> int:
    """
    Especificidade: peca > grupo_peca > fornecedor > tipo_servico > 180.
    """
    tipo = (tipo_servico or RegraPrazoGarantia.TipoServico.EXTERNO).strip().lower()
    peca_cod = (peca.codigo_interno if peca else peca_codigo or "").strip()
    grupo = _grupo_peca(peca, peca_cod)
    forn_val = ""
    if fornecedor is not None:
        forn_val = (fornecedor.cnpj or str(fornecedor.id) or "").strip()
        # tambem tenta nome fantasia / razao como valor_escopo
        nomes = [
            forn_val,
            (fornecedor.nome_fantasia or "").strip(),
            (fornecedor.razao_social or "").strip(),
            str(fornecedor.id),
        ]
    else:
        nomes = [(fornecedor_chave or "").strip()]

    regras = list(
        RegraPrazoGarantia.objects.filter(ativo=True).only(
            "escopo", "valor_escopo", "prazo_dias", "tipo_servico"
        )
    )

    def match(escopo: str, valor: str) -> int | None:
        if not valor:
            return None
        valor_u = valor.strip().upper()
        for r in regras:
            if r.escopo != escopo:
                continue
            if (r.valor_escopo or "").strip().upper() != valor_u:
                continue
            # tipo_servico no escopo tipo_servico; demais escopos podem filtrar por tipo se marcado
            if escopo == RegraPrazoGarantia.Escopo.TIPO_SERVICO:
                return int(r.prazo_dias)
            if (r.tipo_servico or "").strip().lower() in {"", tipo}:
                return int(r.prazo_dias)
        return None

    hit = match(RegraPrazoGarantia.Escopo.PECA, peca_cod)
    if hit is not None:
        return hit

    hit = match(RegraPrazoGarantia.Escopo.GRUPO_PECA, grupo)
    if hit is not None:
        return hit

    for nome in nomes:
        hit = match(RegraPrazoGarantia.Escopo.FORNECEDOR, nome)
        if hit is not None:
            return hit

    hit = match(RegraPrazoGarantia.Escopo.TIPO_SERVICO, tipo)
    if hit is not None:
        return hit

    return FALLBACK_PRAZO_DIAS


def ensure_regra_padrao_externo() -> RegraPrazoGarantia:
    regra, _ = RegraPrazoGarantia.objects.get_or_create(
        escopo=RegraPrazoGarantia.Escopo.TIPO_SERVICO,
        valor_escopo=RegraPrazoGarantia.TipoServico.EXTERNO,
        defaults={
            "prazo_dias": FALLBACK_PRAZO_DIAS,
            "tipo_servico": RegraPrazoGarantia.TipoServico.EXTERNO,
            "ativo": True,
        },
    )
    return regra
