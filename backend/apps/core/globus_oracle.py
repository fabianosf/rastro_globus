"""Cliente Oracle Globus — SOMENTE LEITURA (SELECT/WITH).

Nunca executa INSERT/UPDATE/DELETE/MERGE no Globo.
"""

from __future__ import annotations

import logging
import os
import re
from contextlib import contextmanager
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
_POOL = None
_POOL_TIMEOUT_MS: int | None = None


class GlobusOracleError(Exception):
    """Erro amigavel de consulta Globus."""


def _call_timeout_ms(default_ms: int) -> int:
    raw = (os.environ.get("GLOBUS_CALL_TIMEOUT_MS") or "").strip()
    if not raw:
        return default_ms
    try:
        return max(1000, int(raw))
    except ValueError:
        return default_ms


def _ensure_thick_mode(lib_dir: str | None = None) -> tuple[bool, str]:
    global _THICK_READY, _THICK_ERROR
    if _THICK_READY:
        return True, "thick mode already active"

    import oracledb

    candidates: list[str] = []
    if lib_dir:
        candidates.append(lib_dir)
    env_lib = (os.environ.get("ORACLE_CLIENT_LIB_DIR") or "").strip()
    if env_lib:
        candidates.append(env_lib)

    errors: list[str] = []
    for folder in candidates:
        if not folder or not os.path.isdir(folder):
            if folder:
                errors.append(f"{folder}: nao encontrado")
            continue
        try:
            oracledb.init_oracle_client(lib_dir=folder)
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

    _THICK_ERROR = " | ".join(errors) if errors else (
        "Instant Client nao encontrado. Defina ORACLE_CLIENT_LIB_DIR ou PATH."
    )
    return False, _THICK_ERROR


def assert_readonly_sql(sql: str) -> None:
    text = (sql or "").strip()
    if not text:
        raise GlobusOracleError("SQL vazio.")
    if _WRITE_RE.search(text) or not _READ_RE.search(text):
        raise GlobusOracleError(
            "Somente consultas SELECT/WITH sao permitidas no Globus (somente leitura)."
        )


def reset_pool() -> None:
    global _POOL, _POOL_TIMEOUT_MS
    if _POOL is not None:
        try:
            _POOL.close()
        except Exception:
            pass
    _POOL = None
    _POOL_TIMEOUT_MS = None


class GlobusOracleClient:
    def __init__(
        self,
        settings: GlobusSettings | None = None,
        *,
        call_timeout_ms: int | None = None,
        use_pool: bool = False,
    ):
        self.settings = settings if settings is not None else load_globus_settings()
        self.call_timeout_ms = (
            call_timeout_ms
            if call_timeout_ms is not None
            else _call_timeout_ms(15000)
        )
        self.use_pool = use_pool

    @property
    def configured(self) -> bool:
        return bool(self.settings and self.settings.user and self.settings.dsn)

    def public_status_base(self) -> dict:
        if not self.settings:
            return {
                "configured": False,
                "detail": "conf/ nao encontrada ou erp.dat invalido. "
                "Defina RASTROGLOBUS_CONF_DIR se necessario.",
            }
        return self.settings.public_summary()

    def _acquire_pooled(self):
        global _POOL, _POOL_TIMEOUT_MS
        import oracledb

        timeout = self.call_timeout_ms
        if _POOL is None or _POOL_TIMEOUT_MS != timeout:
            reset_pool()
            _POOL = oracledb.create_pool(
                user=self.settings.user,
                password=self.settings.password,
                dsn=self.settings.dsn,
                min=1,
                max=4,
                increment=1,
                getmode=oracledb.POOL_GETMODE_WAIT,
            )
            _POOL_TIMEOUT_MS = timeout
        conn = _POOL.acquire()
        try:
            conn.call_timeout = timeout
        except Exception:
            pass
        return conn

    @contextmanager
    def connection(self):
        if not self.configured or not self.settings:
            raise GlobusOracleError(
                "Oracle Globus nao configurado. Verifique conf/chave.key e conf/erp.dat."
            )
        import oracledb

        ok_thick, thick_msg = _ensure_thick_mode()
        if ok_thick:
            logger.info("Oracle Globus: %s", thick_msg)
        else:
            logger.warning(
                "Oracle Instant Client indisponivel (%s). Tentando thin (pode falhar com DPY-3001).",
                thick_msg,
            )

        conn = None
        try:
            if self.use_pool:
                conn = self._acquire_pooled()
            else:
                conn = oracledb.connect(
                    user=self.settings.user,
                    password=self.settings.password,
                    dsn=self.settings.dsn,
                )
                try:
                    conn.call_timeout = self.call_timeout_ms
                except Exception:
                    pass
        except GlobusOracleError:
            raise
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
            if conn is None:
                return
            if self.use_pool and _POOL is not None:
                try:
                    _POOL.release(conn)
                except Exception:
                    try:
                        conn.close()
                    except Exception:
                        pass
            else:
                conn.close()

    def fetch_all(
        self,
        sql: str,
        params: dict | Iterable | None = None,
        *,
        arraysize: int | None = None,
    ) -> list[dict[str, Any]]:
        assert_readonly_sql(sql)
        with self.connection() as conn:
            cur = conn.cursor()
            if arraysize:
                cur.arraysize = arraysize
            cur.execute(sql, params or {})
            columns = [d[0].lower() for d in cur.description] if cur.description else []
            rows = cur.fetchall()
            return [dict(zip(columns, row)) for row in rows]

    def iter_batches(
        self,
        sql: str,
        params: dict | Iterable | None = None,
        *,
        arraysize: int = 1000,
    ):
        """Yield listas de dicts em lotes (arraysize)."""
        assert_readonly_sql(sql)
        with self.connection() as conn:
            cur = conn.cursor()
            cur.arraysize = arraysize
            cur.execute(sql, params or {})
            columns = [d[0].lower() for d in cur.description] if cur.description else []
            while True:
                rows = cur.fetchmany(arraysize)
                if not rows:
                    break
                yield [dict(zip(columns, row)) for row in rows]

    def fetch_one(self, sql: str, params: dict | Iterable | None = None) -> dict[str, Any] | None:
        rows = self.fetch_all(sql, params)
        return rows[0] if rows else None

    def ping(self) -> tuple[bool, str, dict]:
        base = self.public_status_base()
        if not self.configured:
            return False, base.get("detail", "Nao configurado."), base
        try:
            row = self.fetch_one("SELECT 1 AS ok FROM DUAL")
            ok = bool(row and int(row.get("ok", 0)) == 1)
            return ok, "Oracle/Globus OK (somente leitura).", {**base, "connected": ok}
        except GlobusOracleError as exc:
            return False, str(exc), {**base, "connected": False}
        except Exception as exc:
            return False, f"Falha no ping Globus: {exc}", {**base, "connected": False}
