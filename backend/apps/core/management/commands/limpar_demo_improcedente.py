"""Remove garantias de demo/teste que poluem o relatório Custo do erro interno."""

from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.core.models import Garantia


PROTOCOLOS_EXATOS = (
    "GAR-2026-0131",
    "GAR-TEST-IMP-001",
)


class Command(BaseCommand):
    help = (
        "Apaga garantias demo/teste (GAR-2026-0131, GAR-TEST-*, etc.) "
        "para limpar o KPI de improcedentes fictícios."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Só lista o que seria apagado.",
        )

    def handle(self, *args, **options):
        qs = Garantia.objects.filter(
            Q(protocolo__in=PROTOCOLOS_EXATOS) | Q(protocolo__startswith="GAR-TEST-")
        )
        rows = list(qs.values_list("id", "protocolo", "status", "valor_peca"))
        if not rows:
            self.stdout.write("Nenhuma garantia demo/teste encontrada.")
            return

        self.stdout.write(f"Encontradas {len(rows)} garantia(s):")
        for gid, proto, status, valor in rows:
            self.stdout.write(f"  id={gid} {proto} status={status} valor={valor}")

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("Dry-run: nada apagado."))
            return

        deleted, detail = qs.delete()
        self.stdout.write(
            self.style.SUCCESS(f"Removido: {deleted} objeto(s) ({detail}).")
        )
