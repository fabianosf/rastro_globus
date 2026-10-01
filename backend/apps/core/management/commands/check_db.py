from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Testa a conexao com o banco e exibe a versao (MariaDB/MySQL/SQLite)."

    def handle(self, *args, **options):
        engine = connection.settings_dict.get("ENGINE", "")
        name = connection.settings_dict.get("NAME", "")
        self.stdout.write(f"ENGINE: {engine}")
        self.stdout.write(f"NAME:   {name}")

        try:
            connection.ensure_connection()
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"Falha na conexao: {exc}"))
            raise SystemExit(1) from exc

        vendor = connection.vendor
        version = ""
        try:
            with connection.cursor() as cursor:
                if vendor in {"mysql", "mariadb"}:
                    cursor.execute("SELECT VERSION()")
                    row = cursor.fetchone()
                    version = row[0] if row else ""
                elif vendor == "sqlite":
                    cursor.execute("SELECT sqlite_version()")
                    row = cursor.fetchone()
                    version = row[0] if row else ""
                else:
                    version = str(connection.get_server_version())
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"Conectou, mas falhou ao ler VERSION: {exc}"))
            raise SystemExit(1) from exc

        self.stdout.write(self.style.SUCCESS(f"OK - vendor={vendor} version={version}"))
