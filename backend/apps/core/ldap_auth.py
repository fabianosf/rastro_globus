"""Hooks LDAP (django-auth-ldap). Não altera o Samba — só popula o Usuario local."""

from __future__ import annotations

import logging

from django.conf import settings

logger = logging.getLogger("sggi.auth")

_signals_connected = False


def ldap_enabled() -> bool:
    return bool(getattr(settings, "AD_LDAP_ENABLED", False))


def connect_ldap_signals() -> None:
    global _signals_connected
    if _signals_connected or not ldap_enabled():
        return
    try:
        from django_auth_ldap.backend import populate_user
    except ImportError:
        logger.warning("django-auth-ldap não instalado; sinais LDAP ignorados.")
        return

    from django.dispatch import receiver

    from .models import Usuario

    @receiver(populate_user, weak=False)
    def _on_populate_user(sender, user, ldap_user, **kwargs):  # noqa: ARG001
        user.set_unusable_password()
        # Novo espelho local: menor privilégio até admin ajustar o perfil.
        if user._state.adding:
            user.perfil = Usuario.Perfil.DIRECAO
        logger.info(
            "ldap_populate username=%s creating=%s",
            getattr(user, "username", ""),
            user._state.adding,
        )

    _signals_connected = True


def configure_ldap_settings() -> dict:
    """
    Monta configuração AUTH_LDAP_* a partir do ambiente.
    Retorna kwargs para aplicar em django.conf.settings (módulo settings.py).
    """
    import os

    enabled = (os.environ.get("AD_LDAP_ENABLED") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    out: dict = {"AD_LDAP_ENABLED": enabled}
    if not enabled:
        return out

    import ldap
    from django_auth_ldap.config import LDAPSearch

    uri = (os.environ.get("AD_LDAP_URI") or "").strip()
    failover = (os.environ.get("AD_LDAP_URI_FAILOVER") or "").strip()
    # django-auth-ldap usa um URI; failover fica documentado / troca manual no .env
    if not uri and failover:
        uri = failover

    base_dn = (os.environ.get("AD_LDAP_BASE_DN") or "DC=grbf,DC=dom").strip()
    bind_dn = (os.environ.get("AD_LDAP_BIND_DN") or "").strip()
    bind_password = os.environ.get("AD_LDAP_BIND_PASSWORD") or ""
    user_filter = (
        os.environ.get("AD_LDAP_USER_FILTER") or "(sAMAccountName=%(user)s)"
    ).strip()
    ca_path = (os.environ.get("AD_LDAP_CA_CERT_PATH") or "/certs/ucs-ca.crt").strip()
    require_cert = (os.environ.get("AD_LDAP_REQUIRE_CERT") or "demand").strip().lower()

    tls_req = {
        "demand": ldap.OPT_X_TLS_DEMAND,
        "allow": ldap.OPT_X_TLS_ALLOW,
        "never": ldap.OPT_X_TLS_NEVER,
        "try": ldap.OPT_X_TLS_TRY,
    }.get(require_cert, ldap.OPT_X_TLS_DEMAND)

    out.update(
        {
            "AUTHENTICATION_BACKENDS": (
                "django_auth_ldap.backend.LDAPBackend",
                "django.contrib.auth.backends.ModelBackend",
            ),
            "AUTH_LDAP_SERVER_URI": uri,
            "AUTH_LDAP_BIND_DN": bind_dn,
            "AUTH_LDAP_BIND_PASSWORD": bind_password,
            "AUTH_LDAP_USER_SEARCH": LDAPSearch(
                base_dn,
                ldap.SCOPE_SUBTREE,
                user_filter,
            ),
            "AUTH_LDAP_USER_ATTR_MAP": {
                "first_name": "givenName",
                "last_name": "sn",
                "email": "mail",
            },
            "AUTH_LDAP_ALWAYS_UPDATE_USER": True,
            "AUTH_LDAP_CONNECTION_OPTIONS": {
                ldap.OPT_REFERRALS: 0,
                ldap.OPT_NETWORK_TIMEOUT: 10,
                ldap.OPT_X_TLS_REQUIRE_CERT: tls_req,
                ldap.OPT_X_TLS_CACERTFILE: ca_path,
                # Necessário em vários OpenLDAP para aplicar CACERTFILE.
                ldap.OPT_X_TLS_NEWCTX: 0,
            },
        }
    )
    return out
