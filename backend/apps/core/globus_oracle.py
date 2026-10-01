"""Cliente Oracle Globus — SOMENTE LEITURA (SELECT/WITH).

Nunca executa INSERT/UPDATE/DELETE/MERGE no Globo.
"""

from __future__ import annotations

import logging
import os
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable

from .globus_conf import GlobusSettings, load_globus_settings

logger = logging.getLogger(__name__)

_WRITE_RE = re.compile(
    r"^\s*(INSERT|UPDATE|DELETE|MERGE|ALTER|DROP|CREATE|TRUNCATE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)
_READ_RE = re.compile(r"^\s*(SELECT|WITH)\b", re.IGNORECASE)

_THICK_READY = False
_THICK_ERROR: str | None = None

_CLIENT_CANDIDATES = (
    Path(r"C:\Users\fabiano.freitas\Documents\PROJ_TOT\drivers\oracle_win\oracle\instantclient_21_14"),
    Path(r"C:\Users\fabiano.freitas\Documents\PROJ_TOT\drivers\oracle_win\instantclient_21_14"),
    Path(r"C:\Users\fabiano.freitas\Documents\PROJ_REC_PYTHON\instantclient"),
    Path(r"C:\oracle\instantclient_21_14"),
    Path(r"C:\oracle\BIN"),
    Path(r"C:\oracle"),
)


class GlobusOracleError(Exception):
    """Erro amigável de consulta Globus."""


def _ensure_thick_mode(lib_dir: str | None = None) -> tuple[bool, str]:
    global _THICK_READY, _THICK_ERROR
    if _THICK_READY:
        return True, "thick mode already active"

    import oracledb

    candidates: list[Path] = []
    if lib_dir:
        candidates.append(Path(lib_dir))
    env_lib = (os.environ.get("ORACLE_CLIENT_LIB_DIR") or "").strip()
    if env_lib:
        candidates.append(Path(env_lib))
    candidates.extend(_CLIENT_CANDIDATES)

    errors: list[str] = []
    for folder in candidates:
        if not folder.exists():
            continue
        try:
            oracledb.init_oracle_client(lib_dir=str(folder))
            _THICK_READY = True
            _THICK_ERROR = None
            return True, f"thick mode OK ({folder})"
        except Exception as exc:
            msg = str(exc).lower()
            if "already been initialized" in msg or "dpi-1050" in msg:
                _THICK_READY = True
                _THICK_ERROR = None
                return True, "thick mode already initialized"
            errors.append(f"{folder}: {exc}")

    try:
        oracledb.init_oracle_client()
        _THICK_READY = True
        _THICK_ERROR = None
        return True, "thick mode OK (PATH)"
    except Exception as exc:
        msg = str(exc).lower()
        if "already been initialized" in msg or "dpi-1050" in msg:
            _THICK_READY = True
            return True, "thick mode already initialized"
        errors.append(f"PATH: {exc}")

    _THICK_ERROR = " | ".join(errors) if errors else "Instant Client não encontrado"
    return False, _THICK_ERROR


def assert_readonly_sql(sql: str) -> None:
    text = (sql or "").strip()
    if not text:
        raise GlobusOracleError("SQL vazio.")
    if _WRITE_RE.search(text) or not _READ_RE.search(text):
        raise GlobusOracleError(
            "Somente consultas SELECT/WITH são permitidas no Globus (somente leitura)."
        )


class GlobusOracleClient:
    def __init__(self, settings: GlobusSettings | None = None):
        self.settings = settings if settings is not None else load_globus_settings()

    @property
    def configured(self) -> bool:
        return bool(self.settings and self.settings.user and self.settings.dsn)

    def public_status_base(self) -> dict:
        if not self.settings:
            return {
                "configured": False,
                "detail": "conf/ não encontrada ou erp.dat inválido. "
                "Defina RASTROGLOBUS_CONF_DIR se necessário.",
            }
        return self.settings.public_summary()

    @contextmanager
    def connection(self):
        if not self.configured or not self.settings:
            raise GlobusOracleError(
                "Oracle Globus não configurado. Verifique conf/chave.key e conf/erp.dat."
            )
        import oracledb

        # Thick ANTES de qualquer connect: o Globus usa Native Network Encryption
        # (DPY-3001). Se thin for tentado primeiro, o processo fica preso em thin
        # e o Instant Client não consegue mais ativar.
        ok_thick, thick_msg = _ensure_thick_mode()
        if ok_thick:
            logger.info("Oracle Globus: %s", thick_msg)
        else:
            logger.warning(
                "Oracle Instant Client indisponível (%s). Tentando thin (pode falhar com DPY-3001).",
                thick_msg,
            )

        try:
            conn = oracledb.connect(
                user=self.settings.user,
                password=self.settings.password,
                dsn=self.settings.dsn,
            )
        except Exception as exc:
            err = str(exc)
            hint = ""
            if "DPY-3001" in err or "Native Network Encryption" in err:
                hint = (
                    " O servidor exige Native Network Encryption — use Instant Client "
                    "(thick mode). Defina ORACLE_CLIENT_LIB_DIR e reinicie o backend. "
                    f"Detalhe thick: {thick_msg}"
                )
            raise GlobusOracleError(f"Falha ao conectar no Globus: {exc}.{hint}") from exc

        try:
            yield conn
        finally:
            conn.close()

    def fetch_all(self, sql: str, params: dict | Iterable | None = None) -> list[dict[str, Any]]:
        assert_readonly_sql(sql)
        with self.connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, params or {})
            columns = [d[0].lower() for d in cur.description] if cur.description else []
            rows = cur.fetchall()
            return [dict(zip(columns, row)) for row in rows]

    def fetch_one(self, sql: str, params: dict | Iterable | None = None) -> dict[str, Any] | None:
        rows = self.fetch_all(sql, params)
        return rows[0] if rows else None

    def ping(self) -> tuple[bool, str, dict]:
        base = self.public_status_base()
        if not self.configured:
            return False, base.get("detail", "Não configurado."), base
        try:
            row = self.fetch_one("SELECT 1 AS ok FROM DUAL")
            ok = bool(row and int(row.get("ok", 0)) == 1)
            return ok, "Oracle/Globus OK (somente leitura).", {**base, "connected": ok}
        except GlobusOracleError as exc:
            return False, str(exc), {**base, "connected": False}
        except Exception as exc:
            return False, f"Falha no ping Globus: {exc}", {**base, "connected": False}
