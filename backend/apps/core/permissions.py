from rest_framework.permissions import BasePermission, SAFE_METHODS

from .models import Garantia

# Status finais — só manutenção / admin
STATUS_FINAIS = {
    Garantia.Status.PROCEDENTE,
    Garantia.Status.IMPROCEDENTE,
    Garantia.Status.CORTESIA,
}

# Avanço intermediário — compras / manutenção / admin
STATUS_INTERMEDIARIOS = {
    Garantia.Status.ENVIADA,
    Garantia.Status.EM_ANALISE,
    Garantia.Status.CANCELADA,
}


def _perfil(user) -> str | None:
    if not user or not user.is_authenticated:
        return None
    return getattr(user, "perfil", None)


def perfil_pode_criar_garantia(perfil: str | None) -> bool:
    return perfil in {"oficina", "manutencao", "admin"}


def perfil_pode_editar_garantia(perfil: str | None) -> bool:
    return perfil in {"oficina", "compras", "manutencao", "admin"}


def perfil_pode_anexar(perfil: str | None) -> bool:
    return perfil in {"oficina", "compras", "manutencao", "admin"}


def perfil_pode_vincular_nf(perfil: str | None) -> bool:
    return perfil in {"compras", "admin"}


def perfil_pode_status(perfil: str | None, novo_status: str) -> bool:
    if perfil == "admin":
        return True
    if perfil == "direcao" or not perfil:
        return False
    if novo_status in STATUS_FINAIS:
        return perfil == "manutencao"
    if novo_status in STATUS_INTERMEDIARIOS:
        return perfil in {"compras", "manutencao"}
    return False


class IsNotDirecaoWrite(BasePermission):
    """Direção: somente leitura em cadastros e escritas genéricas."""

    message = "Perfil Direção possui somente leitura."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return _perfil(request.user) != "direcao"


class CanCreateGarantia(BasePermission):
    message = "Seu perfil não pode criar garantias (permitido: oficina, manutenção, admin)."

    def has_permission(self, request, view):
        return perfil_pode_criar_garantia(_perfil(request.user))


class CanEditGarantia(BasePermission):
    message = "Seu perfil não pode editar garantias."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return perfil_pode_editar_garantia(_perfil(request.user))


class CanAnexar(BasePermission):
    message = "Seu perfil não pode anexar arquivos."

    def has_permission(self, request, view):
        return perfil_pode_anexar(_perfil(request.user))


class CanVincularNota(BasePermission):
    message = "Seu perfil não pode vincular NFs (permitido: compras, admin)."

    def has_permission(self, request, view):
        return perfil_pode_vincular_nf(_perfil(request.user))


class CanChangeStatus(BasePermission):
    """
    Oficina não altera status.
    Compras/manutenção avançam intermediários; só manutenção fecha finais.
    Admin: tudo. Direção: nada.
    """

    message = "Seu perfil não pode alterar o status desta garantia."

    def has_permission(self, request, view):
        perfil = _perfil(request.user)
        if not perfil or perfil == "direcao":
            return False
        if perfil == "admin":
            return True
        # Validação fina com o body ocorre em has_permission após parse;
        # aqui liberamos quem pode POST /status/ e validamos o alvo no service.
        return perfil in {"compras", "manutencao"}
