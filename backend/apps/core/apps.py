from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    label = "core"
    verbose_name = "SGGI Core"

    def ready(self):
        from .ldap_auth import connect_ldap_signals

        connect_ldap_signals()
