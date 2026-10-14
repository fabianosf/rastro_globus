"""Decodificação da chave de acesso NFe (44 dígitos) — sem consulta SEFAZ."""

from __future__ import annotations

import re
from typing import Any


class ChaveNfeError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _apenas_digitos(valor: str) -> str:
    return re.sub(r"\D", "", valor or "")


def calcular_dv_chave(chave43: str) -> str:
    """Dígito verificador módulo 11 (posições 1–43 da chave)."""
    digits = _apenas_digitos(chave43)
    if len(digits) != 43:
        raise ChaveNfeError("Chave incompleta para calcular o dígito verificador.")
    pesos = (2, 3, 4, 5, 6, 7, 8, 9)
    soma = 0
    peso_i = 0
    for ch in reversed(digits):
        soma += int(ch) * pesos[peso_i]
        peso_i = (peso_i + 1) % 8
    resto = soma % 11
    dv = 0 if resto in (0, 1) else 11 - resto
    return str(dv)


def validar_chave_nfe(chave: str) -> str:
    digits = _apenas_digitos(chave)
    if len(digits) != 44:
        raise ChaveNfeError("A chave NFe deve ter exatamente 44 dígitos.")
    esperado = calcular_dv_chave(digits[:43])
    if digits[43] != esperado:
        raise ChaveNfeError("Dígito verificador da chave NFe inválido.")
    return digits


def decodificar_chave_nfe(chave: str) -> dict[str, Any]:
    """
    Extrai campos embutidos na chave de acesso.

    Layout: cUF(2) + AAMM(4) + CNPJ(14) + mod(2) + serie(3) + nNF(9)
            + tpEmis(1) + cNF(8) + cDV(1)
    """
    digits = validar_chave_nfe(chave)
    aamm = digits[2:6]
    ano = 2000 + int(aamm[:2])
    mes = int(aamm[2:4])
    if mes < 1 or mes > 12:
        raise ChaveNfeError("Mês de emissão inválido na chave NFe.")
    serie = str(int(digits[22:25]))  # remove zeros à esquerda
    numero = str(int(digits[25:34]))
    return {
        "chave": digits,
        "uf_codigo": digits[0:2],
        "ano_mes": aamm,
        "nf_remessa_data": f"{ano:04d}-{mes:02d}-01",
        "cnpj_emitente": digits[6:20],
        "modelo": digits[20:22],
        "nf_remessa_serie": serie,
        "nf_remessa_numero": numero,
        "tipo_emissao": digits[34],
        "codigo_numerico": digits[35:43],
        "dv": digits[43],
    }
