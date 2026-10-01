from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.core.models import (
    AlertaReincidencia,
    Fornecedor,
    Garantia,
    Peca,
    PecaGlobus,
    RegraPrazoGarantia,
    SaidaGlobus,
    Usuario,
    Veiculo,
)
from apps.core.prazo_garantia import (
    calcular_data_fim_garantia,
    ensure_regra_padrao_externo,
    resolver_prazo_dias,
)
from apps.core.reincidencia import detectar_reincidencia
from apps.core.services import mudar_status


class PrazoGarantiaTests(TestCase):
    def setUp(self):
        ensure_regra_padrao_externo()
        self.peca = Peca.objects.create(codigo_interno="PX1", descricao="Peca X")
        PecaGlobus.objects.create(codigo_interno="PX1", descricao="Peca X", codigo_grupo="G9")
        self.forn = Fornecedor.objects.create(
            razao_social="Forn Z", cnpj="99.999.999/0001-99", nome_fantasia="Forn Z"
        )

    def test_data_fim_garantia(self):
        fim = calcular_data_fim_garantia(date(2026, 1, 1), 180)
        self.assertEqual(fim, date(2026, 1, 1) + timedelta(days=180))

    def test_especificidade_peca_vence(self):
        RegraPrazoGarantia.objects.create(
            escopo=RegraPrazoGarantia.Escopo.TIPO_SERVICO,
            valor_escopo="externo",
            prazo_dias=180,
            tipo_servico="externo",
        )
        RegraPrazoGarantia.objects.create(
            escopo=RegraPrazoGarantia.Escopo.GRUPO_PECA,
            valor_escopo="G9",
            prazo_dias=90,
            tipo_servico="externo",
        )
        RegraPrazoGarantia.objects.create(
            escopo=RegraPrazoGarantia.Escopo.PECA,
            valor_escopo="PX1",
            prazo_dias=30,
            tipo_servico="externo",
        )
        self.assertEqual(
            resolver_prazo_dias(peca=self.peca, fornecedor=self.forn, tipo_servico="externo"),
            30,
        )

    def test_especificidade_grupo_antes_fornecedor(self):
        RegraPrazoGarantia.objects.filter(escopo=RegraPrazoGarantia.Escopo.PECA).delete()
        RegraPrazoGarantia.objects.create(
            escopo=RegraPrazoGarantia.Escopo.FORNECEDOR,
            valor_escopo="Forn Z",
            prazo_dias=60,
            tipo_servico="externo",
        )
        RegraPrazoGarantia.objects.create(
            escopo=RegraPrazoGarantia.Escopo.GRUPO_PECA,
            valor_escopo="G9",
            prazo_dias=45,
            tipo_servico="externo",
        )
        self.assertEqual(
            resolver_prazo_dias(peca=self.peca, fornecedor=self.forn, tipo_servico="externo"),
            45,
        )


class ReincidenciaTests(TestCase):
    def setUp(self):
        ensure_regra_padrao_externo()
        d1 = date(2026, 1, 10)
        d2 = date(2026, 2, 1)
        SaidaGlobus.objects.create(
            chave_unica="s1",
            veiculo_codigo="1001",
            peca_codigo="PX1",
            peca_descricao="Peca X",
            data_movto=d1,
            numero_nf="N1",
            fornecedor_nome="Forn",
            valor_unitario=Decimal("10"),
        )
        SaidaGlobus.objects.create(
            chave_unica="s2",
            veiculo_codigo="1001",
            peca_codigo="PX1",
            peca_descricao="Peca X",
            data_movto=d2,
            numero_nf="N2",
            fornecedor_nome="Forn",
            valor_unitario=Decimal("12"),
        )

    def test_detect_sem_duplicar(self):
        r1 = detectar_reincidencia()
        self.assertEqual(r1["criados"], 1)
        self.assertEqual(AlertaReincidencia.objects.count(), 1)
        r2 = detectar_reincidencia()
        self.assertEqual(r2["criados"], 0)
        self.assertEqual(AlertaReincidencia.objects.count(), 1)


class CausaImprocedenteTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(
            username="manut_d", password="x", perfil=Usuario.Perfil.MANUTENCAO
        )
        self.forn = Fornecedor.objects.create(razao_social="F", cnpj="88.888.888/0001-88")
        self.veic = Veiculo.objects.create(codigo="V1")
        self.peca = Peca.objects.create(codigo_interno="P1", descricao="P")
        self.g = Garantia.objects.create(
            protocolo="GAR-2026-888001",
            peca=self.peca,
            veiculo=self.veic,
            fornecedor=self.forn,
            status=Garantia.Status.EM_ANALISE,
            laudo_resumo="laudo ok",
            criado_por=self.user,
            nf_venda_fornecedor="1",
            nf_venda_data=date(2026, 1, 1),
            data_aplicacao=date(2026, 1, 2),
            prazo_garantia_dias=180,
            data_fim_garantia=date(2026, 7, 1),
        )

    def test_exige_causa(self):
        with self.assertRaises(ValidationError):
            mudar_status(
                self.g,
                Garantia.Status.IMPROCEDENTE,
                self.user,
                "fecha",
                motivo_improcedente="x",
            )

    def test_fecha_com_causa(self):
        mudar_status(
            self.g,
            Garantia.Status.IMPROCEDENTE,
            self.user,
            "fecha",
            causa_improcedente=Garantia.CausaImprocedente.ERRO_APLICACAO,
            responsavel_tipo=Garantia.ResponsavelTipo.OFICINA,
            responsavel_nome="Joao",
            motivo_improcedente="aplicacao errada",
        )
        self.g.refresh_from_db()
        self.assertEqual(self.g.status, Garantia.Status.IMPROCEDENTE)
        self.assertEqual(self.g.causa_improcedente, "erro_aplicacao")
