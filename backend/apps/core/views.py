import csv
import hashlib
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib.auth import authenticate
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

logger = logging.getLogger("sggi.auth")

from .models import (
    AlertaReincidencia,
    Anexo,
    Fornecedor,
    Garantia,
    HistoricoGarantiaMensal,
    NotaFiscal,
    Peca,
    RegraPrazoGarantia,
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
from .prazo_garantia import (
    calcular_data_fim_garantia,
    ensure_regra_padrao_externo,
    resolver_prazo_dias,
)
from .reincidencia import contagem_alertas_novos
from .serializers import (
    AlertaReincidenciaSerializer,
    AnexoSerializer,
    FornecedorSerializer,
    GarantiaCreateSerializer,
    GarantiaDetailSerializer,
    GarantiaListSerializer,
    GarantiaUpdateSerializer,
    STATUS_PODE_EDITAR_DANFE,
    NotaFiscalSerializer,
    PecaSerializer,
    RegraPrazoGarantiaSerializer,
    StatusChangeSerializer,
    UsuarioSerializer,
    VeiculoSerializer,
    VincularNotaSerializer,
)
from .services import mudar_status, proximo_protocolo


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = (request.data.get("username") or "").strip()
        password = request.data.get("password") or ""
        if not username or not password:
            return Response(
                {"detail": "Usuário ou senha inválidos."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Com AD_LDAP_ENABLED=1: LDAPBackend + ModelBackend (admin local de emergência).
        # Com flag off: só ModelBackend (senha local MariaDB).
        user = authenticate(request, username=username, password=password)
        if user is None:
            logger.info("login_failed username=%s", username)
            return Response(
                {"detail": "Usuário ou senha inválidos."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if not user.is_active:
            logger.info("login_inactive username=%s", username)
            return Response(
                {"detail": "Usuário inativo."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        refresh = RefreshToken.for_user(user)
        logger.info("login_ok username=%s perfil=%s", username, getattr(user, "perfil", ""))
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


class RegraPrazoGarantiaViewSet(viewsets.ModelViewSet):
    queryset = RegraPrazoGarantia.objects.all().order_by("escopo", "valor_escopo")
    serializer_class = RegraPrazoGarantiaSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        return [IsAuthenticated()]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            perfil = getattr(request.user, "perfil", None)
            if perfil not in {"admin", "manutencao"}:
                from rest_framework.exceptions import PermissionDenied

                raise PermissionDenied("Somente admin/manutencao gerenciam regras de prazo.")

    def list(self, request, *args, **kwargs):
        ensure_regra_padrao_externo()
        return super().list(request, *args, **kwargs)


class AlertaReincidenciaViewSet(viewsets.ModelViewSet):
    queryset = AlertaReincidencia.objects.all()
    serializer_class = AlertaReincidenciaSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = AlertaReincidencia.objects.all()
        status_f = (self.request.query_params.get("status") or "").strip()
        peca = (self.request.query_params.get("peca") or "").strip()
        fornecedor = (self.request.query_params.get("fornecedor") or "").strip()
        empresa = (self.request.query_params.get("empresa") or "").strip()
        if status_f:
            qs = qs.filter(status=status_f)
        if peca:
            qs = qs.filter(Q(peca_codigo__icontains=peca) | Q(peca_descricao__icontains=peca))
        if fornecedor:
            qs = qs.filter(fornecedor_1__icontains=fornecedor)
        if empresa:
            qs = qs.filter(empresa__icontains=empresa)
        return qs

    @action(detail=False, methods=["get"], url_path="novos-count")
    def novos_count(self, request):
        return Response({"count": contagem_alertas_novos()})

    @action(detail=True, methods=["post"], url_path="descartar")
    def descartar(self, request, pk=None):
        alerta = self.get_object()
        motivo = str(request.data.get("motivo_descarte") or "").strip()
        if not motivo:
            return Response(
                {"detail": "Informe motivo_descarte."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        alerta.status = AlertaReincidencia.Status.DESCARTADO
        alerta.motivo_descarte = motivo
        alerta.save(update_fields=["status", "motivo_descarte", "atualizado_em"])
        return Response(AlertaReincidenciaSerializer(alerta).data)

    @action(detail=True, methods=["post"], url_path="abrir-garantia")
    def abrir_garantia(self, request, pk=None):
        alerta = self.get_object()
        if alerta.status == AlertaReincidencia.Status.DESCARTADO:
            return Response(
                {"detail": "Alerta descartado nao pode abrir garantia."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not CanCreateGarantia().has_permission(request, self):
            return Response(
                {"detail": "Seu perfil nao pode criar garantias."},
                status=status.HTTP_403_FORBIDDEN,
            )

        peca, _ = Peca.objects.get_or_create(
            codigo_interno=alerta.peca_codigo,
            defaults={
                "descricao": (alerta.peca_descricao or alerta.peca_codigo)[:255],
                "garantia_dias": 180,
                "ativo": True,
            },
        )
        veiculo, _ = Veiculo.objects.get_or_create(
            codigo=alerta.veiculo_codigo,
            defaults={"casa": alerta.empresa or "", "ativo": True},
        )
        forn_nome = (alerta.fornecedor_1 or "Fornecedor reincidencia").strip()
        forn = Fornecedor.objects.filter(
            Q(nome_fantasia__iexact=forn_nome) | Q(razao_social__iexact=forn_nome)
        ).first()
        if not forn:
            digest = hashlib.sha1(forn_nome.encode("utf-8")).hexdigest()[:12]
            forn = Fornecedor.objects.create(
                razao_social=forn_nome,
                nome_fantasia=forn_nome,
                cnpj=f"AR-{digest}"[:18],
                origem="alerta",
            )

        ensure_regra_padrao_externo()
        data_aplicacao = alerta.data_2
        prazo = resolver_prazo_dias(peca=peca, fornecedor=forn)
        garantia = Garantia.objects.create(
            protocolo=proximo_protocolo(),
            peca=peca,
            veiculo=veiculo,
            fornecedor=forn,
            status=Garantia.Status.ABERTA,
            nf_venda_fornecedor=alerta.nf_1 or "SEM-NF",
            nf_venda_data=alerta.data_1,
            data_aplicacao=data_aplicacao,
            prazo_garantia_dias=prazo,
            data_fim_garantia=calcular_data_fim_garantia(data_aplicacao, prazo),
            valor_peca=alerta.valor_estimado,
            alerta_origem=alerta,
            criado_por=request.user,
            observacoes=(
                f"Aberta a partir de alerta de reincidencia "
                f"(saidas {alerta.data_1} e {alerta.data_2}, {alerta.dias_entre} dias)."
            ),
            laudo_resumo="Laudo pendente — origem alerta de reincidencia.",
        )
        from .models import EventoGarantia

        EventoGarantia.objects.create(
            garantia=garantia,
            usuario=request.user,
            status_anterior="",
            status_novo=Garantia.Status.ABERTA,
            descricao="Garantia aberta a partir de AlertaReincidencia.",
        )
        alerta.status = AlertaReincidencia.Status.GARANTIA_ABERTA
        alerta.save(update_fields=["status", "atualizado_em"])
        return Response(
            GarantiaDetailSerializer(garantia, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class GarantiaViewSet(viewsets.ModelViewSet):
    queryset = Garantia.objects.select_related(
        "peca", "veiculo", "fornecedor", "nota_remessa", "nota_retorno", "nota_compra", "criado_por"
    ).prefetch_related("eventos", "anexos")
    permission_classes = [IsAuthenticated]
    # DELETE permitido só para status abertos (correção de cadastro).
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_permissions(self):
        if self.action in ("create", "extrair_danfe"):
            return [IsAuthenticated(), CanCreateGarantia()]
        if self.action in ("partial_update", "update", "destroy"):
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
        if self.action in ("partial_update", "update"):
            return GarantiaUpdateSerializer
        if self.action == "retrieve":
            return GarantiaDetailSerializer
        return GarantiaListSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        instance = self.get_object()
        return Response(GarantiaDetailSerializer(instance, context={"request": request}).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        perfil = getattr(request.user, "perfil", None)
        if instance.status not in STATUS_PODE_EDITAR_DANFE and perfil != "admin":
            return Response(
                {
                    "detail": (
                        "Só é possível excluir garantias abertas, enviadas ou em análise. "
                        "Admin pode excluir casos fechados (limpeza / teste)."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        nota_ids = [
            nid
            for nid in (
                instance.nota_remessa_id,
                instance.nota_compra_id,
                instance.nota_retorno_id,
            )
            if nid
        ]
        instance.delete()
        for nid in nota_ids:
            ainda_usada = Garantia.objects.filter(
                Q(nota_remessa_id=nid) | Q(nota_compra_id=nid) | Q(nota_retorno_id=nid)
            ).exists()
            if not ainda_usada:
                NotaFiscal.objects.filter(pk=nid).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        if status_f := (params.get("status") or "").strip():
            if status_f == "abertos":
                qs = qs.filter(
                    status__in=[
                        Garantia.Status.ABERTA,
                        Garantia.Status.ENVIADA,
                        Garantia.Status.EM_ANALISE,
                    ]
                )
            elif "," in status_f:
                qs = qs.filter(status__in=[s.strip() for s in status_f.split(",") if s.strip()])
            else:
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
                | Q(nota_remessa__numero__icontains=q)
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

        status_sync = sync_status_payload(ping_oracle=False)
        globus_ok = bool(status_sync.get("ok"))
        globus_detail = status_sync.get("detail") or ""
        compras_map: dict = {}
        codigos = [row.get("peca_codigo") for row in data if row.get("peca_codigo")]
        if codigos:
            compras_map = compras_por_codigos_local(
                codigos,
                data_ini=date.today() - timedelta(days=730),
                data_fim=date.today(),
                limite_por_peca=1,
            )

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

    @action(detail=False, methods=["post"], url_path="extrair-danfe")
    def extrair_danfe(self, request):
        """Lê foto de DANFE (OpenAI Vision) e devolve campos tipados — não grava garantia."""
        from .danfe_ocr import DanfeOcrError, extrair_danfe_da_imagem

        imagem = request.FILES.get("imagem") or request.FILES.get("arquivo")
        if not imagem:
            return Response(
                {"detail": "Envie a foto da DANFE no campo 'imagem'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            dados = extrair_danfe_da_imagem(imagem, content_type=getattr(imagem, "content_type", None))
        except DanfeOcrError as exc:
            return Response({"detail": exc.message}, status=exc.status)
        return Response(dados)

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
                causa_improcedente=data.get("causa_improcedente", ""),
                responsavel_tipo=data.get("responsavel_tipo", ""),
                responsavel_nome=data.get("responsavel_nome", ""),
                cobranca_interna=data.get("cobranca_interna", False),
                observacao_cobranca=data.get("observacao_cobranca", ""),
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

    improcedentes = qs.filter(status=Garantia.Status.IMPROCEDENTE)
    custo_por_causa = [
        {
            "causa": r["causa_improcedente"] or "nao_informada",
            "total": r["total"],
            "valor": str(r["valor"] or 0),
        }
        for r in improcedentes.values("causa_improcedente")
        .annotate(total=Count("id"), valor=Sum("valor_peca"))
        .order_by("-valor")
    ]
    custo_por_responsavel = [
        {
            "responsavel_tipo": r["responsavel_tipo"] or "nao_informado",
            "total": r["total"],
            "valor": str(r["valor"] or 0),
        }
        for r in improcedentes.values("responsavel_tipo")
        .annotate(total=Count("id"), valor=Sum("valor_peca"))
        .order_by("-valor")
    ]
    custo_por_veiculo = [
        {
            "veiculo": r["veiculo__codigo"],
            "total": r["total"],
            "valor": str(r["valor"] or 0),
        }
        for r in improcedentes.values("veiculo__codigo")
        .annotate(total=Count("id"), valor=Sum("valor_peca"))
        .order_by("-valor")[:10]
    ]
    top_pecas_improcedentes = [
        {
            "codigo": r["peca__codigo_interno"],
            "descricao": r["peca__descricao"],
            "causa": r["causa_improcedente"] or "nao_informada",
            "total": r["total"],
            "valor": str(r["valor"] or 0),
        }
        for r in improcedentes.values(
            "peca__codigo_interno", "peca__descricao", "causa_improcedente"
        )
        .annotate(total=Count("id"), valor=Sum("valor_peca"))
        .order_by("-total")[:10]
    ]
    valor_recuperado = qs.filter(
        status=Garantia.Status.PROCEDENTE, alerta_origem__isnull=False
    ).aggregate(t=Sum("valor_peca"))["t"] or Decimal("0")

    agora = timezone.now()
    alertas_qs = AlertaReincidencia.objects.filter(
        status=AlertaReincidencia.Status.NOVO,
        criado_em__year=ano,
    )
    if ano == agora.year:
        alertas_qs = alertas_qs.filter(criado_em__month=agora.month)
    alertas_novos_mes = alertas_qs.count()

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
        "custo_improcedente_por_causa": custo_por_causa,
        "custo_improcedente_por_responsavel": custo_por_responsavel,
        "custo_improcedente_por_veiculo": custo_por_veiculo,
        "top_pecas_improcedentes": top_pecas_improcedentes,
        "valor_recuperado_alertas": str(valor_recuperado),
        "alertas_novos_mes": alertas_novos_mes,
        "alertas_novos_total": contagem_alertas_novos(),
    }


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ano = int(request.query_params.get("ano", timezone.now().year))
        payload = _dashboard_payload(ano)

        # Sem ping/consultas Oracle no caminho crítico — badge usa /api/globus/status/ (espelho).
        from .globus_sync import sync_status_payload

        status_sync = sync_status_payload(ping_oracle=False)
        payload["globus"] = {
            "ok": bool(status_sync.get("ok")),
            "detail": status_sync.get("detail") or "",
            "movimentos_recentes": [],
            "compras_recentes": [],
            "readonly": True,
            "aviso": (
                "KPIs do MariaDB. Status Globus via espelho/sync (sem consulta Oracle nesta tela)."
            ),
            "atualizado_em": status_sync.get("atualizado_em"),
            "stale": status_sync.get("stale"),
            "em_andamento": status_sync.get("em_andamento"),
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


def _parse_day_param(value: str) -> date | None:
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _garantias_periodo(request, *, default_status: str | None = None) -> tuple:
    """Retorna (queryset, meta) filtrado por data_ini/data_fim ou ano (+ status opcional)."""
    params = request.query_params
    data_ini = (params.get("data_ini") or "").strip()
    data_fim = (params.get("data_fim") or "").strip()
    qs = Garantia.objects.select_related("peca", "veiculo", "fornecedor")
    meta: dict = {}

    if data_ini or data_fim:
        if data_ini:
            d0 = _parse_day_param(data_ini)
            if d0:
                qs = qs.filter(criado_em__date__gte=d0)
                meta["data_ini"] = d0.isoformat()
        if data_fim:
            d1 = _parse_day_param(data_fim)
            if d1:
                qs = qs.filter(criado_em__date__lte=d1)
                meta["data_fim"] = d1.isoformat()
        meta["modo"] = "periodo"
    else:
        ano = int(params.get("ano", timezone.now().year))
        qs = qs.filter(criado_em__year=ano)
        meta["ano"] = ano
        meta["modo"] = "ano"

    if "status" in params:
        status_f = (params.get("status") or "").strip()
    elif default_status is not None:
        status_f = default_status
    else:
        status_f = ""

    if status_f and status_f not in {"todos", "all"}:
        if status_f == "abertos":
            qs = qs.filter(
                status__in=[
                    Garantia.Status.ABERTA,
                    Garantia.Status.ENVIADA,
                    Garantia.Status.EM_ANALISE,
                ]
            )
        else:
            qs = qs.filter(status=status_f)
        meta["status"] = status_f
    else:
        meta["status"] = "todos"

    try:
        limite = max(1, min(50, int(params.get("limite", 15))))
    except (TypeError, ValueError):
        limite = 15
    meta["limite"] = limite
    return qs, meta


class RelatorioRankingsView(APIView):
    """Top CARROs e top peças cadastradas no RG (MariaDB)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Default: só abertos (alinha com Minhas NFs; esconde improcedentes antigos).
        qs, meta = _garantias_periodo(request, default_status="abertos")
        limite = meta["limite"]

        total = qs.count()
        valor_total = qs.aggregate(t=Sum("valor_peca"))["t"] or Decimal("0")
        abertos_set = {
            Garantia.Status.ABERTA,
            Garantia.Status.ENVIADA,
            Garantia.Status.EM_ANALISE,
        }
        abertos = qs.filter(status__in=abertos_set).count()
        enviada = qs.filter(status=Garantia.Status.ENVIADA).count()

        por_status = [
            {"status": row["status"], "total": row["total"]}
            for row in qs.values("status").annotate(total=Count("id")).order_by("-total")
        ]

        pecas = [
            {
                "peca_id": r["peca_id"],
                "codigo": r["peca__codigo_interno"],
                "descricao": r["peca__descricao"],
                "total": r["total"],
                "valor": str(r["valor"] or 0),
            }
            for r in qs.values("peca_id", "peca__codigo_interno", "peca__descricao")
            .annotate(total=Count("id"), valor=Sum("valor_peca"))
            .order_by("-total")[:limite]
        ]

        veiculos = [
            {
                "veiculo_id": r["veiculo_id"],
                "codigo": r["veiculo__codigo"],
                "casa": r["veiculo__casa"] or "",
                "total": r["total"],
                "valor": str(r["valor"] or 0),
            }
            for r in qs.values("veiculo_id", "veiculo__codigo", "veiculo__casa")
            .annotate(total=Count("id"), valor=Sum("valor_peca"))
            .order_by("-total")[:limite]
        ]

        return Response(
            {
                **meta,
                "kpis": {
                    "total": total,
                    "abertos": abertos,
                    "enviada": enviada,
                    "valor_total": str(valor_total),
                },
                "por_status": por_status,
                "pecas": pecas,
                "veiculos": veiculos,
                "total_garantias": total,
            }
        )


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
    """Status do espelho (SyncLog). Default sem ping Oracle; use ?ping=1 para teste ao vivo."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .globus_sync import sync_status_payload

        ping = (request.query_params.get("ping") or "").strip().lower() in {
            "1",
            "true",
            "yes",
        }
        # Sempre 200: ok/stale/falhou vão no body (badge UI).
        return Response(
            sync_status_payload(ping_oracle=ping),
            status=status.HTTP_200_OK,
        )


class GlobusNfView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .globus_oracle import GlobusOracleError
        from .globus_queries import buscar_nfs

        numero = request.query_params.get("numero", "").strip()
        meses_raw = request.query_params.get("meses", "24")
        try:
            meses = int(meses_raw)
        except (TypeError, ValueError):
            meses = 24
        try:
            rows = buscar_nfs(numero, meses=meses)
        except GlobusOracleError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"detail": f"Falha ao consultar NF no Globus: {exc}"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"count": len(rows), "results": rows, "meses": meses})


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
    Cruza garantias improcedentes (SGGI) com compras do espelho CompraGlobus.
    Improcedente NAO vem do Globo — so do SGGI. Oracle fora do ar nao impede.
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

        status_sync = sync_status_payload(ping_oracle=False)
        globus_ok = bool(status_sync.get("ok"))
        globus_detail = status_sync.get("detail") or ""
        compras_map = compras_por_codigos_local(
            codigos,
            data_ini=date.today() - timedelta(days=730),
            data_fim=date.today(),
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
                    "Improcedente vem do SGGI. Compras vêm do espelho local "
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
                # codigo = chave Globus para ensure no RG; prefixo e exibicao
                "codigo": v.codigo_veic_globus or v.prefixo,
                "prefixo": v.prefixo,
                "placa": v.placa,
                "codigo_veic_globus": v.codigo_veic_globus,
                "codigo_empresa": v.codigo_empresa,
                "condicao": v.condicao,
                "descricao": v.prefixo or v.codigo_veic_globus,
            }
            for v in qs
        ]
        return Response({"count": len(rows), "results": rows, "source": "local"})
