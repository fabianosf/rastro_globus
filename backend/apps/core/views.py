import csv
import hashlib
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import (
    Anexo,
    Fornecedor,
    Garantia,
    HistoricoGarantiaMensal,
    NotaFiscal,
    Peca,
    Usuario,
    Veiculo,
)
from .planilha_import import EMPRESAS, normalize_empresa
from .permissions import (
    CanAnexar,
    CanChangeStatus,
    CanCreateGarantia,
    CanEditGarantia,
    CanVincularNota,
    IsNotDirecaoWrite,
)
from .serializers import (
    AnexoSerializer,
    FornecedorSerializer,
    GarantiaCreateSerializer,
    GarantiaDetailSerializer,
    GarantiaListSerializer,
    NotaFiscalSerializer,
    PecaSerializer,
    StatusChangeSerializer,
    UsuarioSerializer,
    VeiculoSerializer,
    VincularNotaSerializer,
)
from .services import mudar_status


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username", "")
        password = request.data.get("password", "")
        try:
            user = Usuario.objects.get(username=username)
        except Usuario.DoesNotExist:
            return Response(
                {"detail": "Usuário ou senha inválidos."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if not user.check_password(password):
            return Response(
                {"detail": "Usuário ou senha inválidos."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if not user.is_active:
            return Response(
                {"detail": "Usuário inativo."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UsuarioSerializer(user).data,
            }
        )


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UsuarioSerializer(request.user).data)


class FornecedorViewSet(viewsets.ModelViewSet):
    queryset = Fornecedor.objects.all().order_by("razao_social")
    serializer_class = FornecedorSerializer
    permission_classes = [IsAuthenticated, IsNotDirecaoWrite]
    http_method_names = ["get", "post", "head", "options"]

    @action(detail=False, methods=["post"], url_path="ensure")
    def ensure(self, request):
        """Espelho local a partir do Globus (não grava no Oracle)."""
        codigo = str(request.data.get("codigo_externo") or "").strip()
        nome = str(
            request.data.get("nome_fantasia")
            or request.data.get("razao_social")
            or ""
        ).strip()
        razao = str(request.data.get("razao_social") or nome).strip()
        if not nome and not codigo:
            return Response(
                {"detail": "Informe nome_fantasia ou codigo_externo."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not nome:
            nome = f"Fornecedor Globus {codigo}"
        if not razao:
            razao = nome

        obj = None
        if codigo:
            cnpj_key = f"GL-{codigo}"[:18]
            obj = Fornecedor.objects.filter(cnpj=cnpj_key).first()
            if not obj:
                obj = Fornecedor.objects.filter(nome_fantasia__iexact=nome).first()
            if obj:
                changed = False
                if nome and obj.nome_fantasia != nome:
                    obj.nome_fantasia = nome
                    changed = True
                if razao and obj.razao_social != razao:
                    obj.razao_social = razao
                    changed = True
                if changed:
                    obj.save(update_fields=["nome_fantasia", "razao_social"])
            else:
                obj = Fornecedor.objects.create(
                    cnpj=cnpj_key,
                    razao_social=razao[:200],
                    nome_fantasia=nome[:200],
                    contato="Globus (espelho)",
                    ativo=True,
                )
        else:
            obj = Fornecedor.objects.filter(nome_fantasia__iexact=nome).first()
            if not obj:
                # CNPJ sintético estável a partir do nome (máx. 18)
                digest = hashlib.md5(nome.lower().encode()).hexdigest()[:12]
                cnpj_key = f"GL-N{digest}"[:18]
                obj, _ = Fornecedor.objects.get_or_create(
                    cnpj=cnpj_key,
                    defaults={
                        "razao_social": razao[:200],
                        "nome_fantasia": nome[:200],
                        "contato": "Globus (espelho)",
                        "ativo": True,
                    },
                )
        return Response(FornecedorSerializer(obj).data)


class VeiculoViewSet(viewsets.ModelViewSet):
    queryset = Veiculo.objects.all().order_by("codigo")
    serializer_class = VeiculoSerializer
    permission_classes = [IsAuthenticated, IsNotDirecaoWrite]
    http_method_names = ["get", "post", "head", "options"]

    @action(detail=False, methods=["post"], url_path="ensure")
    def ensure(self, request):
        codigo = str(request.data.get("codigo") or "").strip()
        if not codigo:
            return Response({"detail": "Informe o código do veículo."}, status=status.HTTP_400_BAD_REQUEST)
        placa = str(request.data.get("placa") or "").strip()[:10]
        descricao = str(request.data.get("descricao") or f"Veículo {codigo}").strip()[:200]
        casa = str(request.data.get("casa") or "").strip()[:80]
        obj, created = Veiculo.objects.get_or_create(
            codigo=codigo,
            defaults={"placa": placa, "descricao": descricao, "casa": casa, "ativo": True},
        )
        if not created:
            update_fields = []
            if placa and obj.placa != placa:
                obj.placa = placa
                update_fields.append("placa")
            if descricao and obj.descricao != descricao:
                obj.descricao = descricao
                update_fields.append("descricao")
            if casa and obj.casa != casa:
                obj.casa = casa
                update_fields.append("casa")
            if not obj.ativo:
                obj.ativo = True
                update_fields.append("ativo")
            if update_fields:
                obj.save(update_fields=update_fields)
        return Response(VeiculoSerializer(obj).data)


class PecaViewSet(viewsets.ModelViewSet):
    queryset = Peca.objects.all().order_by("codigo_interno")
    serializer_class = PecaSerializer
    permission_classes = [IsAuthenticated, IsNotDirecaoWrite]
    http_method_names = ["get", "post", "head", "options"]

    @action(detail=False, methods=["post"], url_path="ensure")
    def ensure(self, request):
        codigo = str(request.data.get("codigo_interno") or "").strip()
        if not codigo:
            return Response(
                {"detail": "Informe codigo_interno."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        descricao = str(request.data.get("descricao") or codigo).strip()[:255]
        obj, created = Peca.objects.get_or_create(
            codigo_interno=codigo,
            defaults={"descricao": descricao, "garantia_dias": 365, "ativo": True},
        )
        if not created:
            update_fields = []
            if descricao and obj.descricao != descricao:
                obj.descricao = descricao
                update_fields.append("descricao")
            if not obj.ativo:
                obj.ativo = True
                update_fields.append("ativo")
            if update_fields:
                obj.save(update_fields=update_fields)
        return Response(PecaSerializer(obj).data)


class NotaFiscalViewSet(viewsets.ModelViewSet):
    queryset = NotaFiscal.objects.all().order_by("-data_emissao")
    serializer_class = NotaFiscalSerializer
    permission_classes = [IsAuthenticated, IsNotDirecaoWrite]
    http_method_names = ["get", "post", "head", "options"]


class GarantiaViewSet(viewsets.ModelViewSet):
    queryset = Garantia.objects.select_related(
        "peca", "veiculo", "fornecedor", "nota_remessa", "nota_retorno", "nota_compra", "criado_por"
    ).prefetch_related("eventos", "anexos")
    permission_classes = [IsAuthenticated]
    # Sem DELETE: EventoGarantia nunca deve ser apagado em cascata via API
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), CanCreateGarantia()]
        if self.action in ("partial_update", "update"):
            return [IsAuthenticated(), CanEditGarantia()]
        if self.action == "status":
            return [IsAuthenticated(), CanChangeStatus()]
        if self.action == "anexos":
            return [IsAuthenticated(), CanAnexar()]
        if self.action == "vincular_nota":
            return [IsAuthenticated(), CanVincularNota()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "create":
            return GarantiaCreateSerializer
        if self.action in ("retrieve", "partial_update", "update"):
            return GarantiaDetailSerializer
        return GarantiaListSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        if status_f := params.get("status"):
            qs = qs.filter(status=status_f)
        if peca := params.get("peca"):
            qs = qs.filter(
                Q(peca_id=peca)
                | Q(peca__codigo_interno__icontains=peca)
                | Q(peca__descricao__icontains=peca)
            )
        if veiculo := params.get("veiculo"):
            qs = qs.filter(Q(veiculo_id=veiculo) | Q(veiculo__codigo__icontains=veiculo))
        if fornecedor := params.get("fornecedor"):
            qs = qs.filter(
                Q(fornecedor_id=fornecedor)
                | Q(fornecedor__razao_social__icontains=fornecedor)
                | Q(fornecedor__nome_fantasia__icontains=fornecedor)
            )

        data_ini = (params.get("data_ini") or "").strip()
        data_fim = (params.get("data_fim") or "").strip()
        periodo_ativo = bool(data_ini or data_fim)

        def _parse_day(value: str) -> date | None:
            try:
                return datetime.strptime(value[:10], "%Y-%m-%d").date()
            except ValueError:
                return None

        if periodo_ativo:
            if data_ini:
                d0 = _parse_day(data_ini)
                if d0:
                    qs = qs.filter(criado_em__date__gte=d0)
            if data_fim:
                d1 = _parse_day(data_fim)
                if d1:
                    qs = qs.filter(criado_em__date__lte=d1)
        elif ano := params.get("ano"):
            qs = qs.filter(criado_em__year=ano)

        if q := params.get("q"):
            qs = qs.filter(
                Q(protocolo__icontains=q)
                | Q(peca__codigo_interno__icontains=q)
                | Q(peca__descricao__icontains=q)
                | Q(veiculo__codigo__icontains=q)
                | Q(fornecedor__nome_fantasia__icontains=q)
                | Q(fornecedor__razao_social__icontains=q)
            )

        if (params.get("parado_45") or "").strip() in {"1", "true", "yes"}:
            abertos = [
                Garantia.Status.ABERTA,
                Garantia.Status.ENVIADA,
                Garantia.Status.EM_ANALISE,
            ]
            limite = timezone.now() - timedelta(days=45)
            qs = qs.filter(status__in=abertos, criado_em__lt=limite)

        return qs

    def list(self, request, *args, **kwargs):
        """Lista garantias RG enriquecida com ultima compra do espelho CompraGlobus."""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        data = list(serializer.data)

        from .globus_sync import compras_por_codigos_local, sync_status_payload

        status_sync = sync_status_payload()
        globus_ok = bool(status_sync.get("ok"))
        globus_detail = status_sync.get("detail") or ""
        compras_map: dict = {}
        codigos = [row.get("peca_codigo") for row in data if row.get("peca_codigo")]
        if codigos:
            compras_map = compras_por_codigos_local(codigos, limite_por_peca=1)

        for row in data:
            codigo = row.get("peca_codigo") or ""
            compras = compras_map.get(codigo, [])
            if not compras:
                for k, v in compras_map.items():
                    if k.lower() == codigo.lower():
                        compras = v
                        break
            ultima = compras[0] if compras else None
            row["ultima_compra_globus"] = ultima
            row["globus_ok"] = globus_ok

        com_nf = (request.query_params.get("com_nf_globus") or "").strip() in {
            "1",
            "true",
            "yes",
        }
        sem_nf = (request.query_params.get("sem_nf_globus") or "").strip() in {
            "1",
            "true",
            "yes",
        }
        if com_nf and not sem_nf:
            data = [
                r
                for r in data
                if (r.get("ultima_compra_globus") or {}).get("numero_nf")
            ]
        elif sem_nf and not com_nf:
            data = [
                r
                for r in data
                if not (r.get("ultima_compra_globus") or {}).get("numero_nf")
            ]

        response = Response(data)
        response["X-Globus-Ok"] = "1" if globus_ok else "0"
        if globus_detail:
            response["X-Globus-Detail"] = globus_detail[:200]
        return response

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        garantia = serializer.save()
        return Response(
            GarantiaDetailSerializer(garantia, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def status(self, request, pk=None):
        garantia = self.get_object()
        ser = StatusChangeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        try:
            mudar_status(
                garantia,
                data["status"],
                request.user,
                data.get("descricao", ""),
                motivo_improcedente=data.get("motivo_improcedente", ""),
                nf_entrada_globo=data.get("nf_entrada_globo", ""),
            )
        except DjangoValidationError as exc:
            msg = exc.messages[0] if hasattr(exc, "messages") else str(exc)
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)
        garantia.refresh_from_db()
        return Response(GarantiaDetailSerializer(garantia, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def anexos(self, request, pk=None):
        garantia = self.get_object()
        arquivo = request.FILES.get("arquivo")
        if not arquivo:
            return Response({"detail": "Arquivo obrigatório."}, status=status.HTTP_400_BAD_REQUEST)
        anexo = Anexo.objects.create(
            garantia=garantia,
            arquivo=arquivo,
            descricao=request.data.get("descricao", ""),
            enviado_por=request.user,
        )
        return Response(AnexoSerializer(anexo, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="notas")
    def vincular_nota(self, request, pk=None):
        garantia = self.get_object()
        ser = VincularNotaSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        nota, _ = NotaFiscal.objects.get_or_create(
            numero=data["numero"],
            serie=data.get("serie", ""),
            tipo=data["tipo"],
            defaults={
                "data_emissao": data["data_emissao"],
                "valor": data.get("valor"),
                "fornecedor": garantia.fornecedor,
            },
        )
        tipo = data["tipo"]
        if tipo == NotaFiscal.Tipo.COMPRA:
            garantia.nota_compra = nota
            if not garantia.data_compra:
                garantia.data_compra = data["data_emissao"]
        elif tipo == NotaFiscal.Tipo.REMESSA:
            garantia.nota_remessa = nota
            if not garantia.data_envio:
                garantia.data_envio = data["data_emissao"]
        elif tipo == NotaFiscal.Tipo.RETORNO:
            garantia.nota_retorno = nota
            if not garantia.data_retorno:
                garantia.data_retorno = data["data_emissao"]
        garantia.save()
        return Response(GarantiaDetailSerializer(garantia, context={"request": request}).data)


def _garantias_ano(ano):
    return Garantia.objects.filter(criado_em__year=ano).select_related("peca", "veiculo", "fornecedor")


def _dashboard_payload(ano):
    qs = _garantias_ano(ano)
    contagem = {s: 0 for s, _ in Garantia.Status.choices}
    for row in qs.values("status").annotate(total=Count("id")):
        contagem[row["status"]] = row["total"]

    valor_procedente = qs.filter(status=Garantia.Status.PROCEDENTE).aggregate(
        t=Sum("valor_peca")
    )["t"] or Decimal("0")
    valor_improcedente = qs.filter(status=Garantia.Status.IMPROCEDENTE).aggregate(
        t=Sum("valor_peca")
    )["t"] or Decimal("0")
    abertos = {
        Garantia.Status.ABERTA,
        Garantia.Status.ENVIADA,
        Garantia.Status.EM_ANALISE,
    }
    valor_aberto = qs.filter(status__in=abertos).aggregate(t=Sum("valor_peca"))["t"] or Decimal("0")

    ranking_pecas = list(
        qs.values("peca_id", "peca__codigo_interno", "peca__descricao")
        .annotate(total=Count("id"), valor=Sum("valor_peca"))
        .order_by("-total")[:10]
    )

    ranking_veiculos = list(
        qs.values("veiculo_id", "veiculo__codigo", "veiculo__casa")
        .annotate(total=Count("id"))
        .filter(total__gte=2)
        .order_by("-total")
    )

    limite = timezone.now() - timedelta(days=45)
    parados = list(
        qs.filter(status__in=abertos, criado_em__lt=limite)
        .order_by("criado_em")
        .values(
            "id",
            "protocolo",
            "status",
            "criado_em",
            "peca__descricao",
            "veiculo__codigo",
            "valor_peca",
        )[:20]
    )

    return {
        "ano": ano,
        "contagem_status": contagem,
        "valor_procedente": str(valor_procedente),
        "valor_improcedente": str(valor_improcedente),
        "valor_aberto": str(valor_aberto),
        "ranking_pecas": [
            {
                "peca_id": r["peca_id"],
                "codigo": r["peca__codigo_interno"],
                "descricao": r["peca__descricao"],
                "total": r["total"],
                "valor": str(r["valor"] or 0),
            }
            for r in ranking_pecas
        ],
        "veiculos_alerta": [
            {
                "veiculo_id": r["veiculo_id"],
                "codigo": r["veiculo__codigo"],
                "casa": r["veiculo__casa"],
                "total": r["total"],
            }
            for r in ranking_veiculos
        ],
        "parados_45_dias": [
            {
                "id": p["id"],
                "protocolo": p["protocolo"],
                "status": p["status"],
                "criado_em": p["criado_em"],
                "peca": p["peca__descricao"],
                "veiculo": p["veiculo__codigo"],
                "valor_peca": str(p["valor_peca"] or 0),
            }
            for p in parados
        ],
    }


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ano = int(request.query_params.get("ano", timezone.now().year))
        payload = _dashboard_payload(ano)

        globus_ok = False
        globus_detail = ""
        movimentos: list = []
        compras: list = []
        try:
            from .globus_oracle import GlobusOracleClient
            from .globus_queries import buscar_compras_recentes, buscar_movimentos

            client = GlobusOracleClient()
            if client.configured:
                ok, detail, _ = client.ping()
                globus_ok = ok
                globus_detail = detail
                if ok:
                    movimentos = buscar_movimentos(tipo="todos", limite=8)
                    compras = buscar_compras_recentes(limite=8)
            else:
                globus_detail = "conf/ Oracle não configurado. Painel Globus indisponível."
        except Exception as exc:
            globus_ok = False
            globus_detail = f"Painel Globus indisponível: {exc}"

        payload["globus"] = {
            "ok": globus_ok,
            "detail": globus_detail,
            "movimentos_recentes": movimentos,
            "compras_recentes": compras,
            "readonly": True,
            "aviso": "Dados Globus em tempo real (somente leitura). Estoque continua no Globo.",
        }
        return Response(payload)


class RelatorioResumoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ano = int(request.query_params.get("ano", timezone.now().year))
        return Response(_dashboard_payload(ano))


class RankingPecasView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ano = int(request.query_params.get("ano", timezone.now().year))
        return Response(_dashboard_payload(ano)["ranking_pecas"])


class RankingVeiculosView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ano = int(request.query_params.get("ano", timezone.now().year))
        return Response(_dashboard_payload(ano)["veiculos_alerta"])


MERGE_HISTORICO_APP_FROM = date(2026, 10, 1)


def _money_bucket():
    return {
        "solicitado": Decimal("0"),
        "concedido": Decimal("0"),
        "em_analise": Decimal("0"),
        "negado": Decimal("0"),
    }


def _add_bucket(target, concedido=0, em_analise=0, negado=0):
    c = Decimal(concedido or 0)
    e = Decimal(em_analise or 0)
    n = Decimal(negado or 0)
    target["concedido"] += c
    target["em_analise"] += e
    target["negado"] += n
    target["solicitado"] += c + e + n


def _garantia_status_bucket(status: str) -> str | None:
    if status in {Garantia.Status.PROCEDENTE, Garantia.Status.CORTESIA}:
        return "concedido"
    if status in {
        Garantia.Status.ABERTA,
        Garantia.Status.ENVIADA,
        Garantia.Status.EM_ANALISE,
    }:
        return "em_analise"
    if status == Garantia.Status.IMPROCEDENTE:
        return "negado"
    return None


def _historico_payload(ano: int, empresa: str = "", fornecedor_id: int | None = None):
    qs = HistoricoGarantiaMensal.objects.filter(competencia__year=ano).select_related(
        "fornecedor"
    )
    if empresa:
        qs = qs.filter(empresa=empresa)
    if fornecedor_id:
        qs = qs.filter(fornecedor_id=fornecedor_id)

    por_mes: dict[str, dict] = {}
    por_empresa: dict[str, dict] = {}
    ranking: dict[int, dict] = {}
    totais = _money_bucket()

    for row in qs:
        key_mes = row.competencia.strftime("%Y-%m")
        if key_mes not in por_mes:
            por_mes[key_mes] = {"competencia": key_mes, **_money_bucket()}
        _add_bucket(
            por_mes[key_mes],
            row.valor_concedido,
            row.valor_em_analise,
            row.valor_negado,
        )

        if row.empresa not in por_empresa:
            por_empresa[row.empresa] = {"empresa": row.empresa, **_money_bucket()}
        _add_bucket(
            por_empresa[row.empresa],
            row.valor_concedido,
            row.valor_em_analise,
            row.valor_negado,
        )

        fid = row.fornecedor_id
        if fid not in ranking:
            ranking[fid] = {
                "fornecedor_id": fid,
                "fornecedor": str(row.fornecedor),
                **_money_bucket(),
            }
        _add_bucket(
            ranking[fid],
            row.valor_concedido,
            row.valor_em_analise,
            row.valor_negado,
        )
        _add_bucket(totais, row.valor_concedido, row.valor_em_analise, row.valor_negado)

    # Merge garantias do app a partir de out/2026
    if date(ano, 12, 31) >= MERGE_HISTORICO_APP_FROM:
        gqs = Garantia.objects.filter(criado_em__year=ano).select_related(
            "fornecedor", "veiculo"
        )
        if fornecedor_id:
            gqs = gqs.filter(fornecedor_id=fornecedor_id)
        if ano == MERGE_HISTORICO_APP_FROM.year:
            gqs = gqs.filter(criado_em__month__gte=MERGE_HISTORICO_APP_FROM.month)

        for g in gqs:
            bucket = _garantia_status_bucket(g.status)
            if not bucket:
                continue
            competencia = date(g.criado_em.year, g.criado_em.month, 1)
            if competencia < MERGE_HISTORICO_APP_FROM:
                continue
            casa = normalize_empresa(g.veiculo.casa if g.veiculo_id else "")
            if empresa and casa != empresa:
                continue

            valor = g.valor_peca or Decimal("0")
            kwargs = {bucket: valor}
            key_mes = competencia.strftime("%Y-%m")
            if key_mes not in por_mes:
                por_mes[key_mes] = {"competencia": key_mes, **_money_bucket()}
            _add_bucket(por_mes[key_mes], **kwargs)
            _add_bucket(totais, **kwargs)

            fid = g.fornecedor_id
            if fid not in ranking:
                ranking[fid] = {
                    "fornecedor_id": fid,
                    "fornecedor": str(g.fornecedor),
                    **_money_bucket(),
                }
            _add_bucket(ranking[fid], **kwargs)

            if casa in EMPRESAS:
                if casa not in por_empresa:
                    por_empresa[casa] = {"empresa": casa, **_money_bucket()}
                _add_bucket(por_empresa[casa], **kwargs)

    def _serialize_money(d):
        out = {k: v for k, v in d.items() if k not in _money_bucket()}
        for k in ("solicitado", "concedido", "em_analise", "negado"):
            if k in d:
                out[k] = str(d[k])
        return out

    ranking_list = sorted(
        ranking.values(), key=lambda r: r["negado"], reverse=True
    )[:20]

    return {
        "ano": ano,
        "empresa": empresa or None,
        "fornecedor": fornecedor_id,
        "merge_app_from": MERGE_HISTORICO_APP_FROM.isoformat(),
        "por_mes": [_serialize_money(por_mes[k]) for k in sorted(por_mes.keys())],
        "por_empresa": [
            _serialize_money(por_empresa[k]) for k in sorted(por_empresa.keys())
        ],
        "ranking_negado": [_serialize_money(r) for r in ranking_list],
        "totais": {
            k: str(totais[k]) for k in ("solicitado", "concedido", "em_analise", "negado")
        },
    }


class RelatorioHistoricoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ano = int(request.query_params.get("ano", timezone.now().year))
        empresa = normalize_empresa(request.query_params.get("empresa", ""))
        if empresa and empresa not in EMPRESAS:
            return Response(
                {"detail": f"empresa invalida. Use: {', '.join(sorted(EMPRESAS))}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        fornecedor_raw = request.query_params.get("fornecedor", "").strip()
        fornecedor_id = int(fornecedor_raw) if fornecedor_raw.isdigit() else None
        return Response(_historico_payload(ano, empresa=empresa, fornecedor_id=fornecedor_id))


class ExportCsvView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ano = int(request.query_params.get("ano", timezone.now().year))
        qs = _garantias_ano(ano).order_by("protocolo")
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="garantias-{ano}.csv"'
        response.write("\ufeff")
        writer = csv.writer(response, delimiter=";")
        writer.writerow(
            [
                "Protocolo",
                "Peça",
                "Veículo",
                "Fornecedor",
                "Status",
                "NF Remessa",
                "NF Retorno",
                "NF Entrada Globo",
                "Valor",
                "Criado em",
            ]
        )
        for g in qs:
            writer.writerow(
                [
                    g.protocolo,
                    f"{g.peca.codigo_interno} - {g.peca.descricao}",
                    g.veiculo.codigo,
                    str(g.fornecedor),
                    g.status,
                    g.nota_remessa.numero if g.nota_remessa_id else "",
                    g.nota_retorno.numero if g.nota_retorno_id else "",
                    g.nf_entrada_globo if g.status == Garantia.Status.PROCEDENTE else "",
                    g.valor_peca or "",
                    g.criado_em.strftime("%d/%m/%Y %H:%M"),
                ]
            )
        return response


class GlobusStatusView(APIView):
    """Status do espelho local (SyncLog). Oracle e lido so pelo job sync_globus."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .globus_sync import sync_status_payload

        payload = sync_status_payload()
        ok = bool(payload.get("ok"))
        return Response(
            payload,
            status=status.HTTP_200_OK if ok else status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class GlobusNfView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .globus_oracle import GlobusOracleError
        from .globus_queries import buscar_nfs

        numero = request.query_params.get("numero", "").strip()
        try:
            rows = buscar_nfs(numero)
        except GlobusOracleError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"detail": f"Falha ao consultar NF no Globus: {exc}"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"count": len(rows), "results": rows})


class GlobusNfsGarantiaView(APIView):
    """NFs Globus tipo NEG/NFG (garantia) — somente leitura."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .globus_oracle import GlobusOracleError
        from .globus_queries import buscar_nfs_garantia

        try:
            rows = buscar_nfs_garantia(
                numero=request.query_params.get("numero", ""),
                peca=request.query_params.get("peca", ""),
                data_ini=request.query_params.get("data_ini"),
                data_fim=request.query_params.get("data_fim"),
                limite=request.query_params.get("limite", 20),
            )
        except GlobusOracleError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"detail": f"Falha ao consultar NFs de garantia no Globus: {exc}"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(
            {
                "count": len(rows),
                "results": rows,
                "readonly": True,
                "tipos": ["NEG", "NFG"],
                "aviso": (
                    "NFs Globus NEG/NFG (garantia) — somente leitura. "
                    "Não altera estoque nem define improcedente."
                ),
            }
        )


class GlobusVeiculosView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .globus_oracle import GlobusOracleError
        from .globus_queries import buscar_veiculos

        q = request.query_params.get("q", "").strip()
        try:
            rows = buscar_veiculos(q)
        except GlobusOracleError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"detail": f"Falha ao consultar veículos no Globus: {exc}"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"count": len(rows), "results": rows})


class GlobusPecasView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .globus_oracle import GlobusOracleError
        from .globus_queries import buscar_pecas

        q = request.query_params.get("q", "").strip()
        try:
            rows = buscar_pecas(q)
        except GlobusOracleError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"detail": f"Falha ao consultar peças no Globus: {exc}"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"count": len(rows), "results": rows})


class GlobusMovimentosView(APIView):
    """Entrada/saída de peças no Globus — somente leitura (não altera saldo)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .globus_oracle import GlobusOracleError
        from .globus_queries import buscar_movimentos

        try:
            rows = buscar_movimentos(
                peca=request.query_params.get("peca", ""),
                veiculo=request.query_params.get("veiculo", ""),
                data_ini=request.query_params.get("data_ini"),
                data_fim=request.query_params.get("data_fim"),
                tipo=request.query_params.get("tipo", "todos"),
                limite=request.query_params.get("limite", 100),
            )
        except GlobusOracleError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"detail": f"Falha ao consultar movimentos no Globus: {exc}"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(
            {
                "count": len(rows),
                "results": rows,
                "readonly": True,
                "aviso": "Consulta somente leitura. Estoque continua no Globo.",
            }
        )


class GlobusComprasView(APIView):
    """Aquisição/compras de peças no Globus (padrão relatório interno) — só leitura."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .globus_oracle import GlobusOracleError
        from .globus_queries import buscar_compras_peca

        peca = request.query_params.get("peca", "").strip()
        try:
            rows = buscar_compras_peca(
                peca,
                data_ini=request.query_params.get("data_ini"),
                data_fim=request.query_params.get("data_fim"),
                limite=request.query_params.get("limite", 20),
            )
        except GlobusOracleError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"detail": f"Falha ao consultar compras no Globus: {exc}"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(
            {
                "count": len(rows),
                "results": rows,
                "readonly": True,
                "aviso": "Compras Globus (somente leitura). Não altera estoque.",
            }
        )


class ImprocedentesComprasView(APIView):
    """
    Cruza garantias improcedentes (RG) com compras do espelho CompraGlobus.
    Improcedente NAO vem do Globo — so do RastroGlobus. Oracle fora do ar nao impede.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.utils import timezone as tz

        from .globus_sync import compras_por_codigos_local, sync_status_payload

        try:
            ano = int(request.query_params.get("ano", tz.now().year))
        except (TypeError, ValueError):
            return Response({"detail": "Ano invalido."}, status=status.HTTP_400_BAD_REQUEST)

        peca_filtro = request.query_params.get("peca", "").strip()
        qs = (
            Garantia.objects.filter(status=Garantia.Status.IMPROCEDENTE, criado_em__year=ano)
            .select_related("peca", "veiculo", "fornecedor", "nota_compra")
            .order_by("-criado_em")
        )
        if peca_filtro:
            qs = qs.filter(
                Q(peca__codigo_interno__icontains=peca_filtro)
                | Q(peca__descricao__icontains=peca_filtro)
            )

        garantias = list(qs[:200])
        codigos = [g.peca.codigo_interno for g in garantias if g.peca_id]

        status_sync = sync_status_payload()
        globus_ok = bool(status_sync.get("ok"))
        globus_detail = status_sync.get("detail") or ""
        compras_map = compras_por_codigos_local(
            codigos,
            data_ini=date(ano - 5, 1, 1),
            data_fim=date(ano, 12, 31),
            limite_por_peca=5,
        )

        results = []
        for g in garantias:
            codigo = g.peca.codigo_interno
            compras = compras_map.get(codigo, [])
            if not compras:
                for k, v in compras_map.items():
                    if k.lower() == codigo.lower():
                        compras = v
                        break
            ultima = compras[0] if compras else None
            results.append(
                {
                    "id": g.id,
                    "protocolo": g.protocolo,
                    "peca_codigo": codigo,
                    "peca_nome": f"{codigo} - {g.peca.descricao}",
                    "veiculo_codigo": g.veiculo.codigo,
                    "fornecedor_nome": str(g.fornecedor),
                    "valor_peca": str(g.valor_peca) if g.valor_peca is not None else None,
                    "motivo_improcedente": g.motivo_improcedente or "",
                    "criado_em": g.criado_em.isoformat(),
                    "nf_compra_rg": g.nota_compra.numero if g.nota_compra_id else "",
                    "compras_globus": compras,
                    "ultima_compra_globus": ultima,
                }
            )

        return Response(
            {
                "ano": ano,
                "count": len(results),
                "results": results,
                "globus_ok": globus_ok,
                "globus_detail": globus_detail,
                "readonly": True,
                "aviso": (
                    "Improcedente vem do RastroGlobus. Compras vêm do espelho local "
                    "(sync_globus). Estoque continua no Globo."
                ),
            }
        )


class GlobusLocalPecasView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .models import PecaGlobus

        q = request.query_params.get("q", "").strip()
        if len(q) < 2:
            return Response(
                {"detail": "Informe ao menos 2 caracteres."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs = PecaGlobus.objects.filter(
            Q(codigo_interno__icontains=q) | Q(descricao__icontains=q)
        ).order_by("codigo_interno")[:30]
        rows = [
            {
                "codigo_interno": p.codigo_interno,
                "descricao": p.descricao,
                "codigo_mat_int": p.codigo_mat_int,
                "codigo_grupo": p.codigo_grupo,
            }
            for p in qs
        ]
        return Response({"count": len(rows), "results": rows, "source": "local"})


class GlobusLocalVeiculosView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .models import VeiculoGlobus

        q = request.query_params.get("q", "").strip()
        if len(q) < 2:
            return Response(
                {"detail": "Informe ao menos 2 caracteres."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs = VeiculoGlobus.objects.filter(
            Q(prefixo__icontains=q) | Q(placa__icontains=q) | Q(codigo_veic_globus__icontains=q)
        ).order_by("prefixo")[:30]
        rows = [
            {
                "codigo": v.prefixo or v.codigo_veic_globus,
                "placa": v.placa,
                "codigo_veic_globus": v.codigo_veic_globus,
                "codigo_empresa": v.codigo_empresa,
                "condicao": v.condicao,
            }
            for v in qs
        ]
        return Response({"count": len(rows), "results": rows, "source": "local"})
