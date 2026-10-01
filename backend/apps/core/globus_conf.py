"""Carrega credenciais Oracle Globus de conf/ (Fernet).

Padrão corporativo:
  conf/chave.key  — chave Fernet
  conf/erp.dat    — JSON criptografado (fallback erp_BD.dat, erp_Old.dat)

Nunca grava plaintext em disco nem loga senha.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings

ERP_CANDIDATES = ("erp.dat", "erp_BD.dat", "erp_Old.dat")


def resolve_conf_dir() -> Path | None:
    env = (os.environ.get("RASTROGLOBUS_CONF_DIR") or "").strip()
    candidates: list[Path] = []
    if env:
        candidates.append(Path(env))
    # monorepo: backend/ -> ../conf
    base_dir = Path(settings.BASE_DIR)
    candidates.append(base_dir.parent / "conf")
    candidates.append(base_dir / "conf")
    for path in candidates:
        try:
            if path.is_dir() and (path / "chave.key").exists():
                return path.resolve()
        except OSError:
            continue
    return None


@dataclass
class GlobusSettings:
    user: str
    password: str
    dsn: str
    source_file: str
    conf_dir: str
    host: str = ""
    port: str = ""
    service_name: str = ""
    oracle_client_lib_dir: str = ""

    def public_summary(self) -> dict:
        return {
            "configured": True,
            "conf_dir": self.conf_dir,
            "source_file": self.source_file,
            "host_set": bool(self.host),
            "port": self.port or None,
            "service_name_set": bool(self.service_name),
            "user_set": bool(self.user),
            "dsn_set": bool(self.dsn),
            "has_password": bool(self.password),
            "oracle_client_lib_dir_set": bool(self.oracle_client_lib_dir),
        }


def resolve_oracle_client_lib_dir(conf_dir: Path | None = None) -> str:
    """Resolve Instant Client a partir de conf/ (sem hardcode de caminho pessoal no codigo)."""
    base = Path(conf_dir) if conf_dir else resolve_conf_dir()
    if base is None:
        return ""

    # 1) arquivo texto em conf/ (gitignored junto com conf/)
    for name in ("oracle_client_dir.txt", "instantclient_dir.txt"):
        marker = base / name
        if marker.is_file():
            try:
                text = marker.read_text(encoding="utf-8").strip().splitlines()
                if text:
                    candidate = Path(text[0].strip().strip('"').strip("'"))
                    if candidate.is_dir():
                        return str(candidate.resolve())
            except OSError:
                pass

    # 2) pasta local ao lado da conf
    for rel in (
        base / "instantclient",
        base / "oracle" / "instantclient",
        base.parent / "instantclient",
        base.parent / "drivers" / "oracle_win" / "oracle" / "instantclient_21_14",
        base.parent / "drivers" / "oracle_win" / "instantclient_21_14",
    ):
        try:
            if rel.is_dir() and (rel / "oci.dll").exists():
                return str(rel.resolve())
        except OSError:
            continue
    return ""


def _first(data: dict, *keys: str):
    lower = {str(k).lower().strip(): v for k, v in data.items()}
    for key in keys:
        if key.lower() in lower and lower[key.lower()] not in (None, ""):
            return lower[key.lower()]
    return None


def _build_dsn(data: dict) -> tuple[str, str, str, str]:
    explicit = _first(data, "oracle_dsn", "dsn", "tns_name", "connect_string")
    host = str(_first(data, "servidor", "server", "host", "hostname") or "").strip()
    port = str(_first(data, "porta", "port") or "1521").strip() or "1521"
    service = str(
        _first(
            data,
            "bd",
            "service name",
            "service_name",
            "servicename",
            "service",
            "servico",
            "sid",
        )
        or ""
    ).strip()
    if explicit:
        return str(explicit).strip(), host, port, service
    if host and service:
        return f"{host}:{port}/{service}", host, port, service
    return host, host, port, service


def load_globus_settings(conf_dir: Path | None = None) -> GlobusSettings | None:
    base = Path(conf_dir) if conf_dir else resolve_conf_dir()
    if base is None:
        return None
    key_path = base / "chave.key"
    if not key_path.exists():
        return None

    try:
        from cryptography.fernet import Fernet, InvalidToken
    except ImportError as exc:
        raise RuntimeError(
            "Instale cryptography para ler conf/ (pip install cryptography)."
        ) from exc

    key = key_path.read_text(encoding="utf-8").strip().encode("ascii")
    fernet = Fernet(key)

    for name in ERP_CANDIDATES:
        path = base / name
        if not path.exists():
            continue
        token = path.read_bytes().strip()
        try:
            plain = fernet.decrypt(token).decode("utf-8", errors="replace")
        except InvalidToken:
            # alguns legados gravam o token como texto
            try:
                plain = fernet.decrypt(token.decode("utf-8").strip().encode("ascii")).decode(
                    "utf-8", errors="replace"
                )
            except Exception:
                continue
        try:
            data = json.loads(plain)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue

        user = str(_first(data, "usuario", "user", "oracle_user", "User ID", "uid") or "").strip()
        password = str(
            _first(data, "senha", "password", "oracle_password", "Password", "pwd") or ""
        )
        client_lib = str(
            _first(
                data,
                "oracle_client",
                "oracle_client_lib_dir",
                "instant_client",
                "instantclient",
                "lib_dir",
                "ORACLE_CLIENT_LIB_DIR",
            )
            or ""
        ).strip()
        if not client_lib:
            client_lib = resolve_oracle_client_lib_dir(base)
        elif not Path(client_lib).is_dir():
            client_lib = resolve_oracle_client_lib_dir(base)

        dsn, host, port, service = _build_dsn(data)
        if user and dsn:
            return GlobusSettings(
                user=user,
                password=password,
                dsn=dsn,
                source_file=name,
                conf_dir=str(base),
                host=host,
                port=port,
                service_name=service,
                oracle_client_lib_dir=client_lib,
            )
    return None
