from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from apps.core.models import EventoGarantia, Fornecedor, Garantia, NotaFiscal, Peca, Usuario, Veiculo
from apps.core.services import fechar_improcedente_direto


class FecharImprocedenteDiretoTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(
            username="manut_dir", password="x", perfil=Usuario.Perfil.MANUTENCAO
        )
        self.compras = Usuario.objects.create_user(
            username="compras_dir", password="x", perfil=Usuario.Perfil.COMPRAS
        )
        self.forn = Fornecedor.objects.create(razao_social="F Dir", cnpj="77.777.777/0001-77")
        self.veic = Veiculo.objects.create(codigo="VD1")
        self.peca = Peca.objects.create(codigo_interno="PD1", descricao="Peca D")
        self.nf_remessa = NotaFiscal.objects.create(
            numero="REM-100",
            serie="1",
            tipo=NotaFiscal.Tipo.REMESSA,
            data_emissao=date(2026, 2, 1),
            fornecedor=self.forn,
        )
        self.g = Garantia.objects.create(
            protocolo="GAR-2026-DIR001",
            peca=self.peca,
            veiculo=self.veic,
            fornecedor=self.forn,
            status=Garantia.Status.ABERTA,
            nota_remessa=self.nf_remessa,
            laudo_resumo="",
            criado_por=self.user,
            nf_venda_fornecedor="9",
            nf_venda_data=date(2026, 1, 1),
            data_aplicacao=date(2026, 1, 2),
            prazo_garantia_dias=180,
            data_fim_garantia=date(2026, 7, 1),
        )

    def test_aberta_gera_timeline_completa(self):
        fechar_improcedente_direto(
            self.g,
            self.user,
            laudo_resumo="Laudo tecnico ok",
            causa_improcedente=Garantia.CausaImprocedente.ERRO_APLICACAO,
            responsavel_tipo=Garantia.ResponsavelTipo.OFICINA,
            responsavel_nome="Joao",
            motivo_improcedente="aplicacao errada",
            cobranca_interna=True,
            nf_retorno={"numero": "RET-55", "serie": "", "data_emissao": "2026-03-01"},
        )
        self.g.refresh_from_db()
        self.assertEqual(self.g.status, Garantia.Status.IMPROCEDENTE)
        self.assertEqual(self.g.causa_improcedente, "erro_aplicacao")
        self.assertEqual(self.g.nf_entrada_globo, "")
        self.assertTrue(self.g.nota_retorno_id)
        eventos = list(
            EventoGarantia.objects.filter(garantia=self.g).order_by("id").values_list(
                "status_novo", flat=True
            )
        )
        self.assertEqual(
            eventos,
            [
                Garantia.Status.ENVIADA,
                Garantia.Status.EM_ANALISE,
                Garantia.Status.IMPROCEDENTE,
            ],
        )

    def test_exige_remessa(self):
        self.g.nota_remessa = None
        self.g.save(update_fields=["nota_remessa"])
        with self.assertRaises(ValidationError):
            fechar_improcedente_direto(
                self.g,
                self.user,
                laudo_resumo="x",
                causa_improcedente=Garantia.CausaImprocedente.ERRO_APLICACAO,
                responsavel_tipo=Garantia.ResponsavelTipo.OFICINA,
                responsavel_nome="Joao",
            )

    def test_compras_nao_pode(self):
        with self.assertRaises(ValidationError):
            fechar_improcedente_direto(
                self.g,
                self.compras,
                laudo_resumo="x",
                causa_improcedente=Garantia.CausaImprocedente.ERRO_APLICACAO,
                responsavel_tipo=Garantia.ResponsavelTipo.OFICINA,
                responsavel_nome="Joao",
            )

    def test_api_endpoint(self):
        client = APIClient()
        client.force_authenticate(user=self.user)
        resp = client.post(
            f"/api/garantias/{self.g.id}/fechar-improcedente-direto/",
            {
                "laudo_resumo": "Laudo via API",
                "causa_improcedente": "erro_operacao",
                "responsavel_tipo": "motorista",
                "responsavel_nome": "Carlos",
                "motivo_improcedente": "uso indevido",
                "cobranca_interna": True,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.g.refresh_from_db()
        self.assertEqual(self.g.status, Garantia.Status.IMPROCEDENTE)
        self.assertEqual(EventoGarantia.objects.filter(garantia=self.g).count(), 3)
