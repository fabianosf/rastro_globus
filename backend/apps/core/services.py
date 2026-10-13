from datetime import date, datetime

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import EventoGarantia, Garantia, NotaFiscal
from .permissions import perfil_pode_status


TRANSICOES = {
    Garantia.Status.ABERTA: {Garantia.Status.ENVIADA, Garantia.Status.CANCELADA},
    Garantia.Status.ENVIADA: {Garantia.Status.EM_ANALISE, Garantia.Status.CANCELADA},
    Garantia.Status.EM_ANALISE: {
        Garantia.Status.PROCEDENTE,
        Garantia.Status.IMPROCEDENTE,
        Garantia.Status.CORTESIA,
    },
    Garantia.Status.PROCEDENTE: set(),
    Garantia.Status.IMPROCEDENTE: set(),
    Garantia.Status.CORTESIA: set(),
    Garantia.Status.CANCELADA: set(),
}


def proximo_protocolo() -> str:
    ano = timezone.now().year
    prefixo = f"GAR-{ano}-"
    max_seq = 0
    for protocolo in Garantia.objects.filter(protocolo__startswith=prefixo).values_list(
        "protocolo", flat=True
    ):
        try:
            max_seq = max(max_seq, int(str(protocolo).split("-")[-1]))
        except ValueError:
            continue
    return f"{prefixo}{max_seq + 1:06d}"


def pode_espelhar_globo(status: str) -> bool:
    return status == Garantia.Status.PROCEDENTE


def mudar_status(garantia, novo_status, usuario, descricao, **extras):
    """
    Valida transição, grava EventoGarantia e atualiza campos.
    NUNCA cria movimento de estoque.
    nf_entrada_globo só é salvo como texto se status for procedente.
    """
    status_anterior = garantia.status
    novo_status = str(novo_status)

    if status_anterior == novo_status:
        raise ValidationError("O status informado já é o atual.")

    perfil = getattr(usuario, "perfil", None)
    if not perfil_pode_status(perfil, novo_status):
        raise ValidationError(
            f"Perfil '{perfil}' não pode alterar status para '{novo_status}'."
        )

    permitidos = TRANSICOES.get(status_anterior, set())
    admin_pode_cancelar = (
        novo_status == Garantia.Status.CANCELADA
        and status_anterior
        in {
            Garantia.Status.PROCEDENTE,
            Garantia.Status.IMPROCEDENTE,
            Garantia.Status.CORTESIA,
        }
        and perfil == "admin"
    )

    if novo_status not in permitidos and not admin_pode_cancelar:
        raise ValidationError(
            f"Transição de '{status_anterior}' para '{novo_status}' não é permitida."
        )

    if novo_status in {Garantia.Status.ENVIADA, Garantia.Status.EM_ANALISE}:
        if not garantia.nota_remessa_id:
            raise ValidationError("Para este status é obrigatório vincular a NF de remessa.")

    if novo_status == Garantia.Status.PROCEDENTE:
        tem_retorno = bool(garantia.nota_retorno_id)
        tem_justificativa = bool(
            extras.get("descricao") or descricao or garantia.laudo_resumo or garantia.laudo_pdf
        )
        if not tem_retorno and not tem_justificativa:
            raise ValidationError(
                "Procedente exige NF de retorno ou justificativa/laudo."
            )

    if novo_status == Garantia.Status.IMPROCEDENTE:
        motivo = (extras.get("motivo_improcedente") or garantia.motivo_improcedente or "").strip()
        causa = (extras.get("causa_improcedente") or garantia.causa_improcedente or "").strip()
        resp_tipo = (extras.get("responsavel_tipo") or garantia.responsavel_tipo or "").strip()
        resp_nome = (extras.get("responsavel_nome") or garantia.responsavel_nome or "").strip()
        tem_laudo = bool(garantia.laudo_resumo or garantia.laudo_pdf)
        causas_ok = {c.value for c in Garantia.CausaImprocedente}
        tipos_ok = {t.value for t in Garantia.ResponsavelTipo}
        if not tem_laudo:
            raise ValidationError("Improcedente exige laudo (resumo ou PDF).")
        if not causa or causa not in causas_ok:
            raise ValidationError(
                "Improcedente exige causa_improcedente "
                "(erro_aplicacao, erro_operacao, falha_sistemica_veiculo, outro)."
            )
        if not resp_tipo or resp_tipo not in tipos_ok:
            raise ValidationError(
                "Improcedente exige responsavel_tipo "
                "(oficina, mecanico, motorista, sistema, outro)."
            )
        if resp_tipo != Garantia.ResponsavelTipo.SISTEMA and not resp_nome:
            raise ValidationError("Informe responsavel_nome (exceto quando tipo=sistema).")
        if not motivo:
            motivo = causa
        garantia.motivo_improcedente = motivo
        garantia.causa_improcedente = causa
        garantia.responsavel_tipo = resp_tipo
        garantia.responsavel_nome = resp_nome
        if "cobranca_interna" in extras:
            garantia.cobranca_interna = bool(extras.get("cobranca_interna"))
        if extras.get("observacao_cobranca") is not None:
            garantia.observacao_cobranca = str(extras.get("observacao_cobranca") or "")
        # Improcedente NUNCA grava logica de estoque / nf_entrada_globo
        garantia.nf_entrada_globo = ""

    if novo_status == Garantia.Status.CORTESIA:
        obs = extras.get("descricao") or descricao or garantia.observacoes
        if not obs:
            raise ValidationError("Cortesia exige observação comercial.")
        # Cortesia NUNCA grava lógica de estoque
        garantia.nf_entrada_globo = ""

    if novo_status == Garantia.Status.PROCEDENTE and pode_espelhar_globo(novo_status):
        nf_globo = extras.get("nf_entrada_globo")
        if nf_globo is not None:
            # Apenas texto espelho — sem movimento de estoque
            garantia.nf_entrada_globo = str(nf_globo).strip()
    elif novo_status != Garantia.Status.PROCEDENTE:
        # Limpa qualquer tentativa de gravar nf_entrada_globo fora de procedente
        if "nf_entrada_globo" in extras and extras.get("nf_entrada_globo"):
            raise ValidationError(
                "Campo nf_entrada_globo só faz sentido no status procedente."
            )

    with transaction.atomic():
        garantia.status = novo_status
        if novo_status == Garantia.Status.ENVIADA and not garantia.data_envio:
            garantia.data_envio = timezone.localdate()
        if novo_status in {
            Garantia.Status.PROCEDENTE,
            Garantia.Status.IMPROCEDENTE,
            Garantia.Status.CORTESIA,
        } and not garantia.data_retorno:
            garantia.data_retorno = timezone.localdate()
        garantia.save()

        EventoGarantia.objects.create(
            garantia=garantia,
            usuario=usuario,
            status_anterior=status_anterior,
            status_novo=novo_status,
            descricao=descricao or f"Status alterado para {novo_status}",
            arquivo=extras.get("arquivo"),
        )

    return garantia


def _parse_data_emissao(raw) -> date:
    if raw is None or raw == "":
        return timezone.localdate()
    if isinstance(raw, date) and not isinstance(raw, datetime):
        return raw
    if isinstance(raw, datetime):
        return raw.date()
    return date.fromisoformat(str(raw)[:10])


def fechar_improcedente_direto(
    garantia,
    usuario,
    *,
    laudo_resumo="",
    laudo_pdf=None,
    nf_retorno=None,
    descricao="",
    **extras,
):
    """
    Avança aberta→enviada→em_analise→improcedente (conforme status atual)
    em uma única transação, gerando EventoGarantia em cada etapa via mudar_status.
    Não altera TRANSICOES. Improcedente nunca preenche nf_entrada_globo.
    """
    status_ok = {
        Garantia.Status.ABERTA,
        Garantia.Status.ENVIADA,
        Garantia.Status.EM_ANALISE,
    }
    if garantia.status not in status_ok:
        raise ValidationError(
            "Encerramento direto só é permitido com status aberta, enviada ou em_analise."
        )

    perfil = getattr(usuario, "perfil", None)
    if not perfil_pode_status(perfil, Garantia.Status.IMPROCEDENTE):
        raise ValidationError(
            f"Perfil '{perfil}' não pode encerrar como improcedente."
        )

    if not garantia.nota_remessa_id:
        raise ValidationError("Vincule a NF de remessa antes de encerrar.")

    if garantia.status == Garantia.Status.ABERTA:
        sequencia = [
            Garantia.Status.ENVIADA,
            Garantia.Status.EM_ANALISE,
            Garantia.Status.IMPROCEDENTE,
        ]
    elif garantia.status == Garantia.Status.ENVIADA:
        sequencia = [Garantia.Status.EM_ANALISE, Garantia.Status.IMPROCEDENTE]
    else:
        sequencia = [Garantia.Status.IMPROCEDENTE]

    with transaction.atomic():
        dirty = []
        if laudo_resumo:
            garantia.laudo_resumo = str(laudo_resumo).strip()
            dirty.append("laudo_resumo")
        if laudo_pdf is not None:
            garantia.laudo_pdf = laudo_pdf
            dirty.append("laudo_pdf")
        if dirty:
            garantia.save(update_fields=[*dirty, "atualizado_em"])

        if isinstance(nf_retorno, dict) and str(nf_retorno.get("numero") or "").strip():
            data_em = _parse_data_emissao(nf_retorno.get("data_emissao"))
            nota, _ = NotaFiscal.objects.get_or_create(
                numero=str(nf_retorno["numero"]).strip(),
                serie=str(nf_retorno.get("serie") or "").strip(),
                tipo=NotaFiscal.Tipo.RETORNO,
                defaults={
                    "data_emissao": data_em,
                    "fornecedor": garantia.fornecedor,
                },
            )
            garantia.nota_retorno = nota
            if not garantia.data_retorno:
                garantia.data_retorno = data_em
            garantia.save(update_fields=["nota_retorno", "data_retorno", "atualizado_em"])

        for i, novo_status in enumerate(sequencia):
            is_last = i == len(sequencia) - 1
            etapa_desc = (
                f"Encerramento direto (fornecedor já respondeu): {novo_status}"
            )
            if is_last:
                last_extras = dict(extras)
                if laudo_pdf is not None:
                    # Anexa o PDF também ao EventoGarantia final (mudar_status → arquivo=)
                    last_extras["arquivo"] = garantia.laudo_pdf or laudo_pdf
                mudar_status(
                    garantia,
                    novo_status,
                    usuario,
                    descricao or etapa_desc,
                    **last_extras,
                )
            else:
                mudar_status(garantia, novo_status, usuario, etapa_desc)
            garantia.refresh_from_db()

    return garantia
