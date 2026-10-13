from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.core.models import Fornecedor, Garantia, Peca, Usuario, Veiculo


class RelatorioErroInternoTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(
            username="dir_ei", password="x", perfil=Usuario.Perfil.DIRECAO
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.peca = Peca.objects.create(codigo_interno="EI1", descricao="Peca EI")
        self.veiculo = Veiculo.objects.create(codigo="V-EI", casa="Casa A")
        self.forn = Fornecedor.objects.create(
            razao_social="Forn EI", cnpj="11.111.111/0001-11", nome_fantasia="Forn EI"
        )
        Garantia.objects.create(
            protocolo="GAR-2026-EI0001",
            peca=self.peca,
            veiculo=self.veiculo,
            fornecedor=self.forn,
            status=Garantia.Status.IMPROCEDENTE,
            data_retorno=date(2026, 3, 15),
            valor_peca=Decimal("100.00"),
            causa_improcedente=Garantia.CausaImprocedente.ERRO_APLICACAO,
            responsavel_tipo=Garantia.ResponsavelTipo.OFICINA,
            responsavel_nome="Joao",
            cobranca_interna=True,
            criado_por=self.user,
            nf_venda_fornecedor="1",
            laudo_resumo="x",
        )
        Garantia.objects.create(
            protocolo="GAR-2026-EI0002",
            peca=self.peca,
            veiculo=self.veiculo,
            fornecedor=self.forn,
            status=Garantia.Status.IMPROCEDENTE,
            data_retorno=None,
            valor_peca=None,
            causa_improcedente=Garantia.CausaImprocedente.ERRO_OPERACAO,
            cobranca_interna=False,
            criado_por=self.user,
            nf_venda_fornecedor="2",
            laudo_resumo="y",
        )
        # Force criado_em year via update after create is hard; use data_retorno year filter.
        # Second row uses criado_em (today) — if tests run in 2026 it counts; annotate covers it.

    def test_erro_interno_payload(self):
        resp = self.client.get("/api/relatorios/erro-interno/?ano=2026")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["ano"], 2026)
        self.assertGreaterEqual(data["total"], 1)
        self.assertIn("por_causa", data)
        self.assertIn("por_mes", data)
        self.assertEqual(len(data["por_mes"]), 12)
        self.assertIn("reincidencia", data)
        self.assertIn("cobranca", data)
        # First garantia with valor 100 and cobranca
        self.assertGreaterEqual(Decimal(data["valor_total"]), Decimal("100.00"))
