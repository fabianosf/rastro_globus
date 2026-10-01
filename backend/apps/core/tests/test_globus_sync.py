from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.globus_oracle import GlobusOracleError, assert_readonly_sql
from apps.core.globus_sync import compra_chave_unica, sync_compras, sync_pecas
from apps.core.models import (
    CompraGlobus,
    Fornecedor,
    Garantia,
    Peca,
    PecaGlobus,
    SyncLog,
    Usuario,
    Veiculo,
)


class AssertReadonlyTests(TestCase):
    def test_blocks_insert(self):
        with self.assertRaises(GlobusOracleError):
            assert_readonly_sql("INSERT INTO X VALUES (1)")
        with self.assertRaises(GlobusOracleError):
            assert_readonly_sql("UPDATE GLOBUS.EST_MOVTO SET X=1")
        assert_readonly_sql("SELECT 1 FROM DUAL")
        assert_readonly_sql("WITH cte AS (SELECT 1 AS a FROM DUAL) SELECT * FROM cte")


class SyncGlobusMockTests(TestCase):
    def test_sync_pecas_upsert_idempotent(self):
        batch1 = [
            {
                "codigo_interno": "01111011",
                "descricao": "Filtro A",
                "codigo_mat_int": "100",
                "codigo_grupo": "01",
            }
        ]
        batch2 = [
            {
                "codigo_interno": "01111011",
                "descricao": "Filtro A v2",
                "codigo_mat_int": "100",
                "codigo_grupo": "01",
            }
        ]

        client = MagicMock()
        client.configured = True
        client.iter_batches.side_effect = [[batch1], [batch2]]

        with patch("apps.core.globus_sync._oracle_client", return_value=client):
            log1 = sync_pecas(full=True)
            self.assertEqual(log1.status, SyncLog.Status.OK)
            self.assertEqual(PecaGlobus.objects.count(), 1)
            self.assertEqual(PecaGlobus.objects.get().descricao, "Filtro A")

            log2 = sync_pecas(full=True)
            self.assertEqual(log2.status, SyncLog.Status.OK)
            self.assertEqual(PecaGlobus.objects.count(), 1)
            self.assertEqual(PecaGlobus.objects.get().descricao, "Filtro A v2")

    def test_sync_compras_chave_unica(self):
        dm = date(2025, 6, 1)
        chave = compra_chave_unica(1, 99, 55, dm, 12345)
        batch = [
            {
                "cod_empresa": 1,
                "empresa": "Viacao Redentor Ltda",
                "codintnf": 99,
                "codigomatint": 55,
                "seqmovto": 12345,
                "numero_nf": "1000",
                "serie_nf": "1",
                "data_emissao": dm,
                "data_movto": dm,
                "peca_codigo": "01111011",
                "peca_descricao": "Filtro",
                "fornecedor_codigo": "10",
                "fornecedor_nome": "FORN",
                "quantidade": Decimal("2"),
                "valor_unitario": Decimal("15.5"),
            }
        ]
        client = MagicMock()
        client.configured = True
        client.iter_batches.return_value = [batch]

        with patch("apps.core.globus_sync._oracle_client", return_value=client):
            log = sync_compras(full=True)
        self.assertEqual(log.status, SyncLog.Status.OK)
        self.assertEqual(CompraGlobus.objects.count(), 1)
        row = CompraGlobus.objects.get()
        self.assertEqual(row.chave_unica, chave)
        self.assertEqual(row.valor_unitario, Decimal("15.5"))

        with patch("apps.core.globus_sync._oracle_client", return_value=client):
            log2 = sync_compras(full=True)
        self.assertEqual(log2.status, SyncLog.Status.OK)
        self.assertEqual(CompraGlobus.objects.count(), 1)

    def test_sync_error_logs_without_wiping(self):
        PecaGlobus.objects.create(codigo_interno="KEEP", descricao="x")
        client = MagicMock()
        client.configured = True
        client.iter_batches.side_effect = RuntimeError("oracle down")

        with patch("apps.core.globus_sync._oracle_client", return_value=client):
            with self.assertRaises(RuntimeError):
                sync_pecas(full=True)

        self.assertEqual(PecaGlobus.objects.count(), 1)
        log = SyncLog.objects.filter(tipo=SyncLog.Tipo.PECAS).latest("inicio")
        self.assertEqual(log.status, SyncLog.Status.ERRO)
        self.assertIn("oracle down", log.erro)


class ImprocedentesLocalTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(
            username="oficina_test", password="x", perfil=Usuario.Perfil.OFICINA
        )
        self.forn = Fornecedor.objects.create(
            razao_social="Forn Test", cnpj="12.345.678/0001-99"
        )
        self.veic = Veiculo.objects.create(codigo="1001", casa="REDENTOR")
        self.peca = Peca.objects.create(codigo_interno="01111011", descricao="Filtro")
        Garantia.objects.create(
            protocolo="GAR-2026-999001",
            peca=self.peca,
            veiculo=self.veic,
            fornecedor=self.forn,
            status=Garantia.Status.IMPROCEDENTE,
            valor_peca=Decimal("100.00"),
            criado_por=self.user,
            motivo_improcedente="teste",
        )
        CompraGlobus.objects.create(
            chave_unica="abc123",
            empresa="Viacao Redentor Ltda",
            numero_nf="555",
            serie_nf="1",
            data_emissao=date(2025, 1, 10),
            data_movto=date(2025, 1, 12),
            peca_codigo="01111011",
            peca_descricao="Filtro",
            fornecedor_nome="FORN",
            valor_unitario=Decimal("50"),
            quantidade=Decimal("1"),
        )
        SyncLog.objects.create(
            tipo=SyncLog.Tipo.COMPRAS,
            inicio=timezone.now() - timedelta(hours=1),
            fim=timezone.now() - timedelta(hours=1),
            status=SyncLog.Status.OK,
            linhas_lidas=1,
            linhas_gravadas=1,
        )

    def test_improcedentes_uses_local_compras(self):
        client = APIClient()
        client.force_authenticate(user=self.user)
        with patch("apps.core.globus_oracle.GlobusOracleClient.ping") as ping:
            ping.side_effect = AssertionError("Oracle nao deve ser chamado")
            resp = client.get("/api/relatorios/improcedentes-compras/?ano=2026")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["ultima_compra_globus"]["numero_nf"], "555")
        ping.assert_not_called()
