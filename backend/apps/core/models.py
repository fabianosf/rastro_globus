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
    origem = models.CharField(max_length=20, blank=True, default="")

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


class HistoricoGarantiaMensal(models.Model):
    class Empresa(models.TextChoices):
        REDENTOR = "REDENTOR", "REDENTOR"
        FUTURO = "FUTURO", "FUTURO"
        BARRA_G1 = "BARRA G1", "BARRA G1"
        BARRA_G2 = "BARRA G2", "BARRA G2"

    fornecedor = models.ForeignKey(
        Fornecedor, on_delete=models.PROTECT, related_name="historico_mensal"
    )
    empresa = models.CharField(max_length=20, choices=Empresa.choices)
    competencia = models.DateField(help_text="Primeiro dia do mes")
    valor_concedido = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    valor_em_analise = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    valor_negado = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    valor_solicitado = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    origem = models.CharField(max_length=20, default="planilha")
    importado_em = models.DateTimeField(auto_now_add=True)
    hash_linha = models.CharField(max_length=64, unique=True)

    class Meta:
        ordering = ["-competencia", "empresa", "fornecedor_id"]
        indexes = [
            models.Index(fields=["competencia"]),
            models.Index(fields=["empresa", "competencia"]),
        ]

    def __str__(self):
        return f"{self.empresa} {self.competencia} {self.fornecedor_id}"


class PecaGlobus(models.Model):
    codigo_interno = models.CharField(max_length=40, unique=True)
    descricao = models.CharField(max_length=255, blank=True)
    codigo_mat_int = models.CharField(max_length=40, blank=True)
    codigo_grupo = models.CharField(max_length=20, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Peca Globus (espelho)"
        verbose_name_plural = "Pecas Globus (espelho)"

    def __str__(self):
        return self.codigo_interno


class VeiculoGlobus(models.Model):
    prefixo = models.CharField(max_length=30, blank=True)
    placa = models.CharField(max_length=20, blank=True)
    codigo_veic_globus = models.CharField(max_length=40, unique=True)
    codigo_empresa = models.CharField(max_length=20, blank=True)
    condicao = models.CharField(max_length=10, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Veiculo Globus (espelho)"
        verbose_name_plural = "Veiculos Globus (espelho)"
        indexes = [models.Index(fields=["prefixo"]), models.Index(fields=["placa"])]

    def __str__(self):
        return self.prefixo or self.codigo_veic_globus


class FornecedorGlobus(models.Model):
    codigo_forn = models.CharField(max_length=40, unique=True)
    nome_fantasia = models.CharField(max_length=200, blank=True)
    nr_forn = models.CharField(max_length=40, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Fornecedor Globus (espelho)"
        verbose_name_plural = "Fornecedores Globus (espelho)"

    def __str__(self):
        return self.nome_fantasia or self.codigo_forn


class CompraGlobus(models.Model):
    empresa = models.CharField(max_length=80, blank=True)
    numero_nf = models.CharField(max_length=30, blank=True)
    serie_nf = models.CharField(max_length=10, blank=True)
    data_emissao = models.DateField(null=True, blank=True)
    data_movto = models.DateField(null=True, blank=True, db_index=True)
    peca_codigo = models.CharField(max_length=40, db_index=True)
    peca_descricao = models.CharField(max_length=255, blank=True)
    fornecedor_codigo = models.CharField(max_length=40, blank=True)
    fornecedor_nome = models.CharField(max_length=200, blank=True)
    quantidade = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    valor_unitario = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    chave_unica = models.CharField(max_length=64, unique=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Compra Globus (espelho)"
        verbose_name_plural = "Compras Globus (espelho)"
        ordering = ["-data_movto"]

    def __str__(self):
        return f"{self.peca_codigo} NF {self.numero_nf}"


class SyncLog(models.Model):
    class Tipo(models.TextChoices):
        PECAS = "pecas", "Pecas"
        VEICULOS = "veiculos", "Veiculos"
        FORNECEDORES = "fornecedores", "Fornecedores"
        COMPRAS = "compras", "Compras"

    class Status(models.TextChoices):
        OK = "ok", "OK"
        ERRO = "erro", "Erro"

    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    inicio = models.DateTimeField()
    fim = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices)
    linhas_lidas = models.PositiveIntegerField(default=0)
    linhas_gravadas = models.PositiveIntegerField(default=0)
    erro = models.TextField(blank=True)

    class Meta:
        ordering = ["-inicio"]
        indexes = [models.Index(fields=["tipo", "-inicio"])]

    def __str__(self):
        return f"{self.tipo} {self.status} {self.inicio}"
