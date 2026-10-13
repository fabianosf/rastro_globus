from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.core.models import (
    AlertaReincidencia,
    CompraGlobus,
    Fornecedor,
    Garantia,
    Peca,
    PecaGlobus,
    SaidaGlobus,
    Usuario,
    Veiculo,
)


class HistoricoGlobusFichaTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(
            username="manut_hg", password="x", perfil=Usuario.Perfil.MANUTENCAO
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.forn = Fornecedor.objects.create(razao_social="F HG", cnpj="66.666.666/0001-66")
        self.veic = Veiculo.objects.create(codigo="47624", casa="Matriz")
        self.peca = Peca.objects.create(codigo_interno="01111011", descricao="Peca HG")
        self.g = Garantia.objects.create(
            protocolo="GAR-2026-HG0001",
            peca=self.peca,
            veiculo=self.veic,
            fornecedor=self.forn,
            status=Garantia.Status.ENVIADA,
            valor_peca=Decimal("100.00"),
            criado_por=self.user,
            nf_venda_fornecedor="1",
            laudo_resumo="x",
        )
        PecaGlobus.objects.create(
            codigo_interno="01111011", descricao="Peça Globus espelho", codigo_grupo="G1"
        )
        SaidaGlobus.objects.create(
            chave_unica="hg-s1",
            veiculo_codigo="47624",
            peca_codigo="01111011",
            peca_descricao="Peca HG",
            data_movto=date(2026, 8, 1),
            numero_nf="S1",
            fornecedor_nome="Forn A",
            quantidade=Decimal("1"),
        )
        SaidaGlobus.objects.create(
            chave_unica="hg-s2",
            veiculo_codigo="47624",
            peca_codigo="01111011",
            data_movto=date(2026, 9, 1),
            numero_nf="S2",
            fornecedor_nome="Forn A",
        )
        CompraGlobus.objects.create(
            chave_unica="hg-c1",
            peca_codigo="01111011",
            numero_nf="C100",
            data_movto=date(2026, 7, 1),
            fornecedor_nome="Forn Compra",
            valor_unitario=Decimal("50"),
        )
        AlertaReincidencia.objects.create(
            veiculo_codigo="47624",
            peca_codigo="01111011",
            peca_descricao="Peca HG",
            data_1=date(2026, 8, 1),
            data_2=date(2026, 9, 1),
            dias_entre=31,
            status=AlertaReincidencia.Status.NOVO,
            valor_estimado=Decimal("100"),
        )

    def test_historico_espelho(self):
        resp = self.client.get(f"/api/garantias/{self.g.id}/historico-globus/")
        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()
        self.assertTrue(data["readonly"])
        self.assertEqual(data["peca_codigo"], "01111011")
        self.assertEqual(data["veiculo_codigo"], "47624")
        self.assertIsNotNone(data["peca_espelho"])
        self.assertEqual(len(data["saidas"]), 2)
        self.assertEqual(len(data["compras"]), 1)
        self.assertEqual(len(data["alertas_reincidencia"]), 1)
        self.assertFalse(data["ao_vivo"]["solicitado"])

    def test_ao_vivo_sem_oracle_mantem_espelho(self):
        resp = self.client.get(f"/api/garantias/{self.g.id}/historico-globus/?ao_vivo=1")
        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()
        self.assertTrue(data["ao_vivo"]["solicitado"])
        # Espelho permanece mesmo se Oracle falhar
        self.assertEqual(len(data["saidas"]), 2)
        self.assertIn("aviso", data)
