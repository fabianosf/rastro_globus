from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.core.models import Usuario


class LoginViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = Usuario.objects.create_user(
            username="localuser",
            password="secret123",
            perfil=Usuario.Perfil.OFICINA,
        )

    def test_login_local_ok(self):
        resp = self.client.post(
            "/api/auth/login/",
            {"username": "localuser", "password": "secret123"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data)
        self.assertEqual(resp.data["user"]["username"], "localuser")
        self.assertEqual(resp.data["user"]["perfil"], "oficina")

    def test_login_invalid(self):
        resp = self.client.post(
            "/api/auth/login/",
            {"username": "localuser", "password": "wrong"},
            format="json",
        )
        self.assertEqual(resp.status_code, 401)

    @override_settings(AD_LDAP_ENABLED=False)
    def test_login_empty_rejected(self):
        resp = self.client.post(
            "/api/auth/login/",
            {"username": "", "password": ""},
            format="json",
        )
        self.assertEqual(resp.status_code, 401)
