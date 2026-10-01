from django.core.management.base import BaseCommand

from apps.core.prazo_garantia import ensure_regra_padrao_externo
from apps.core.reincidencia import detectar_reincidencia


class Command(BaseCommand):
    help = (
        "Detecta reincidencias (veiculo+peca) a partir de SaidaGlobus. "
        "Rode apos sync_globus --tipo saidas (ou sync completo)."
    )

    def handle(self, *args, **options):
        ensure_regra_padrao_externo()
        result = detectar_reincidencia()
        self.stdout.write(
            self.style.SUCCESS(
                f"reincidencia: pares={result['pares_avaliados']} "
                f"criados={result['criados']} atualizados={result['atualizados']} "
                f"ignorados_descartados={result['ignorados_descartados']}"
            )
        )
