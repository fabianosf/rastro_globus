from django.db import models
from django.contrib.auth.models import AbstractUser


class Usuario(AbstractUser):
    class Perfil(models.TextChoices):
        OFICINA = "oficina", "Oficina / Depósito"
        COMPRAS = "compras", "Compras"
        MANUTENCAO = "manutencao", "Manutenção"
        DIRECAO = "direcao", "Direção"
        ADMIN = "admin", "Administrador"

    perfil = models.CharField(max_length=20, choices=Perfil.choices, default=Perfil.OFICINA)
    telefone = models.CharField(max_length=20, blank=True)


class Fornecedor(models.Model):
    razao_social = models.CharField(max_length=200)
    nome_fantasia = models.CharField(max_length=200, blank=True)
    cnpj = models.CharField(max_length=18, unique=True)
    contato = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    telefone = models.CharField(max_length=20, blank=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome_fantasia or self.razao_social


class Veiculo(models.Model):
    codigo = models.CharField(max_length=30, unique=True)
    placa = models.CharField(max_length=10, blank=True)
    descricao = models.CharField(max_length=200, blank=True)
    casa = models.CharField(max_length=80, blank=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.codigo


class Peca(models.Model):
    codigo_interno = models.CharField(max_length=40, unique=True)
    descricao = models.CharField(max_length=255)
    garantia_dias = models.PositiveIntegerField(default=365)
    garantia_km = models.PositiveIntegerField(null=True, blank=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.codigo_interno} - {self.descricao}"


class NotaFiscal(models.Model):
    class Tipo(models.TextChoices):
        COMPRA = "compra", "Compra / entrada original"
        REMESSA = "remessa", "Saída para garantia"
        RETORNO = "retorno", "Retorno do fornecedor"
        ENTRADA_PROCEDENTE = "entrada_procedente", "Espelho Globo (procedente)"

    numero = models.CharField(max_length=30)
    serie = models.CharField(max_length=10, blank=True)
    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.PROTECT, null=True, blank=True)
    data_emissao = models.DateField()
    valor = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    chave_nfe = models.CharField(max_length=44, blank=True)
    arquivo_pdf = models.FileField(upload_to="notas/", blank=True, null=True)
    observacao = models.TextField(blank=True)

    class Meta:
        unique_together = ("numero", "serie", "tipo")

    def __str__(self):
        return f"NF {self.numero} ({self.tipo})"


class Garantia(models.Model):
    class Status(models.TextChoices):
        ABERTA = "aberta", "Aberta / laudo gerado"
        ENVIADA = "enviada", "Enviada ao fornecedor"
        EM_ANALISE = "em_analise", "Em análise"
        PROCEDENTE = "procedente", "Procedente"
        IMPROCEDENTE = "improcedente", "Improcedente"
        CORTESIA = "cortesia", "Cortesia comercial"
        CANCELADA = "cancelada", "Cancelada"

    protocolo = models.CharField(max_length=20, unique=True)
    peca = models.ForeignKey(Peca, on_delete=models.PROTECT)
    veiculo = models.ForeignKey(Veiculo, on_delete=models.PROTECT)
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ABERTA)

    data_compra = models.DateField(null=True, blank=True)
    nota_compra = models.ForeignKey(
        NotaFiscal, on_delete=models.SET_NULL, null=True, blank=True, related_name="garantias_compra"
    )
    km_aplicacao = models.PositiveIntegerField(null=True, blank=True)
    data_primeira_baixa = models.DateField(null=True, blank=True)
    data_segunda_baixa = models.DateField(null=True, blank=True)
    requisicao_anterior = models.CharField(max_length=40, blank=True)
    requisicao_atual = models.CharField(max_length=40, blank=True)

    nota_remessa = models.ForeignKey(
        NotaFiscal, on_delete=models.SET_NULL, null=True, blank=True, related_name="garantias_remessa"
    )
    data_envio = models.DateField(null=True, blank=True)
    nota_retorno = models.ForeignKey(
        NotaFiscal, on_delete=models.SET_NULL, null=True, blank=True, related_name="garantias_retorno"
    )
    data_retorno = models.DateField(null=True, blank=True)

    valor_peca = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    laudo_pdf = models.FileField(upload_to="laudos/", blank=True, null=True)
    laudo_resumo = models.TextField(blank=True)
    motivo_improcedente = models.TextField(blank=True)
    nf_entrada_globo = models.CharField(max_length=30, blank=True)

    criado_por = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name="garantias_criadas")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    observacoes = models.TextField(blank=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return self.protocolo


class EventoGarantia(models.Model):
    garantia = models.ForeignKey(Garantia, on_delete=models.CASCADE, related_name="eventos")
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    data = models.DateTimeField(auto_now_add=True)
    status_anterior = models.CharField(max_length=20, blank=True)
    status_novo = models.CharField(max_length=20)
    descricao = models.TextField()
    arquivo = models.FileField(upload_to="eventos/", blank=True, null=True)

    class Meta:
        ordering = ["data"]


class Anexo(models.Model):
    garantia = models.ForeignKey(Garantia, on_delete=models.CASCADE, related_name="anexos")
    arquivo = models.FileField(upload_to="anexos/")
    descricao = models.CharField(max_length=200, blank=True)
    enviado_por = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    enviado_em = models.DateTimeField(auto_now_add=True)
