"""Extração de campos de DANFE (foto) via OpenAI Vision — sem persistir a imagem."""

from __future__ import annotations

import base64
import json
import re
from typing import Any

from django.conf import settings

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": "jpeg",
    "image/jpg": "jpeg",
    "image/png": "png",
    "image/webp": "webp",
}
MAX_BYTES = 8 * 1024 * 1024

EXTRACT_PROMPT = """Você lê uma foto de DANFE (Nota Fiscal Eletrônica) brasileira de remessa em garantia.
Extraia os campos abaixo. Responda APENAS um JSON válido (sem markdown) com estas chaves:

{
  "nf_remessa_numero": "número da NF emitida (ex: 7427)",
  "nf_remessa_serie": "série (ex: 1)",
  "nf_remessa_data": "data de emissão YYYY-MM-DD",
  "chave_nfe": "chave de acesso com 44 dígitos ou vazio",
  "valor_peca": "valor total/produto como número decimal string (ex: 500.00) ou vazio",
  "peca_codigo": "código do produto/serviço (ex: 03120026)",
  "peca_descricao": "descrição do produto",
  "veiculo_codigo": "código do CARRO / veículo nas infos complementares (ex: 30059)",
  "fornecedor_nome": "nome do DESTINATÁRIO (fornecedor que recebe a remessa)",
  "nf_origem_numero": "NF de origem/compra citada nas informações complementares (ex: 39511)",
  "nf_origem_data": "data da NF origem YYYY-MM-DD se aparecer, senão vazio",
  "defeito": "texto do DEFEITO nas infos complementares",
  "avisos": ["lista de campos incertos ou ilegíveis"]
}

Regras:
- Se um campo não for legível, use string vazia e mencione em avisos.
- Prefira dígitos da chave de acesso (44) se visível.
- Datas no formato ISO YYYY-MM-DD (converte de DD/MM/AAAA se necessário).
- Não invente números de NF ou códigos.
"""


class DanfeOcrError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


def _normalize_date(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return raw
    m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", raw)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    m = re.fullmatch(r"(\d{2})-(\d{2})-(\d{4})", raw)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return raw


def _clean_payload(data: dict[str, Any]) -> dict[str, Any]:
    def s(key: str) -> str:
        v = data.get(key, "")
        if v is None:
            return ""
        return str(v).strip()

    chave = re.sub(r"\D", "", s("chave_nfe"))
    if len(chave) != 44:
        chave = chave if chave else ""

    avisos = data.get("avisos") or []
    if not isinstance(avisos, list):
        avisos = [str(avisos)]
    avisos = [str(a).strip() for a in avisos if str(a).strip()]

    return {
        "nf_remessa_numero": s("nf_remessa_numero"),
        "nf_remessa_serie": s("nf_remessa_serie") or "1",
        "nf_remessa_data": _normalize_date(s("nf_remessa_data")),
        "chave_nfe": chave,
        "valor_peca": s("valor_peca").replace(",", "."),
        "peca_codigo": s("peca_codigo"),
        "peca_descricao": s("peca_descricao"),
        "veiculo_codigo": s("veiculo_codigo"),
        "fornecedor_nome": s("fornecedor_nome"),
        "nf_origem_numero": s("nf_origem_numero"),
        "nf_origem_data": _normalize_date(s("nf_origem_data")),
        "defeito": s("defeito"),
        "avisos": avisos,
    }


def extrair_danfe_da_imagem(file_obj, content_type: str | None = None) -> dict[str, Any]:
    api_key = (getattr(settings, "OPENAI_API_KEY", None) or "").strip()
    if not api_key:
        raise DanfeOcrError(
            "OCR não configurado. Defina OPENAI_API_KEY no ambiente do backend.",
            status=503,
        )

    ctype = (content_type or getattr(file_obj, "content_type", "") or "").lower().split(";")[0].strip()
    if ctype not in ALLOWED_CONTENT_TYPES:
        # fallback by name
        name = (getattr(file_obj, "name", "") or "").lower()
        if name.endswith((".jpg", ".jpeg")):
            ctype = "image/jpeg"
        elif name.endswith(".png"):
            ctype = "image/png"
        elif name.endswith(".webp"):
            ctype = "image/webp"
        else:
            raise DanfeOcrError("Envie imagem JPEG, PNG ou WebP.")

    raw = file_obj.read()
    if hasattr(file_obj, "seek"):
        try:
            file_obj.seek(0)
        except Exception:
            pass
    if not raw:
        raise DanfeOcrError("Arquivo de imagem vazio.")
    if len(raw) > MAX_BYTES:
        raise DanfeOcrError("Imagem maior que 8 MB. Reduza a foto e tente de novo.")

    mime = ctype if ctype in ALLOWED_CONTENT_TYPES else "image/jpeg"
    b64 = base64.b64encode(raw).decode("ascii")
    model = (getattr(settings, "OPENAI_VISION_MODEL", None) or "gpt-4o-mini").strip()

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise DanfeOcrError(
            "Pacote openai não instalado no servidor. Rode: pip install openai",
            status=503,
        ) from exc

    client = OpenAI(api_key=api_key)
    try:
        completion = client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": EXTRACT_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{b64}"},
                        },
                    ],
                }
            ],
            temperature=0,
            max_tokens=1200,
        )
    except Exception as exc:
        raise DanfeOcrError(f"Falha na leitura da DANFE: {exc}", status=502) from exc

    text = (completion.choices[0].message.content or "").strip()
    if not text:
        raise DanfeOcrError("Modelo não retornou dados da DANFE.", status=502)

    # Remove fences if model ignores json_object sometimes
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise DanfeOcrError("Resposta do OCR inválida (JSON).", status=502) from exc

    if not isinstance(parsed, dict):
        raise DanfeOcrError("Resposta do OCR inválida.", status=502)

    return _clean_payload(parsed)
