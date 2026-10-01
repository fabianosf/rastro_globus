from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    AlertaReincidenciaViewSet,
    DashboardView,
    ExportCsvView,
    FornecedorViewSet,
    GarantiaViewSet,
    GlobusComprasView,
    GlobusLocalPecasView,
    GlobusLocalVeiculosView,
    GlobusMovimentosView,
    GlobusNfView,
    GlobusNfsGarantiaView,
    GlobusPecasView,
    GlobusStatusView,
    GlobusVeiculosView,
    ImprocedentesComprasView,
    LoginView,
    MeView,
    NotaFiscalViewSet,
    PecaViewSet,
    RankingPecasView,
    RankingVeiculosView,
    RegraPrazoGarantiaViewSet,
    RelatorioHistoricoView,
    RelatorioResumoView,
    VeiculoViewSet,
)

router = DefaultRouter()
router.register("fornecedores", FornecedorViewSet, basename="fornecedores")
router.register("veiculos", VeiculoViewSet, basename="veiculos")
router.register("pecas", PecaViewSet, basename="pecas")
router.register("notas", NotaFiscalViewSet, basename="notas")
router.register("garantias", GarantiaViewSet, basename="garantias")
router.register("regras-prazo", RegraPrazoGarantiaViewSet, basename="regras-prazo")
router.register("alertas-reincidencia", AlertaReincidenciaViewSet, basename="alertas-reincidencia")

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("relatorios/resumo/", RelatorioResumoView.as_view(), name="relatorios-resumo"),
    path("relatorios/ranking-pecas/", RankingPecasView.as_view(), name="relatorios-ranking-pecas"),
    path("relatorios/ranking-veiculos/", RankingVeiculosView.as_view(), name="relatorios-ranking-veiculos"),
    path("relatorios/export.csv/", ExportCsvView.as_view(), name="relatorios-export"),
    path(
        "relatorios/improcedentes-compras/",
        ImprocedentesComprasView.as_view(),
        name="relatorios-improcedentes-compras",
    ),
    path(
        "relatorios/historico/",
        RelatorioHistoricoView.as_view(),
        name="relatorios-historico",
    ),
    path("globus/status/", GlobusStatusView.as_view(), name="globus-status"),
    path("globus/nf/", GlobusNfView.as_view(), name="globus-nf"),
    path("globus/nfs-garantia/", GlobusNfsGarantiaView.as_view(), name="globus-nfs-garantia"),
    path("globus/veiculos/", GlobusVeiculosView.as_view(), name="globus-veiculos"),
    path("globus/pecas/", GlobusPecasView.as_view(), name="globus-pecas"),
    path("globus/local/pecas/", GlobusLocalPecasView.as_view(), name="globus-local-pecas"),
    path(
        "globus/local/veiculos/",
        GlobusLocalVeiculosView.as_view(),
        name="globus-local-veiculos",
    ),
    path("globus/movimentos/", GlobusMovimentosView.as_view(), name="globus-movimentos"),
    path("globus/compras/", GlobusComprasView.as_view(), name="globus-compras"),
    path("", include(router.urls)),
]
