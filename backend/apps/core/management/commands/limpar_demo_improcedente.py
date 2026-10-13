"""Remove garantias de demo/teste que poluem o relatório Custo do erro interno."""

from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.core.models import Garantia


class Command(BaseCommand):
    help = (
        "Apaga garantias de teste (GAR-TEST-*) e a demo GAR-2026-0131 "
        "somente se ainda estiver improcedente — limpa o KPI falso."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Só lista o que seria apagado.",
        )

    def handle(self, *args, **options):
        # Não apaga GAR-2026-0131 em em_analise/enviada (seed válido).
        qs = Garantia.objects.filter(
            Q(protocolo__startswith="GAR-TEST-")
            | Q(
                protocolo="GAR-2026-0131",
                status=Garantia.Status.IMPROCEDENTE,
            )
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
