"""Deteccao de reincidencia a partir de SaidaGlobus."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from .models import AlertaReincidencia, RegraPrazoGarantia, SaidaGlobus
from .prazo_garantia import ensure_regra_padrao_externo, resolver_prazo_dias


def detectar_reincidencia(*, limite_pares: int | None = None) -> dict:
    """
    Para cada (veiculo, peca) com 2+ saidas ordenadas por data,
    se dias entre consecutivas <= prazo aplicavel, cria/atualiza alerta.
    Unique: veiculo+peca+data_2. Nao apaga descartados.
    """
    ensure_regra_padrao_externo()

    qs = (
        SaidaGlobus.objects.exclude(veiculo_codigo="")
        .exclude(peca_codigo="")
        .exclude(data_movto__isnull=True)
        .order_by("veiculo_codigo", "peca_codigo", "data_movto", "id")
        .only(
            "veiculo_codigo",
            "peca_codigo",
            "peca_descricao",
            "empresa",
            "data_movto",
            "numero_nf",
            "fornecedor_nome",
            "valor_unitario",
        )
    )

    grupos: dict[tuple[str, str], list[SaidaGlobus]] = defaultdict(list)
    for row in qs.iterator(chunk_size=2000):
        grupos[(row.veiculo_codigo, row.peca_codigo)].append(row)

    criados = 0
    atualizados = 0
    ignorados = 0
    pares = 0

    for (veiculo, peca), saidas in grupos.items():
        if len(saidas) < 2:
            continue
        prazo = resolver_prazo_dias(
            peca_codigo=peca,
            fornecedor_chave=saidas[0].fornecedor_nome or "",
            tipo_servico=RegraPrazoGarantia.TipoServico.EXTERNO,
        )
        for i in range(1, len(saidas)):
            s1 = saidas[i - 1]
            s2 = saidas[i]
            if not s1.data_movto or not s2.data_movto:
                continue
            if s2.data_movto < s1.data_movto:
                continue
            dias = (s2.data_movto - s1.data_movto).days
            if dias < 0 or dias > prazo:
                continue
            pares += 1
            if limite_pares is not None and pares > limite_pares:
                break

            valor = s1.valor_unitario
            defaults = {
                "peca_descricao": s1.peca_descricao or s2.peca_descricao or "",
                "empresa": s2.empresa or s1.empresa or "",
                "data_1": s1.data_movto,
                "dias_entre": dias,
                "fornecedor_1": s1.fornecedor_nome or "",
                "nf_1": s1.numero_nf or "",
                "valor_estimado": Decimal(valor) if valor is not None else None,
            }
            obj, created = AlertaReincidencia.objects.get_or_create(
                veiculo_codigo=veiculo,
                peca_codigo=peca,
                data_2=s2.data_movto,
                defaults={**defaults, "status": AlertaReincidencia.Status.NOVO},
            )
            if created:
                criados += 1
            elif obj.status == AlertaReincidencia.Status.DESCARTADO:
                ignorados += 1
            else:
                # atualiza metadados sem mudar status
                for k, v in defaults.items():
                    setattr(obj, k, v)
                obj.save(update_fields=[*defaults.keys(), "atualizado_em"])
                atualizados += 1
        if limite_pares is not None and pares > limite_pares:
            break

    return {
        "pares_avaliados": pares,
        "criados": criados,
        "atualizados": atualizados,
        "ignorados_descartados": ignorados,
        "grupos": len(grupos),
    }


def contagem_alertas_novos() -> int:
    return AlertaReincidencia.objects.filter(status=AlertaReincidencia.Status.NOVO).count()
