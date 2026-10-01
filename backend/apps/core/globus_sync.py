"""Sincronizacao Globus (Oracle SELECT) -> tabelas espelho locais."""

from __future__ import annotations

import hashlib
import os
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Iterable

from django.db import transaction
from django.utils import timezone

from .globus_oracle import GlobusOracleClient, GlobusOracleError, _call_timeout_ms
from .models import CompraGlobus, FornecedorGlobus, PecaGlobus, SaidaGlobus, SyncLog, VeiculoGlobus

SQL_SYNC_PECAS = """
SELECT
    TRIM(M.CODIGOINTERNOMATERIAL) AS codigo_interno,
    TRIM(M.DESCRICAOMAT) AS descricao,
    TO_CHAR(M.CODIGOMATINT) AS codigo_mat_int,
    TRIM(TO_CHAR(M.CODIGOGRE)) AS codigo_grupo
FROM GLOBUS.EST_CADMATERIAL M
WHERE 1=1
{grupo_filter}
"""

SQL_SYNC_VEICULOS = """
SELECT
    TRIM(TO_CHAR(V.PREFIXOVEIC)) AS prefixo,
    TRIM(V.PLACAATUALVEIC) AS placa,
    TO_CHAR(V.CODIGOVEIC) AS codigo_veic_globus,
    TRIM(TO_CHAR(V.CODIGOEMPRESA)) AS codigo_empresa,
    TRIM(V.CONDICAOVEIC) AS condicao
FROM GLOBUS.FRT_CADVEICULOS V
WHERE V.CONDICAOVEIC = 'A'
"""

SQL_SYNC_FORNECEDORES = """
SELECT
    TO_CHAR(F.CODIGOFORN) AS codigo_forn,
    TRIM(F.NFANTASIAFORN) AS nome_fantasia,
    TRIM(TO_CHAR(F.NRFORN)) AS nr_forn
FROM GLOBUS.BGM_FORNECEDOR F
"""

SQL_SYNC_COMPRAS = """
SELECT
    A.CODIGOEMPRESA AS cod_empresa,
    DECODE(
        A.CODIGOEMPRESA,
        1, 'Viacao Redentor Ltda',
        2, 'Transportes Futuro Ltda',
        3, 'Transportes Barra Ltda',
        TO_CHAR(A.CODIGOEMPRESA)
    ) AS empresa,
    F.CODINTNF AS codintnf,
    B.CODIGOMATINT AS codigomatint,
    A.SEQMOVTO AS seqmovto,
    TRIM(TO_CHAR(F.NUMERONF)) AS numero_nf,
    TRIM(F.SERIENF) AS serie_nf,
    F.DATAEMISSAONF AS data_emissao,
    A.DATAMOVTO AS data_movto,
    TRIM(C.CODIGOINTERNOMATERIAL) AS peca_codigo,
    TRIM(C.DESCRICAOMAT) AS peca_descricao,
    TRIM(TO_CHAR(E.NRFORN)) AS fornecedor_codigo,
    TRIM(E.NFANTASIAFORN) AS fornecedor_nome,
    B.QTDEITENSMOVTO AS quantidade,
    D.VALORUNITARIOITENSNF AS valor_unitario
FROM GLOBUS.EST_MOVTO A
JOIN GLOBUS.EST_ITENSMOVTO B
  ON B.SEQMOVTO = A.SEQMOVTO
JOIN GLOBUS.EST_CADMATERIAL C
  ON C.CODIGOMATINT = B.CODIGOMATINT
LEFT JOIN GLOBUS.BGM_NOTAFISCAL F
  ON F.CODINTNF = A.CODINTNF
LEFT JOIN GLOBUS.EST_ITENSNF D
  ON D.CODINTNF = F.CODINTNF
 AND D.CODIGOMATINT = B.CODIGOMATINT
LEFT JOIN GLOBUS.BGM_FORNECEDOR E
  ON E.CODIGOFORN = F.CODIGOFORN
WHERE A.CODIGOHISMOV IN (1, 10)
  AND A.CODIGOEMPRESA IN (1, 2, 3)
  AND A.DATAMOVTO >= :data_ini
  AND A.DATAMOVTO < :data_fim_exclusive
{grupo_filter}
"""

SQL_SYNC_SAIDAS = """
SELECT
    A.CODIGOEMPRESA AS cod_empresa,
    DECODE(
        A.CODIGOEMPRESA,
        1, 'Viacao Redentor Ltda',
        2, 'Transportes Futuro Ltda',
        3, 'Transportes Barra Ltda',
        TO_CHAR(A.CODIGOEMPRESA)
    ) AS empresa,
    A.SEQMOVTO AS seqmovto,
    B.CODIGOMATINT AS codigomatint,
    A.DATAMOVTO AS data_movto,
    TRIM(H.TIPOHISMOV) AS tipo_his,
    TRIM(C.CODIGOINTERNOMATERIAL) AS peca_codigo,
    TRIM(C.DESCRICAOMAT) AS peca_descricao,
    TRIM(TO_CHAR(COALESCE(V1.PREFIXOVEIC, V2.PREFIXOVEIC))) AS veiculo_codigo,
    TRIM(TO_CHAR(F.NUMERONF)) AS numero_nf,
    TRIM(TO_CHAR(E.NRFORN)) AS fornecedor_codigo,
    TRIM(E.NFANTASIAFORN) AS fornecedor_nome,
    B.QTDEITENSMOVTO AS quantidade,
    D.VALORUNITARIOITENSNF AS valor_unitario
FROM GLOBUS.EST_MOVTO A
JOIN GLOBUS.EST_ITENSMOVTO B
  ON B.SEQMOVTO = A.SEQMOVTO
JOIN GLOBUS.EST_HISTORICOMOVTO H
  ON H.CODIGOHISMOV = A.CODIGOHISMOV
JOIN GLOBUS.EST_CADMATERIAL C
  ON C.CODIGOMATINT = B.CODIGOMATINT
LEFT JOIN GLOBUS.BGM_NOTAFISCAL F
  ON F.CODINTNF = A.CODINTNF
LEFT JOIN GLOBUS.EST_ITENSNF D
  ON D.CODINTNF = F.CODINTNF
 AND D.CODIGOMATINT = B.CODIGOMATINT
LEFT JOIN GLOBUS.BGM_FORNECEDOR E
  ON E.CODIGOFORN = F.CODIGOFORN
LEFT JOIN GLOBUS.EST_REQUISICAO R
  ON R.NUMERORQ = A.NUMERORQ
LEFT JOIN GLOBUS.FRT_CADVEICULOS V1
  ON V1.CODIGOVEIC = R.CODIGOVEIC
LEFT JOIN GLOBUS.EST_OUTRASSAIDAS OS
  ON TO_CHAR(OS.NROUTSAI) = TO_CHAR(A.DOCUMENTO)
 AND OS.CODIGOEMPRESA = A.CODIGOEMPRESA
LEFT JOIN GLOBUS.FRT_CADVEICULOS V2
  ON V2.CODIGOVEIC = OS.CODIGOVEIC
WHERE TRIM(H.TIPOHISMOV) IN ('SA', 'SV', 'DS', 'RA')
  AND A.CODIGOEMPRESA IN (1, 2, 3)
  AND A.DATAMOVTO >= :data_ini
  AND A.DATAMOVTO < :data_fim_exclusive
  AND COALESCE(V1.PREFIXOVEIC, V2.PREFIXOVEIC) IS NOT NULL
{grupo_filter}
"""


def _grupos_pecas() -> list[str]:
    raw = (os.environ.get("GLOBUS_GRUPOS_PECAS") or "").strip()
    if not raw:
        return []
    return [g.strip() for g in raw.split(",") if g.strip()]


def _grupo_filter_sql(alias: str = "C") -> str:
    grupos = _grupos_pecas()
    if not grupos:
        return ""
    # CODIGOGRE costuma ser char/number; compara como texto
    quoted = ", ".join(f"'{g}'" for g in grupos)
    return f" AND TRIM(TO_CHAR({alias}.CODIGOGRE)) IN ({quoted})"


def _as_str(value: Any, maxlen: int = 255) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return text[:maxlen]


def _as_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _as_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def compra_chave_unica(
    cod_empresa: Any,
    codintnf: Any,
    codigomatint: Any,
    data_movto: Any,
    seqmovto: Any,
) -> str:
    dm = _as_date(data_movto)
    dm_s = dm.isoformat() if dm else ""
    payload = (
        f"{_as_str(cod_empresa)}|{_as_str(codintnf)}|{_as_str(codigomatint)}|"
        f"{dm_s}|{_as_str(seqmovto)}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _last_ok_inicio(tipo: str) -> datetime | None:
    log = (
        SyncLog.objects.filter(tipo=tipo, status=SyncLog.Status.OK)
        .order_by("-inicio")
        .first()
    )
    return log.inicio if log else None


def _movto_window(full: bool, tipo_log: str) -> tuple[date, date]:
    hoje = timezone.localdate()
    fim_exclusive = hoje + timedelta(days=1)
    if full:
        return hoje.replace(year=hoje.year - 5), fim_exclusive
    last = _last_ok_inicio(tipo_log)
    if last is None:
        return hoje.replace(year=hoje.year - 5), fim_exclusive
    ini = (last - timedelta(days=3)).date()
    return ini, fim_exclusive


def _compras_window(full: bool) -> tuple[date, date]:
    return _movto_window(full, SyncLog.Tipo.COMPRAS)


def _oracle_client() -> GlobusOracleClient:
    return GlobusOracleClient(
        call_timeout_ms=_call_timeout_ms(60000),
        use_pool=True,
    )


def _run_sync(
    tipo: str,
    reader: Callable[[GlobusOracleClient], Iterable[list[dict]]],
    writer: Callable[[list[dict]], int],
) -> SyncLog:
    inicio = timezone.now()
    log = SyncLog.objects.create(
        tipo=tipo,
        inicio=inicio,
        status=SyncLog.Status.RODANDO,
        linhas_lidas=0,
        linhas_gravadas=0,
    )
    lidas = 0
    gravadas = 0
    try:
        client = _oracle_client()
        if not client.configured:
            raise GlobusOracleError("Oracle Globus nao configurado.")
        for batch in reader(client):
            lidas += len(batch)
            if batch:
                gravadas += writer(batch)
        log.linhas_lidas = lidas
        log.linhas_gravadas = gravadas
        log.status = SyncLog.Status.OK
        log.fim = timezone.now()
        log.erro = ""
        log.save(update_fields=["linhas_lidas", "linhas_gravadas", "status", "fim", "erro"])
    except Exception as exc:
        log.linhas_lidas = lidas
        log.linhas_gravadas = gravadas
        log.status = SyncLog.Status.ERRO
        log.fim = timezone.now()
        log.erro = str(exc)[:4000]
        log.save(update_fields=["linhas_lidas", "linhas_gravadas", "status", "fim", "erro"])
        raise
    return log


def _upsert_pecas(batch: list[dict]) -> int:
    now = timezone.now()
    objs = []
    for row in batch:
        codigo = _as_str(row.get("codigo_interno"), 40)
        if not codigo:
            continue
        objs.append(
            PecaGlobus(
                codigo_interno=codigo,
                descricao=_as_str(row.get("descricao"), 255),
                codigo_mat_int=_as_str(row.get("codigo_mat_int"), 40),
                codigo_grupo=_as_str(row.get("codigo_grupo"), 20),
                atualizado_em=now,
            )
        )
    if not objs:
        return 0
    with transaction.atomic():
        PecaGlobus.objects.bulk_create(
            objs,
            update_conflicts=True,
            unique_fields=["codigo_interno"],
            update_fields=["descricao", "codigo_mat_int", "codigo_grupo", "atualizado_em"],
            batch_size=1000,
        )
    return len(objs)


def _upsert_veiculos(batch: list[dict]) -> int:
    now = timezone.now()
    objs = []
    for row in batch:
        codigo = _as_str(row.get("codigo_veic_globus"), 40)
        if not codigo:
            continue
        objs.append(
            VeiculoGlobus(
                codigo_veic_globus=codigo,
                prefixo=_as_str(row.get("prefixo"), 30),
                placa=_as_str(row.get("placa"), 20),
                codigo_empresa=_as_str(row.get("codigo_empresa"), 20),
                condicao=_as_str(row.get("condicao"), 10),
                atualizado_em=now,
            )
        )
    if not objs:
        return 0
    with transaction.atomic():
        VeiculoGlobus.objects.bulk_create(
            objs,
            update_conflicts=True,
            unique_fields=["codigo_veic_globus"],
            update_fields=["prefixo", "placa", "codigo_empresa", "condicao", "atualizado_em"],
            batch_size=1000,
        )
    return len(objs)


def _upsert_fornecedores(batch: list[dict]) -> int:
    now = timezone.now()
    objs = []
    for row in batch:
        codigo = _as_str(row.get("codigo_forn"), 40)
        if not codigo:
            continue
        objs.append(
            FornecedorGlobus(
                codigo_forn=codigo,
                nome_fantasia=_as_str(row.get("nome_fantasia"), 200),
                nr_forn=_as_str(row.get("nr_forn"), 40),
                atualizado_em=now,
            )
        )
    if not objs:
        return 0
    with transaction.atomic():
        FornecedorGlobus.objects.bulk_create(
            objs,
            update_conflicts=True,
            unique_fields=["codigo_forn"],
            update_fields=["nome_fantasia", "nr_forn", "atualizado_em"],
            batch_size=1000,
        )
    return len(objs)


def _upsert_compras(batch: list[dict]) -> int:
    now = timezone.now()
    objs = []
    for row in batch:
        chave = compra_chave_unica(
            row.get("cod_empresa"),
            row.get("codintnf"),
            row.get("codigomatint"),
            row.get("data_movto"),
            row.get("seqmovto"),
        )
        peca = _as_str(row.get("peca_codigo"), 40)
        if not peca:
            continue
        objs.append(
            CompraGlobus(
                chave_unica=chave,
                empresa=_as_str(row.get("empresa"), 80),
                numero_nf=_as_str(row.get("numero_nf"), 30),
                serie_nf=_as_str(row.get("serie_nf"), 10),
                data_emissao=_as_date(row.get("data_emissao")),
                data_movto=_as_date(row.get("data_movto")),
                peca_codigo=peca,
                peca_descricao=_as_str(row.get("peca_descricao"), 255),
                fornecedor_codigo=_as_str(row.get("fornecedor_codigo"), 40),
                fornecedor_nome=_as_str(row.get("fornecedor_nome"), 200),
                quantidade=_as_decimal(row.get("quantidade")),
                valor_unitario=_as_decimal(row.get("valor_unitario")),
                atualizado_em=now,
            )
        )
    if not objs:
        return 0
    with transaction.atomic():
        CompraGlobus.objects.bulk_create(
            objs,
            update_conflicts=True,
            unique_fields=["chave_unica"],
            update_fields=[
                "empresa",
                "numero_nf",
                "serie_nf",
                "data_emissao",
                "data_movto",
                "peca_codigo",
                "peca_descricao",
                "fornecedor_codigo",
                "fornecedor_nome",
                "quantidade",
                "valor_unitario",
                "atualizado_em",
            ],
            batch_size=1000,
        )
    return len(objs)


def sync_pecas(*, full: bool = False) -> SyncLog:
    grupo = _grupo_filter_sql("M")
    sql = SQL_SYNC_PECAS.format(grupo_filter=grupo)

    def reader(client: GlobusOracleClient):
        return client.iter_batches(sql, arraysize=1000)

    return _run_sync(SyncLog.Tipo.PECAS, reader, _upsert_pecas)


def sync_veiculos(*, full: bool = False) -> SyncLog:
    def reader(client: GlobusOracleClient):
        return client.iter_batches(SQL_SYNC_VEICULOS, arraysize=1000)

    return _run_sync(SyncLog.Tipo.VEICULOS, reader, _upsert_veiculos)


def sync_fornecedores(*, full: bool = False) -> SyncLog:
    def reader(client: GlobusOracleClient):
        return client.iter_batches(SQL_SYNC_FORNECEDORES, arraysize=1000)

    return _run_sync(SyncLog.Tipo.FORNECEDORES, reader, _upsert_fornecedores)


def sync_compras(*, full: bool = False) -> SyncLog:
    data_ini, data_fim_exclusive = _compras_window(full)
    grupo = _grupo_filter_sql("C")
    sql = SQL_SYNC_COMPRAS.format(grupo_filter=grupo)
    params = {"data_ini": data_ini, "data_fim_exclusive": data_fim_exclusive}

    def reader(client: GlobusOracleClient):
        return client.iter_batches(sql, params, arraysize=1000)

    return _run_sync(SyncLog.Tipo.COMPRAS, reader, _upsert_compras)


def _upsert_saidas(batch: list[dict]) -> int:
    now = timezone.now()
    objs = []
    for row in batch:
        veiculo = _as_str(row.get("veiculo_codigo"), 40)
        peca = _as_str(row.get("peca_codigo"), 40)
        if not veiculo or not peca:
            continue
        chave = compra_chave_unica(
            row.get("cod_empresa"),
            row.get("seqmovto"),
            row.get("codigomatint"),
            row.get("data_movto"),
            f"{veiculo}|{_as_str(row.get('tipo_his'), 10)}",
        )
        objs.append(
            SaidaGlobus(
                chave_unica=chave,
                empresa=_as_str(row.get("empresa"), 80),
                veiculo_codigo=veiculo,
                peca_codigo=peca,
                peca_descricao=_as_str(row.get("peca_descricao"), 255),
                data_movto=_as_date(row.get("data_movto")),
                tipo_his=_as_str(row.get("tipo_his"), 10),
                numero_nf=_as_str(row.get("numero_nf"), 30),
                fornecedor_codigo=_as_str(row.get("fornecedor_codigo"), 40),
                fornecedor_nome=_as_str(row.get("fornecedor_nome"), 200),
                quantidade=_as_decimal(row.get("quantidade")),
                valor_unitario=_as_decimal(row.get("valor_unitario")),
                atualizado_em=now,
            )
        )
    if not objs:
        return 0
    with transaction.atomic():
        SaidaGlobus.objects.bulk_create(
            objs,
            update_conflicts=True,
            unique_fields=["chave_unica"],
            update_fields=[
                "empresa",
                "veiculo_codigo",
                "peca_codigo",
                "peca_descricao",
                "data_movto",
                "tipo_his",
                "numero_nf",
                "fornecedor_codigo",
                "fornecedor_nome",
                "quantidade",
                "valor_unitario",
                "atualizado_em",
            ],
            batch_size=1000,
        )
    return len(objs)


def sync_saidas(*, full: bool = False) -> SyncLog:
    data_ini, data_fim_exclusive = _movto_window(full, SyncLog.Tipo.SAIDAS)
    grupo = _grupo_filter_sql("C")
    sql = SQL_SYNC_SAIDAS.format(grupo_filter=grupo)
    params = {"data_ini": data_ini, "data_fim_exclusive": data_fim_exclusive}

    def reader(client: GlobusOracleClient):
        return client.iter_batches(sql, params, arraysize=1000)

    return _run_sync(SyncLog.Tipo.SAIDAS, reader, _upsert_saidas)


TIPOS_SYNC = {
    SyncLog.Tipo.PECAS: sync_pecas,
    SyncLog.Tipo.VEICULOS: sync_veiculos,
    SyncLog.Tipo.FORNECEDORES: sync_fornecedores,
    SyncLog.Tipo.COMPRAS: sync_compras,
    SyncLog.Tipo.SAIDAS: sync_saidas,
}


def run_sync(*, full: bool = False, tipo: str | None = None) -> list[SyncLog]:
    if tipo:
        if tipo not in TIPOS_SYNC:
            raise ValueError(f"Tipo invalido: {tipo}. Use: {', '.join(TIPOS_SYNC)}")
        return [TIPOS_SYNC[tipo](full=full)]
    logs = []
    for name in (
        SyncLog.Tipo.PECAS,
        SyncLog.Tipo.VEICULOS,
        SyncLog.Tipo.FORNECEDORES,
        SyncLog.Tipo.COMPRAS,
        SyncLog.Tipo.SAIDAS,
    ):
        logs.append(TIPOS_SYNC[name](full=full))
    return logs


def compras_por_codigos_local(
    codigos: list[str],
    *,
    data_ini: date | None = None,
    data_fim: date | None = None,
    limite_por_peca: int = 5,
) -> dict[str, list[dict[str, Any]]]:
    """Consulta CompraGlobus local (sem Oracle)."""
    codigos_norm = [c.strip() for c in codigos if c and str(c).strip()]
    if not codigos_norm:
        return {}

    qs = CompraGlobus.objects.filter(peca_codigo__in=codigos_norm)
    if data_ini:
        qs = qs.filter(data_movto__gte=data_ini)
    if data_fim:
        qs = qs.filter(data_movto__lte=data_fim)
    qs = qs.order_by("peca_codigo", "-data_movto", "-id")

    out: dict[str, list[dict[str, Any]]] = {c: [] for c in codigos_norm}
    # also case-insensitive index
    lower_map = {c.lower(): c for c in codigos_norm}

    for row in qs.iterator(chunk_size=2000):
        key = row.peca_codigo
        if key not in out:
            key = lower_map.get(row.peca_codigo.lower(), "")
            if not key:
                continue
        bucket = out[key]
        if len(bucket) >= limite_por_peca:
            continue
        bucket.append(
            {
                "empresa": row.empresa,
                "numero_nf": row.numero_nf,
                "serie_nf": row.serie_nf,
                "data_emissao_nf": row.data_emissao.isoformat() if row.data_emissao else None,
                "data_entrada_nf": None,
                "data_movto": row.data_movto.isoformat() if row.data_movto else None,
                "peca_codigo": row.peca_codigo,
                "peca_descricao": row.peca_descricao,
                "valor_unitario": str(row.valor_unitario) if row.valor_unitario is not None else None,
                "fornecedor_nome": row.fornecedor_nome,
                "fornecedor_codigo": row.fornecedor_codigo,
                "quantidade": str(row.quantidade) if row.quantidade is not None else None,
            }
        )
    return out


def sync_status_payload(*, ping_oracle: bool = True) -> dict[str, Any]:
    """Payload de status do espelho (SyncLog). Com ping_oracle=True, testa conf/ Oracle."""
    agora = timezone.now()
    tipos = list(SyncLog.Tipo.values)
    por_tipo: dict[str, Any] = {}
    pior_falhou = False
    em_andamento = False
    mais_recente: datetime | None = None
    stale = False

    for tipo in tipos:
        log = SyncLog.objects.filter(tipo=tipo).order_by("-inicio").first()
        if not log:
            por_tipo[tipo] = None
            continue
        # RODANDO ou ERRO legado sem fim = sync ainda em execucao
        unfinished = log.status == SyncLog.Status.RODANDO or (
            log.status == SyncLog.Status.ERRO and log.fim is None and not (log.erro or "").strip()
        )
        if unfinished:
            em_andamento = True
            finished = (
                SyncLog.objects.filter(tipo=tipo)
                .exclude(pk=log.pk)
                .exclude(fim__isnull=True, erro="")
                .order_by("-inicio")
                .first()
            )
            if finished is None:
                finished = (
                    SyncLog.objects.filter(tipo=tipo, status=SyncLog.Status.OK)
                    .order_by("-inicio")
                    .first()
                )
            por_tipo[tipo] = {
                "tipo": log.tipo,
                "status": SyncLog.Status.RODANDO,
                "inicio": log.inicio.isoformat(),
                "fim": None,
                "linhas_lidas": log.linhas_lidas,
                "linhas_gravadas": log.linhas_gravadas,
                "erro": "",
                "age_hours": None,
            }
            log = finished
            if not log:
                continue
        age_h = (agora - (log.fim or log.inicio)).total_seconds() / 3600.0
        if por_tipo.get(tipo) is None or por_tipo[tipo].get("status") != SyncLog.Status.RODANDO:
            por_tipo[tipo] = {
                "tipo": log.tipo,
                "status": log.status,
                "inicio": log.inicio.isoformat(),
                "fim": log.fim.isoformat() if log.fim else None,
                "linhas_lidas": log.linhas_lidas,
                "linhas_gravadas": log.linhas_gravadas,
                "erro": log.erro or "",
                "age_hours": round(age_h, 2),
            }
        ref = log.fim or log.inicio
        if mais_recente is None or ref > mais_recente:
            mais_recente = ref
        if log.status == SyncLog.Status.ERRO:
            pior_falhou = True
        if age_h > 24:
            stale = True

    compras_log = por_tipo.get(SyncLog.Tipo.COMPRAS)
    if compras_log and compras_log.get("status") == SyncLog.Status.ERRO:
        pior_falhou = True

    oracle_ok = False
    oracle_detail = "conf/ nao verificada."
    configured = False
    if ping_oracle:
        from .globus_oracle import GlobusOracleClient

        try:
            client = GlobusOracleClient(call_timeout_ms=5000, use_pool=False)
            configured = client.configured
            oracle_ok, oracle_detail, _ = client.ping()
        except Exception as exc:
            oracle_ok = False
            oracle_detail = f"Falha ao ler conf/ ou ping Oracle: {exc}"
            configured = False
    else:
        from .globus_conf import load_globus_settings

        settings_g = load_globus_settings()
        configured = bool(settings_g and settings_g.user and settings_g.dsn)

    ok = bool(mais_recente) and not pior_falhou and not stale and not em_andamento
    if em_andamento:
        detail = "Sync Globus em andamento."
        ok = False
    elif not mais_recente:
        if ping_oracle and oracle_ok:
            detail = "Oracle OK (conf/). Espelho local ainda sem sync_globus."
        elif ping_oracle and not configured:
            detail = oracle_detail
        elif ping_oracle:
            detail = oracle_detail or "Nenhum sync_globus registrado."
        else:
            detail = "Nenhum sync_globus registrado. Rode python manage.py sync_globus."
        ok = False
        stale = True
    elif pior_falhou:
        detail = "Ultimo sync com erro. Ver SyncLog."
    elif stale:
        detail = "Sync com mais de 24h."
    else:
        detail = "Espelho Globus atualizado (somente leitura no Oracle via job)."

    payload: dict[str, Any] = {
        "ok": ok,
        "detail": detail,
        "readonly": True,
        "configured": configured,
        "atualizado_em": mais_recente.isoformat() if mais_recente else None,
        "stale": stale or not mais_recente,
        "falhou": pior_falhou,
        "em_andamento": em_andamento,
        "sync": por_tipo,
        "source": "synclog+conf" if ping_oracle else "synclog",
    }
    if ping_oracle:
        payload["oracle_ok"] = oracle_ok
        payload["oracle_detail"] = oracle_detail
    return payload
