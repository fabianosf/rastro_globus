from datetime import date
from decimal import Decimal
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from openpyxl import Workbook

from apps.core.models import Fornecedor, HistoricoGarantiaMensal
from apps.core.planilha_import import (
    hash_linha,
    import_planilha,
    normalize_fornecedor_nome,
)


def _write_sample_xlsx(path: Path, rows: list[list]) -> None:
    wb = Workbook()
    # remove default and create BASE GERAL
    default = wb.active
    wb.remove(default)
    ws = wb.create_sheet("BASE GERAL")
    ws.append(
        [
            "Fornecedor",
            "Solicitado",
            "Concedido",
            "Em análise",
            "Negado",
            "Empresa",
            "Data",
            "Ano",
            "Mês",
        ]
    )
    for row in rows:
        ws.append(row)
    wb.save(path)


class NormalizeFornecedorTests(TestCase):
    def test_strip_upper_accents_aliases(self):
        self.assertEqual(normalize_fornecedor_nome("  mundo  diesel "), "MUNDO DIESEL")
        self.assertEqual(normalize_fornecedor_nome("José"), "JOSE")
        self.assertEqual(normalize_fornecedor_nome("BB TECH"), "BBTECH")
        self.assertEqual(normalize_fornecedor_nome("bb tech"), "BBTECH")


class ImportPlanilhaTests(TestCase):
    def setUp(self):
        self.tmp = Path(self._test_tmpdir())
        self.tmp.mkdir(parents=True, exist_ok=True)

    def _test_tmpdir(self) -> str:
        import tempfile

        return tempfile.mkdtemp(prefix="rg_planilha_")

    def test_dry_run_does_not_persist(self):
        path = self.tmp / "sample.xlsx"
        _write_sample_xlsx(
            path,
            [
                ["MUNDO DIESEL", 300, 100, 50, 150, "REDENTOR", date(2025, 3, 15), 2025, 3],
            ],
        )
        result = import_planilha(path, dry_run=True)
        self.assertEqual(result.inseridas, 1)
        self.assertEqual(HistoricoGarantiaMensal.objects.count(), 0)
        self.assertEqual(Fornecedor.objects.filter(origem="planilha").count(), 0)

    def test_import_idempotent(self):
        path = self.tmp / "sample.xlsx"
        _write_sample_xlsx(
            path,
            [
                ["BB TECH", 200, 80, 20, 100, "FUTURO", date(2025, 1, 1), 2025, 1],
                ["Empresa Ruim", 10, 10, 0, 0, "INVALIDA", date(2025, 1, 1), 2025, 1],
            ],
        )
        r1 = import_planilha(path, dry_run=False)
        self.assertEqual(r1.inseridas, 1)
        self.assertEqual(r1.rejeitadas, 1)
        self.assertEqual(HistoricoGarantiaMensal.objects.count(), 1)

        row = HistoricoGarantiaMensal.objects.get()
        self.assertEqual(row.empresa, "FUTURO")
        self.assertEqual(row.valor_solicitado, Decimal("200.00"))
        self.assertEqual(row.valor_concedido + row.valor_em_analise + row.valor_negado, row.valor_solicitado)
        self.assertEqual(row.fornecedor.origem, "planilha")
        self.assertEqual(normalize_fornecedor_nome(row.fornecedor.razao_social), "BBTECH")

        r2 = import_planilha(path, dry_run=False)
        self.assertEqual(r2.inseridas, 0)
        self.assertEqual(r2.ignoradas, 1)
        self.assertEqual(HistoricoGarantiaMensal.objects.count(), 1)

        expected = hash_linha(
            "BBTECH",
            "FUTURO",
            date(2025, 1, 1),
            Decimal("80"),
            Decimal("20"),
            Decimal("100"),
        )
        self.assertEqual(row.hash_linha, expected)

    def test_rejects_csv(self):
        path = self.tmp / "sample.csv"
        path.write_text("a,b\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            import_planilha(path)

        out = StringIO()
        with self.assertRaises(CommandError):
            call_command("import_planilha", str(path), stdout=out)
