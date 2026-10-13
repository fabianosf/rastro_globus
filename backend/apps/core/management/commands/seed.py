from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.core.models import (
    Fornecedor,
    Garantia,
    Peca,
    Usuario,
    Veiculo,
)

# Protocolos / peças de demo — removidos para não poluir a UI / relatório
PROTOCOLOS_DEMO_REMOVER = (
    "GAR-2026-0131",
    "GAR-2026-0142",
    "GAR-2026-0138",
    "GAR-2026-0126",
    "GAR-2026-0119",
    "GAR-2026-000144",
)
PECAS_DEMO_REMOVER = (
    "EMB-0144",
    "CXA-0901",
    "ALT-0330",
    "BMB-0102",
    "10110114",
)


class Command(BaseCommand):
    help = "Popula usuários, cadastros base e peça/veículo Globus (sem garantia demo)"

    def handle(self, *args, **options):
        self.stdout.write("Iniciando seed SGGI...")

        admin, _ = Usuario.objects.update_or_create(
            username="admin",
            defaults={
                "perfil": Usuario.Perfil.ADMIN,
                "is_staff": True,
                "is_superuser": True,
                "first_name": "Admin",
                "email": "admin@rastroglobus.local",
            },
        )
        admin.set_password("admin123")
        admin.save()

        manut, _ = Usuario.objects.update_or_create(
            username="manutencao",
            defaults={
                "perfil": Usuario.Perfil.MANUTENCAO,
                "first_name": "Manutenção",
                "email": "manutencao@rastroglobus.local",
            },
        )
        manut.set_password("manut123")
        manut.save()

        oficina, _ = Usuario.objects.update_or_create(
            username="oficina",
            defaults={
                "perfil": Usuario.Perfil.OFICINA,
                "first_name": "Oficina",
                "email": "oficina@rastroglobus.local",
            },
        )
        oficina.set_password("oficina123")
        oficina.save()

        compras, _ = Usuario.objects.update_or_create(
            username="compras",
            defaults={
                "perfil": Usuario.Perfil.COMPRAS,
                "first_name": "Compras",
                "email": "compras@rastroglobus.local",
            },
        )
        compras.set_password("compras123")
        compras.save()

        direcao, _ = Usuario.objects.update_or_create(
            username="direcao",
            defaults={
                "perfil": Usuario.Perfil.DIRECAO,
                "first_name": "Direção",
                "email": "direcao@rastroglobus.local",
            },
        )
        direcao.set_password("direcao123")
        direcao.save()

        Fornecedor.objects.update_or_create(
            cnpj="00.000.000/0001-00",
            defaults={
                "razao_social": "Distribuidor X Ltda",
                "nome_fantasia": "Distribuidor X",
                "contato": "João",
                "email": "contato@distribuidorx.local",
                "telefone": "(11) 3000-0000",
                "ativo": True,
            },
        )
        Fornecedor.objects.update_or_create(
            cnpj="11.111.111/0001-11",
            defaults={
                "razao_social": "Fabricante Y S.A.",
                "nome_fantasia": "Fabricante Y",
                "contato": "Maria",
                "email": "garantias@fabricantey.local",
                "telefone": "(11) 4000-0000",
                "ativo": True,
            },
        )

        for codigo, casa in (
            ("47620", "Matriz"),
            ("47885", "Matriz"),
            ("47624", "Matriz"),
            ("46201", "Anexo"),
        ):
            Veiculo.objects.update_or_create(
                codigo=codigo,
                defaults={"casa": casa, "descricao": f"Veículo {codigo}", "ativo": True},
            )

        peca, _ = Peca.objects.update_or_create(
            codigo_interno="01111011",
            defaults={
                "descricao": "Peça Globus 01111011 (espelho)",
                "garantia_dias": 365,
                "ativo": True,
            },
        )

        # Remove garantias/peças demo (não poluir Minhas NFs nem Custo do erro interno)
        qs_demo = Garantia.objects.filter(
            Q(protocolo__in=PROTOCOLOS_DEMO_REMOVER)
            | Q(peca__codigo_interno__in=PECAS_DEMO_REMOVER)
            | Q(protocolo__startswith="GAR-2026-000")
            | Q(protocolo__startswith="GAR-TEST-")
        )
        removidas = qs_demo.count()
        qs_demo.delete()
        Peca.objects.filter(codigo_interno__in=PECAS_DEMO_REMOVER).delete()
        if removidas:
            self.stdout.write(f"Removidas {removidas} garantias de demonstração.")

        from apps.core.prazo_garantia import ensure_regra_padrao_externo

        ensure_regra_padrao_externo()

        self.stdout.write(self.style.SUCCESS("Seed concluído."))
        self.stdout.write(
            "Usuários: admin/admin123 | manutencao/manut123 | oficina/oficina123 | "
            "compras/compras123 | direcao/direcao123"
        )
        self.stdout.write(
            f"Cadastros: {Garantia.objects.count()} garantia(s) · "
            f"peça base {peca.codigo_interno} · veículos Globus de exemplo ok"
        )
        self.stdout.write("RegraPrazoGarantia padrao: tipo_servico=externo -> 180 dias")
