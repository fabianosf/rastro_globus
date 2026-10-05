"""Checks automaticos de go-live (parte tecnica do aceite ops)."""

from django.core.management.base import BaseCommand

from apps.core.globus_conf import load_globus_settings, resolve_conf_dir
from apps.core.globus_sync import sync_status_payload
from apps.core.models import (
    CompraGlobus,
    Garantia,
    HistoricoGarantiaMensal,
    PecaGlobus,
    SaidaGlobus,
    SyncLog,
)


class Command(BaseCommand):
    help = "Checklist tecnico go-live SGGI (sem inventar dados)."

    def handle(self, *args, **options):
        fail = 0

        def ok(msg: str) -> None:
            self.stdout.write(self.style.SUCCESS(f"[OK] {msg}"))

        def warn(msg: str) -> None:
            self.stdout.write(self.style.WARNING(f"[WARN] {msg}"))

        def bad(msg: str) -> None:
            nonlocal fail
            fail += 1
            self.stdout.write(self.style.ERROR(f"[FAIL] {msg}"))

        conf = resolve_conf_dir()
        settings = load_globus_settings()
        if conf and settings:
            ok(f"conf/ Oracle carregada ({conf})")
        else:
            bad("conf/ ausente ou erp.dat invalido")

        payload = sync_status_payload(ping_oracle=True)
        if payload.get("oracle_ok"):
            ok("ping Oracle OK")
        else:
            warn(f"ping Oracle: {payload.get('oracle_detail') or payload.get('detail')}")

        pecas = PecaGlobus.objects.count()
        compras = CompraGlobus.objects.count()
        saidas = SaidaGlobus.objects.count()
        if pecas > 0:
            ok(f"espelho pecas populado ({pecas})")
        else:
            bad("espelho pecas vazio")
        if compras > 0:
            ok(f"espelho compras populado ({compras})")
        else:
            bad("espelho compras vazio")
        if saidas > 0:
            ok(f"espelho saidas populado ({saidas})")
        else:
            warn("espelho saidas vazio ou sync ainda nao concluiu")

        hist = HistoricoGarantiaMensal.objects.count()
        if hist > 0:
            ok(f"HistoricoGarantiaMensal importado ({hist})")
        else:
            warn("historico=0 — coloque xlsx em docs/ops/incoming e rode import_planilha_real.ps1")

        g = Garantia.objects.count()
        if g > 0:
            ok(f"ha Garantia no banco ({g})")
        else:
            warn("garantias=0 — operacao ainda nao criou casos reais")

        bad_nf = Garantia.objects.filter(status=Garantia.Status.IMPROCEDENTE).exclude(
            nf_entrada_globo=""
        ).count()
        if bad_nf == 0:
            ok("nenhum improcedente com nf_entrada_globo indevido")
        else:
            bad(f"improcedentes com nf_entrada_globo={bad_nf}")

        if payload.get("em_andamento"):
            warn("sync ainda em andamento")

        latest = list(
            SyncLog.objects.order_by("-inicio")[:5].values_list("tipo", "status", "fim")
        )
        self.stdout.write(f"synclog_recente={latest}")
        self.stdout.write(f"status_detail={payload.get('detail')}")

        self.stdout.write("")
        self.stdout.write("Manuais (doc ops secao 4):")
        self.stdout.write("  [ ] DATA_CORTE 2026-10-06 comunicada; Excel sem casos novos")
        self.stdout.write("  [ ] Rubrica Matheus (secao 5)")
        self.stdout.write("  [ ] Fluxo improcedente real testado na UI")
        self.stdout.write("  [ ] Dashboard/Relatorios conferidos no ano corrente")

        if fail:
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS("RESULTADO: checks automaticos OK (completar manuais)"))
