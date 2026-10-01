from django.core.management.base import BaseCommand, CommandError

from apps.core.globus_sync import TIPOS_SYNC, run_sync
from apps.core.models import SyncLog


class Command(BaseCommand):
    help = (
        "Sincroniza espelho local a partir do Oracle Globus (somente SELECT). "
        "Nao grava no Globo nem movimenta estoque."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--full",
            action="store_true",
            help="Carga completa (compras dos ultimos 5 anos)",
        )
        parser.add_argument(
            "--tipo",
            type=str,
            default="",
            help=f"Tipo: {', '.join(TIPOS_SYNC)} (padrao: todos)",
        )

    def handle(self, *args, **options):
        full = bool(options["full"])
        tipo = (options.get("tipo") or "").strip() or None
        if tipo and tipo not in TIPOS_SYNC:
            raise CommandError(f"Tipo invalido: {tipo}. Use: {', '.join(TIPOS_SYNC)}")

        self.stdout.write(
            f"sync_globus full={full} tipo={tipo or 'todos'} "
            f"(Oracle somente leitura)"
        )
        try:
            logs = run_sync(full=full, tipo=tipo)
        except Exception as exc:
            raise CommandError(str(exc)) from exc

        for log in logs:
            style = self.style.SUCCESS if log.status == SyncLog.Status.OK else self.style.ERROR
            self.stdout.write(
                style(
                    f"{log.tipo}: status={log.status} lidas={log.linhas_lidas} "
                    f"gravadas={log.linhas_gravadas}"
                    + (f" erro={log.erro[:200]}" if log.erro else "")
                )
            )
