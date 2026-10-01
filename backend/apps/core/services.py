from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import EventoGarantia, Garantia
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
        tem_laudo = bool(garantia.laudo_resumo or garantia.laudo_pdf)
        if not tem_laudo or not motivo:
            raise ValidationError(
                "Improcedente exige laudo (resumo ou PDF) e motivo."
            )
        garantia.motivo_improcedente = motivo
        # Improcedente NUNCA grava lógica de estoque / nf_entrada_globo
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
