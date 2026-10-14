from django.test import TestCase
from rest_framework.test import APIClient

from apps.core.chave_nfe import ChaveNfeError, calcular_dv_chave, decodificar_chave_nfe
from apps.core.models import Usuario


def _chave_exemplo() -> str:
    base = "35" + "2607" + "12345678000199" + "55" + "001" + "000007427" + "1" + "12345678"
    return base + calcular_dv_chave(base)


class ChaveNfeDecodeTests(TestCase):
    def test_decodifica_numero_serie_data(self):
        dados = decodificar_chave_nfe(_chave_exemplo())
        self.assertEqual(dados["nf_remessa_numero"], "7427")
        self.assertEqual(dados["nf_remessa_serie"], "1")
        self.assertEqual(dados["nf_remessa_data"], "2026-07-01")
        self.assertEqual(len(dados["chave"]), 44)

    def test_rejeita_tamanho(self):
        with self.assertRaises(ChaveNfeError):
            decodificar_chave_nfe("123")

    def test_rejeita_dv(self):
        chave = _chave_exemplo()
        ruim = chave[:-1] + ("0" if chave[-1] != "0" else "1")
        with self.assertRaises(ChaveNfeError):
            decodificar_chave_nfe(ruim)


class ConsultarChaveNfeApiTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(
            username="oficina_chave",
            password="x",
            perfil=Usuario.Perfil.OFICINA,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_consulta_decode_mesmo_sem_globus(self):
        resp = self.client.post(
            "/api/garantias/consultar-chave-nfe/",
            {"chave": _chave_exemplo()},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["nf_remessa_numero"], "7427")
        self.assertIn("globus", body)
        self.assertIn("results", body["globus"])

    def test_chave_invalida(self):
        resp = self.client.post(
            "/api/garantias/consultar-chave-nfe/",
            {"chave": "000"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
