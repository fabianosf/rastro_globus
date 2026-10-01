from django.utils import timezone
from rest_framework import serializers

from .models import (
    AlertaReincidencia,
    Anexo,
    CompraGlobus,
    EventoGarantia,
    Fornecedor,
    Garantia,
    NotaFiscal,
    Peca,
    RegraPrazoGarantia,
    Usuario,
    Veiculo,
)
from .prazo_garantia import (
    calcular_data_fim_garantia,
    ensure_regra_padrao_externo,
    resolver_prazo_dias,
)
from .services import proximo_protocolo


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ("id", "username", "first_name", "last_name", "email", "perfil", "telefone")


class FornecedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fornecedor
        fields = "__all__"


class VeiculoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Veiculo
        fields = "__all__"


class PecaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Peca
        fields = "__all__"


class NotaFiscalSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotaFiscal
        fields = "__all__"


class RegraPrazoGarantiaSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegraPrazoGarantia
        fields = "__all__"


class AlertaReincidenciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertaReincidencia
        fields = "__all__"
        read_only_fields = (
            "veiculo_codigo",
            "peca_codigo",
            "peca_descricao",
            "empresa",
            "data_1",
            "data_2",
            "dias_entre",
            "fornecedor_1",
            "nf_1",
            "valor_estimado",
            "criado_em",
            "atualizado_em",
        )


class EventoGarantiaSerializer(serializers.ModelSerializer):
    usuario_nome = serializers.SerializerMethodField()

    class Meta:
        model = EventoGarantia
        fields = (
            "id",
            "data",
            "status_anterior",
            "status_novo",
            "descricao",
            "arquivo",
            "usuario",
            "usuario_nome",
        )

    def get_usuario_nome(self, obj):
        return obj.usuario.get_full_name() or obj.usuario.username


class AnexoSerializer(serializers.ModelSerializer):
    enviado_por_nome = serializers.SerializerMethodField()

    class Meta:
        model = Anexo
        fields = (
            "id",
            "arquivo",
            "descricao",
            "enviado_por",
            "enviado_por_nome",
            "enviado_em",
        )
        read_only_fields = ("enviado_por", "enviado_em")

    def get_enviado_por_nome(self, obj):
        return obj.enviado_por.get_full_name() or obj.enviado_por.username


def _dias_garantia_restantes(obj: Garantia) -> int | None:
    if not obj.data_fim_garantia:
        return None
    return (obj.data_fim_garantia - timezone.localdate()).days


class GarantiaListSerializer(serializers.ModelSerializer):
    peca_nome = serializers.SerializerMethodField()
    peca_codigo = serializers.CharField(source="peca.codigo_interno", read_only=True)
    veiculo_codigo = serializers.CharField(source="veiculo.codigo", read_only=True)
    fornecedor_nome = serializers.SerializerMethodField()
    nf_remessa = serializers.SerializerMethodField()
    nf_retorno = serializers.SerializerMethodField()
    dias_aberta = serializers.SerializerMethodField()
    dias_garantia_restantes = serializers.SerializerMethodField()

    class Meta:
        model = Garantia
        fields = (
            "id",
            "protocolo",
            "peca_nome",
            "peca_codigo",
            "veiculo_codigo",
            "fornecedor_nome",
            "nf_remessa",
            "nf_retorno",
            "status",
            "valor_peca",
            "criado_em",
            "dias_aberta",
            "data_fim_garantia",
            "dias_garantia_restantes",
            "causa_improcedente",
            "nf_venda_fornecedor",
        )

    def get_peca_nome(self, obj):
        return f"{obj.peca.codigo_interno} - {obj.peca.descricao}"

    def get_fornecedor_nome(self, obj):
        return str(obj.fornecedor)

    def get_nf_remessa(self, obj):
        return obj.nota_remessa.numero if obj.nota_remessa_id else ""

    def get_nf_retorno(self, obj):
        return obj.nota_retorno.numero if obj.nota_retorno_id else ""

    def get_dias_aberta(self, obj):
        if obj.status in {
            Garantia.Status.PROCEDENTE,
            Garantia.Status.IMPROCEDENTE,
            Garantia.Status.CORTESIA,
            Garantia.Status.CANCELADA,
        }:
            fim = obj.data_retorno or obj.atualizado_em.date()
        else:
            fim = timezone.localdate()
        inicio = obj.criado_em.date()
        return (fim - inicio).days

    def get_dias_garantia_restantes(self, obj):
        return _dias_garantia_restantes(obj)


class GarantiaDetailSerializer(serializers.ModelSerializer):
    peca_nome = serializers.SerializerMethodField()
    veiculo_codigo = serializers.CharField(source="veiculo.codigo", read_only=True)
    fornecedor_nome = serializers.SerializerMethodField()
    nf_remessa = serializers.SerializerMethodField()
    nf_retorno = serializers.SerializerMethodField()
    nf_compra = serializers.SerializerMethodField()
    dias_aberta = serializers.SerializerMethodField()
    dias_garantia_restantes = serializers.SerializerMethodField()
    eventos = EventoGarantiaSerializer(many=True, read_only=True)
    anexos = AnexoSerializer(many=True, read_only=True)
    peca_detalhe = PecaSerializer(source="peca", read_only=True)
    veiculo_detalhe = VeiculoSerializer(source="veiculo", read_only=True)
    fornecedor_detalhe = FornecedorSerializer(source="fornecedor", read_only=True)

    class Meta:
        model = Garantia
        fields = (
            "id",
            "protocolo",
            "peca",
            "veiculo",
            "fornecedor",
            "peca_nome",
            "veiculo_codigo",
            "fornecedor_nome",
            "peca_detalhe",
            "veiculo_detalhe",
            "fornecedor_detalhe",
            "status",
            "data_compra",
            "nota_compra",
            "nf_compra",
            "km_aplicacao",
            "data_primeira_baixa",
            "data_segunda_baixa",
            "requisicao_anterior",
            "requisicao_atual",
            "nota_remessa",
            "nf_remessa",
            "data_envio",
            "nota_retorno",
            "nf_retorno",
            "data_retorno",
            "valor_peca",
            "laudo_pdf",
            "laudo_resumo",
            "motivo_improcedente",
            "causa_improcedente",
            "responsavel_tipo",
            "responsavel_nome",
            "cobranca_interna",
            "observacao_cobranca",
            "nf_entrada_globo",
            "nf_venda_fornecedor",
            "nf_venda_data",
            "compra_globus",
            "data_aplicacao",
            "prazo_garantia_dias",
            "data_fim_garantia",
            "dias_garantia_restantes",
            "alerta_origem",
            "criado_por",
            "criado_em",
            "atualizado_em",
            "observacoes",
            "dias_aberta",
            "eventos",
            "anexos",
        )
        read_only_fields = (
            "protocolo",
            "criado_por",
            "criado_em",
            "atualizado_em",
            "data_fim_garantia",
            "prazo_garantia_dias",
            "compra_globus",
        )

    def get_peca_nome(self, obj):
        return f"{obj.peca.codigo_interno} - {obj.peca.descricao}"

    def get_fornecedor_nome(self, obj):
        return str(obj.fornecedor)

    def get_nf_remessa(self, obj):
        return obj.nota_remessa.numero if obj.nota_remessa_id else ""

    def get_nf_retorno(self, obj):
        return obj.nota_retorno.numero if obj.nota_retorno_id else ""

    def get_nf_compra(self, obj):
        return obj.nota_compra.numero if obj.nota_compra_id else ""

    def get_dias_aberta(self, obj):
        if obj.status in {
            Garantia.Status.PROCEDENTE,
            Garantia.Status.IMPROCEDENTE,
            Garantia.Status.CORTESIA,
            Garantia.Status.CANCELADA,
        }:
            fim = obj.data_retorno or obj.atualizado_em.date()
        else:
            fim = timezone.localdate()
        return (fim - obj.criado_em.date()).days

    def get_dias_garantia_restantes(self, obj):
        return _dias_garantia_restantes(obj)


class GarantiaCreateSerializer(serializers.ModelSerializer):
    nf_compra_numero = serializers.CharField(required=False, allow_blank=True, write_only=True)
    nf_compra_data = serializers.DateField(required=False, allow_null=True, write_only=True)
    nf_venda_fornecedor = serializers.CharField(required=True, allow_blank=False)
    nf_venda_data = serializers.DateField(required=True)
    data_aplicacao = serializers.DateField(required=True)
    tipo_servico = serializers.ChoiceField(
        choices=RegraPrazoGarantia.TipoServico.choices,
        required=False,
        default=RegraPrazoGarantia.TipoServico.EXTERNO,
        write_only=True,
    )
    alerta_origem = serializers.PrimaryKeyRelatedField(
        queryset=AlertaReincidencia.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Garantia
        fields = (
            "peca",
            "veiculo",
            "fornecedor",
            "data_compra",
            "km_aplicacao",
            "requisicao_anterior",
            "requisicao_atual",
            "valor_peca",
            "observacoes",
            "laudo_resumo",
            "nf_compra_numero",
            "nf_compra_data",
            "nf_venda_fornecedor",
            "nf_venda_data",
            "data_aplicacao",
            "tipo_servico",
            "alerta_origem",
        )

    def validate_nf_venda_fornecedor(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("NF de venda do fornecedor e obrigatoria.")
        return value

    def create(self, validated_data):
        ensure_regra_padrao_externo()
        nf_numero = validated_data.pop("nf_compra_numero", "").strip()
        nf_data = validated_data.pop("nf_compra_data", None)
        tipo_servico = validated_data.pop(
            "tipo_servico", RegraPrazoGarantia.TipoServico.EXTERNO
        )
        user = self.context["request"].user

        garantia = Garantia(
            protocolo=proximo_protocolo(),
            criado_por=user,
            status=Garantia.Status.ABERTA,
            **validated_data,
        )

        prazo = resolver_prazo_dias(
            peca=garantia.peca,
            fornecedor=garantia.fornecedor,
            tipo_servico=tipo_servico,
        )
        garantia.prazo_garantia_dias = prazo
        garantia.data_fim_garantia = calcular_data_fim_garantia(
            garantia.data_aplicacao, prazo
        )

        # Liga CompraGlobus quando houver match NF + peca
        compra = (
            CompraGlobus.objects.filter(
                peca_codigo__iexact=garantia.peca.codigo_interno,
                numero_nf__iexact=garantia.nf_venda_fornecedor,
            )
            .order_by("-data_movto")
            .first()
        )
        if compra:
            garantia.compra_globus = compra

        if nf_numero:
            data_emissao = nf_data or garantia.nf_venda_data or timezone.localdate()
            nota, _ = NotaFiscal.objects.get_or_create(
                numero=nf_numero,
                serie="",
                tipo=NotaFiscal.Tipo.COMPRA,
                defaults={
                    "data_emissao": data_emissao,
                    "fornecedor": garantia.fornecedor,
                    "valor": garantia.valor_peca,
                },
            )
            garantia.nota_compra = nota
            if not garantia.data_compra:
                garantia.data_compra = data_emissao
        elif garantia.nf_venda_data and not garantia.data_compra:
            garantia.data_compra = garantia.nf_venda_data

        garantia.save()

        EventoGarantia.objects.create(
            garantia=garantia,
            usuario=user,
            status_anterior="",
            status_novo=Garantia.Status.ABERTA,
            descricao="Garantia aberta / laudo gerado.",
        )
        return garantia


class StatusChangeSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Garantia.Status.choices)
    descricao = serializers.CharField(required=False, allow_blank=True, default="")
    motivo_improcedente = serializers.CharField(required=False, allow_blank=True, default="")
    causa_improcedente = serializers.ChoiceField(
        choices=Garantia.CausaImprocedente.choices, required=False, allow_blank=True
    )
    responsavel_tipo = serializers.ChoiceField(
        choices=Garantia.ResponsavelTipo.choices, required=False, allow_blank=True
    )
    responsavel_nome = serializers.CharField(required=False, allow_blank=True, default="")
    cobranca_interna = serializers.BooleanField(required=False, default=False)
    observacao_cobranca = serializers.CharField(required=False, allow_blank=True, default="")
    nf_entrada_globo = serializers.CharField(required=False, allow_blank=True, default="")


class VincularNotaSerializer(serializers.Serializer):
    tipo = serializers.ChoiceField(
        choices=[
            NotaFiscal.Tipo.COMPRA,
            NotaFiscal.Tipo.REMESSA,
            NotaFiscal.Tipo.RETORNO,
        ]
    )
    numero = serializers.CharField(max_length=30)
    serie = serializers.CharField(max_length=10, required=False, allow_blank=True, default="")
    data_emissao = serializers.DateField()
    valor = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
