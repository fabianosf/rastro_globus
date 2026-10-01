from django.utils import timezone
from rest_framework import serializers

from .models import (
    Anexo,
    EventoGarantia,
    Fornecedor,
    Garantia,
    NotaFiscal,
    Peca,
    Usuario,
    Veiculo,
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


class GarantiaListSerializer(serializers.ModelSerializer):
    peca_nome = serializers.SerializerMethodField()
    peca_codigo = serializers.CharField(source="peca.codigo_interno", read_only=True)
    veiculo_codigo = serializers.CharField(source="veiculo.codigo", read_only=True)
    fornecedor_nome = serializers.SerializerMethodField()
    nf_remessa = serializers.SerializerMethodField()
    nf_retorno = serializers.SerializerMethodField()
    dias_aberta = serializers.SerializerMethodField()

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


class GarantiaDetailSerializer(serializers.ModelSerializer):
    peca_nome = serializers.SerializerMethodField()
    veiculo_codigo = serializers.CharField(source="veiculo.codigo", read_only=True)
    fornecedor_nome = serializers.SerializerMethodField()
    nf_remessa = serializers.SerializerMethodField()
    nf_retorno = serializers.SerializerMethodField()
    nf_compra = serializers.SerializerMethodField()
    dias_aberta = serializers.SerializerMethodField()
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
            "nf_entrada_globo",
            "criado_por",
            "criado_em",
            "atualizado_em",
            "observacoes",
            "dias_aberta",
            "eventos",
            "anexos",
        )
        read_only_fields = ("protocolo", "criado_por", "criado_em", "atualizado_em")

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


class GarantiaCreateSerializer(serializers.ModelSerializer):
    nf_compra_numero = serializers.CharField(required=False, allow_blank=True, write_only=True)
    nf_compra_data = serializers.DateField(required=False, allow_null=True, write_only=True)

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
        )

    def create(self, validated_data):
        nf_numero = validated_data.pop("nf_compra_numero", "").strip()
        nf_data = validated_data.pop("nf_compra_data", None)
        user = self.context["request"].user

        garantia = Garantia(
            protocolo=proximo_protocolo(),
            criado_por=user,
            status=Garantia.Status.ABERTA,
            **validated_data,
        )

        if nf_numero:
            data_emissao = nf_data or timezone.localdate()
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
