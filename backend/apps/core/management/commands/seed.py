from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from apps.core.models import (
    EventoGarantia,
    Fornecedor,
    Garantia,
    NotaFiscal,
    Peca,
    Usuario,
    Veiculo,
)

# Protocolos / peças de demo antiga — removidos para não poluir a UI
PROTOCOLOS_DEMO_REMOVER = (
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
    help = "Popula usuários e 1 garantia exemplo com peça Globus real (01111011)"

    def handle(self, *args, **options):
        self.stdout.write("Iniciando seed RastroGlobus...")

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

        forn_x, _ = Fornecedor.objects.update_or_create(
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

        veiculos_data = [
            ("47620", "Matriz"),
            ("47885", "Matriz"),
            ("47624", "Matriz"),
            ("46201", "Anexo"),
        ]
        veiculos = {}
        for codigo, casa in veiculos_data:
            v, _ = Veiculo.objects.update_or_create(
                codigo=codigo,
                defaults={"casa": casa, "descricao": f"Veículo {codigo}", "ativo": True},
            )
            veiculos[codigo] = v

        peca, _ = Peca.objects.update_or_create(
            codigo_interno="01111011",
            defaults={
                "descricao": "Peça Globus 01111011 (espelho)",
                "garantia_dias": 365,
                "ativo": True,
            },
        )

        # Remove garantias/peças demo antigas (não usadas mais)
        qs_demo = Garantia.objects.filter(
            Q(protocolo__in=PROTOCOLOS_DEMO_REMOVER)
            | Q(peca__codigo_interno__in=PECAS_DEMO_REMOVER)
            | Q(protocolo__startswith="GAR-2026-000")
        ).exclude(protocolo="GAR-2026-0131")
        removidas = qs_demo.count()
        qs_demo.delete()
        Peca.objects.filter(codigo_interno__in=PECAS_DEMO_REMOVER).delete()
        if removidas:
            self.stdout.write(f"Removidas {removidas} garantias de demonstração antigas.")

        def nf(numero, tipo, data, fornecedor, valor=None):
            obj, _ = NotaFiscal.objects.update_or_create(
                numero=str(numero),
                serie="",
                tipo=tipo,
                defaults={
                    "data_emissao": data,
                    "fornecedor": fornecedor,
                    "valor": valor,
                },
            )
            return obj

        # Uma garantia improcedente com código Globus real (cruzamento com compras)
        criado = timezone.now() - timedelta(days=70)
        valor = Decimal("1840.00")
        remessa = nf(
            "87002",
            NotaFiscal.Tipo.REMESSA,
            criado.date() + timedelta(days=2),
            forn_x,
            valor,
        )
        retorno = nf(
            "4988",
            NotaFiscal.Tipo.RETORNO,
            criado.date() + timedelta(days=20),
            forn_x,
            valor,
        )

        g, _ = Garantia.objects.update_or_create(
            protocolo="GAR-2026-0131",
            defaults={
                "peca": peca,
                "veiculo": veiculos["47624"],
                "fornecedor": forn_x,
                "status": Garantia.Status.IMPROCEDENTE,
                "valor_peca": valor,
                "nota_remessa": remessa,
                "nota_retorno": retorno,
                "data_envio": criado.date() + timedelta(days=2),
                "data_retorno": criado.date() + timedelta(days=20),
                "nf_entrada_globo": "",
                "motivo_improcedente": "Desgaste natural — fora de cobertura.",
                "observacoes": "",
                "laudo_resumo": "Laudo gerado na abertura da garantia.",
                "criado_por": oficina,
                "km_aplicacao": 120000,
                "requisicao_anterior": "REQ-100",
                "requisicao_atual": "REQ-200",
            },
        )
        Garantia.objects.filter(pk=g.pk).update(criado_em=criado)

        EventoGarantia.objects.filter(garantia=g).delete()
        eventos = [
            ("", Garantia.Status.ABERTA, "Garantia aberta / laudo gerado.", oficina),
            (
                Garantia.Status.ABERTA,
                Garantia.Status.ENVIADA,
                "NF remessa 87002 vinculada.",
                admin,
            ),
            (
                Garantia.Status.ENVIADA,
                Garantia.Status.EM_ANALISE,
                "Fornecedor em análise.",
                admin,
            ),
            (
                Garantia.Status.EM_ANALISE,
                Garantia.Status.IMPROCEDENTE,
                "Desgaste natural — fora de cobertura.",
                admin,
            ),
        ]
        for i, (ant, novo, desc, user) in enumerate(eventos):
            ev = EventoGarantia.objects.create(
                garantia=g,
                usuario=user,
                status_anterior=ant,
                status_novo=novo,
                descricao=desc,
            )
            EventoGarantia.objects.filter(pk=ev.pk).update(data=criado + timedelta(days=i * 5))

        self.stdout.write(self.style.SUCCESS("Seed concluído."))
        self.stdout.write(
            "Usuários: admin/admin123 | manutencao/manut123 | oficina/oficina123 | "
            "compras/compras123 | direcao/direcao123"
        )
        self.stdout.write(
            f"Garantias: {Garantia.objects.count()} "
            f"(exemplo Globus: GAR-2026-0131 / peça 01111011)"
        )
