from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.core.planilha_import import import_planilha


class Command(BaseCommand):
    help = (
        "Importa a aba BASE GERAL de um .xlsx para HistoricoGarantiaMensal "
        "(idempotente por hash_linha). Nao cria Garantia."
    )

    def add_arguments(self, parser):
        parser.add_argument("caminho", type=str, help="Caminho do arquivo .xlsx")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula a importacao sem gravar no banco",
        )

    def handle(self, *args, **options):
        caminho = Path(options["caminho"]).expanduser().resolve()
        dry_run = bool(options["dry_run"])

        try:
            result = import_planilha(caminho, dry_run=dry_run)
        except FileNotFoundError as exc:
            raise CommandError(str(exc)) from exc
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        prefix = "[DRY-RUN] " if dry_run else ""
        self.stdout.write(
            f"{prefix}inseridas={result.inseridas} "
            f"ignoradas={result.ignoradas} "
            f"rejeitadas={result.rejeitadas} "
            f"fornecedores_criados={result.fornecedores_criados}"
        )

        if result.similares:
            self.stdout.write(self.style.WARNING(
                f"Nomes similares (difflib > 0.85): {len(result.similares)}"
            ))
            for a, b, ratio in result.similares[:30]:
                self.stdout.write(f"  {a} ~ {b} ({ratio})")
            if len(result.similares) > 30:
                self.stdout.write(f"  ... e mais {len(result.similares) - 30}")

        if result.rejeitados_path:
            self.stdout.write(f"Rejeitados: {result.rejeitados_path}")
        if result.similares_path:
            self.stdout.write(f"Similares: {result.similares_path}")

        if not dry_run:
            self.stdout.write(self.style.SUCCESS("Importacao concluida."))
        else:
            self.stdout.write(self.style.SUCCESS("Dry-run concluido (nada gravado)."))
