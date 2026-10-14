"""Extração de campos de DANFE (foto) via Vision API — sem persistir a imagem."""

from __future__ import annotations

import base64
import io
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
MAX_SIDE_PX = 1600

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


def _resize_image(raw: bytes, mime: str) -> tuple[bytes, str]:
    """Redimensiona lado máximo ~1600px (Pillow). Se falhar, devolve original."""
    try:
        from PIL import Image, ImageOps
    except ImportError:
        return raw, mime

    try:
        img = Image.open(io.BytesIO(raw))
        img = ImageOps.exif_transpose(img)
        w, h = img.size
        if max(w, h) > MAX_SIDE_PX:
            img.thumbnail((MAX_SIDE_PX, MAX_SIDE_PX), Image.Resampling.LANCZOS)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=85, optimize=True)
        return out.getvalue(), "image/jpeg"
    except Exception:
        return raw, mime


def _extract_json_text(text: str) -> str:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        return text
    # fallback: primeiro objeto JSON no texto
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        return m.group(0)
    return text


def extrair_danfe_da_imagem(file_obj, content_type: str | None = None) -> dict[str, Any]:
    api_key = (getattr(settings, "OPENAI_API_KEY", None) or "").strip()
    if not api_key:
        raise DanfeOcrError(
            "OCR não configurado. Defina OPENAI_API_KEY no ambiente do backend.",
            status=503,
        )

    ctype = (content_type or getattr(file_obj, "content_type", "") or "").lower().split(";")[0].strip()
    if ctype not in ALLOWED_CONTENT_TYPES:
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
    raw, mime = _resize_image(raw, mime)
    b64 = base64.b64encode(raw).decode("ascii")
    model = (getattr(settings, "OPENAI_VISION_MODEL", None) or "gpt-4o-mini").strip()

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise DanfeOcrError(
            "Pacote openai não instalado no servidor. Rode: pip install openai",
            status=503,
        ) from exc

    base_url = (getattr(settings, "OPENAI_BASE_URL", None) or "").strip() or None
    is_deepseek = bool(base_url and "deepseek" in base_url.lower())
    client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)

    create_kwargs: dict[str, Any] = {
        "model": model,
        "messages": [
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
        "temperature": 0,
        "max_tokens": 2000,
    }
    # DeepSeek + vision: response_format json_object tende a esvaziar campos
    if not is_deepseek:
        create_kwargs["response_format"] = {"type": "json_object"}

    try:
        completion = client.chat.completions.create(**create_kwargs)
    except Exception as exc:
        msg = str(exc).strip() or exc.__class__.__name__
        if "connection" in msg.lower() or "connect" in msg.lower():
            alvo = base_url or "https://api.openai.com/v1"
            raise DanfeOcrError(
                f"Falha na leitura da DANFE: sem conexão com {alvo}. "
                "Confira OPENAI_BASE_URL, rede/firewall e a chave do provedor.",
                status=502,
            ) from exc
        raise DanfeOcrError(f"Falha na leitura da DANFE: {msg}", status=502) from exc

    text = _extract_json_text(completion.choices[0].message.content or "")
    if not text:
        raise DanfeOcrError("Modelo não retornou dados da DANFE.", status=502)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise DanfeOcrError("Resposta do OCR inválida (JSON).", status=502) from exc

    if not isinstance(parsed, dict):
        raise DanfeOcrError("Resposta do OCR inválida.", status=502)

    cleaned = _clean_payload(parsed)
    principais = (
        cleaned.get("nf_remessa_numero"),
        cleaned.get("peca_codigo") or cleaned.get("peca_descricao"),
        cleaned.get("veiculo_codigo"),
    )
    if not any(principais):
        raise DanfeOcrError(
            "Não foi possível ler NF, peça ou CARRO na foto. "
            "Tire outra foto mais nítida e bem iluminada (JPEG/PNG).",
            status=422,
        )
    return cleaned
