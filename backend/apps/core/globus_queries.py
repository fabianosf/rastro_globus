"""SQLs parametrizados Globus — SOMENTE SELECT.

Tabelas confirmadas em relatórios internos:
  - GLOBUS.BGM_NOTAFISCAL
  - GLOBUS.EST_CADMATERIAL
  - GLOBUS.FRT_CADVEICULOS
  - GLOBUS.EST_MOVTO / EST_ITENSMOVTO / EST_HISTORICOMOVTO (movimentos)
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from .globus_oracle import GlobusOracleClient, GlobusOracleError

# Entrada (compra) e saída (aplicação/baixa) — padrão dos relatórios internos
CODIGOS_ENTRADA = (1, 10)
TIPOS_SAIDA = ("SA", "SV", "DS", "RA")

SQL_NF_POR_NUMERO = """
SELECT
    TRIM(TO_CHAR(N.NUMERONF)) AS numero,
    TRIM(N.SERIENF) AS serie,
    N.DATAEMISSAONF AS data_emissao,
    N.VALORTOTALNF AS valor,
    N.CODIGOFORN AS codigo_fornecedor,
    TRIM(F.NFANTASIAFORN) AS fornecedor_nome,
    TRIM(F.NRFORN) AS fornecedor_nr,
    N.CODINTNF AS cod_int_nf,
    TRIM(N.ENTRADASAIDANF) AS entrada_saida,
    TRIM(N.CODTPDOC) AS tipo_doc
FROM GLOBUS.BGM_NOTAFISCAL N
LEFT JOIN GLOBUS.BGM_FORNECEDOR F
  ON F.CODIGOFORN = N.CODIGOFORN
WHERE (
        TRIM(TO_CHAR(N.NUMERONF)) = :numero
     OR LTRIM(TRIM(TO_CHAR(N.NUMERONF)), '0') = LTRIM(:numero, '0')
      )
  AND N.DATAEMISSAONF >= :data_ini
ORDER BY N.DATAEMISSAONF DESC
FETCH FIRST 20 ROWS ONLY
"""

SQL_PECAS = """
SELECT
    TRIM(M.CODIGOINTERNOMATERIAL) AS codigo_interno,
    TRIM(M.DESCRICAOMAT) AS descricao,
    M.CODIGOMATINT AS codigo_mat_int
FROM GLOBUS.EST_CADMATERIAL M
WHERE UPPER(TRIM(M.CODIGOINTERNOMATERIAL)) LIKE UPPER(:q)
   OR UPPER(TRIM(M.DESCRICAOMAT)) LIKE UPPER(:q)
FETCH FIRST 30 ROWS ONLY
"""

SQL_VEICULOS = """
SELECT
    TRIM(TO_CHAR(V.PREFIXOVEIC)) AS codigo,
    TRIM(V.PLACAATUALVEIC) AS placa,
    V.CODIGOVEIC AS codigo_veic_globus,
    V.CODIGOEMPRESA AS codigo_empresa,
    TRIM(V.CONDICAOVEIC) AS condicao
FROM GLOBUS.FRT_CADVEICULOS V
WHERE V.CONDICAOVEIC = 'A'
  AND (
        UPPER(TRIM(TO_CHAR(V.PREFIXOVEIC))) LIKE UPPER(:q)
     OR UPPER(TRIM(V.PLACAATUALVEIC)) LIKE UPPER(:q)
     OR LTRIM(TRIM(TO_CHAR(V.PREFIXOVEIC)), '0') LIKE LTRIM(:q_digits, '0')
  )
FETCH FIRST 30 ROWS ONLY
"""


def _serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in row.items():
        if hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        elif v is None:
            out[k] = None
        else:
            out[k] = v if isinstance(v, (int, float, bool)) else str(v).strip()
    return out


def buscar_nfs(numero: str, *, meses: int = 24) -> list[dict[str, Any]]:
    """NF por número — só emissões recentes (default 24 meses) para uso operacional."""
    numero = (numero or "").strip()
    if not numero:
        raise GlobusOracleError("Informe o número da NF.")
    try:
        meses_n = max(1, min(int(meses or 24), 120))
    except (TypeError, ValueError):
        meses_n = 24
    # ~30.44 dias/mês; suficiente para janela operacional
    data_ini = date.today() - timedelta(days=int(meses_n * 30.44))
    client = GlobusOracleClient(call_timeout_ms=15000)
    rows = client.fetch_all(
        SQL_NF_POR_NUMERO,
        {"numero": numero, "data_ini": data_ini},
    )
    return [_serialize_row(r) for r in rows]


# Tipos de NF de garantia no Globus (CPRTPDOC / BGM_NOTAFISCAL.CODTPDOC)
TIPOS_NF_GARANTIA = ("NEG", "NFG")

SQL_NFS_GARANTIA = """
SELECT
    TRIM(TO_CHAR(N.NUMERONF)) AS numero,
    TRIM(N.SERIENF) AS serie,
    TRIM(N.CODTPDOC) AS tipo_doc,
    N.DATAEMISSAONF AS data_emissao,
    N.ENTRADASAIDANF AS data_entrada,
    N.VALORTOTALNF AS valor,
    N.CODIGOFORN AS codigo_fornecedor,
    TRIM(F.NFANTASIAFORN) AS fornecedor_nome,
    N.CODINTNF AS cod_int_nf,
    TRIM(MAT.CODIGOINTERNOMATERIAL) AS peca_codigo,
    TRIM(MAT.DESCRICAOMAT) AS peca_descricao
FROM GLOBUS.BGM_NOTAFISCAL N
LEFT JOIN GLOBUS.BGM_FORNECEDOR F
  ON F.CODIGOFORN = N.CODIGOFORN
LEFT JOIN GLOBUS.EST_MOVTO M
  ON M.CODINTNF = N.CODINTNF
LEFT JOIN GLOBUS.EST_ITENSMOVTO I
  ON I.SEQMOVTO = M.SEQMOVTO
LEFT JOIN GLOBUS.EST_CADMATERIAL MAT
  ON MAT.CODIGOMATINT = I.CODIGOMATINT
WHERE TRIM(N.CODTPDOC) IN ('NEG', 'NFG')
  AND N.DATAEMISSAONF >= :data_ini
  AND N.DATAEMISSAONF < :data_fim_exclusive
  {filtros}
ORDER BY N.DATAEMISSAONF DESC NULLS LAST
FETCH FIRST {limite} ROWS ONLY
"""


def buscar_nfs_garantia(
    *,
    numero: str = "",
    peca: str = "",
    data_ini: str | None = None,
    data_fim: str | None = None,
    limite: int = 20,
) -> list[dict[str, Any]]:
    """NFs Globus tipo NEG/NFG (garantia) — somente leitura."""
    numero = (numero or "").strip()
    peca = (peca or "").strip()
    hoje = date.today()
    ini = _parse_date(data_ini, hoje - timedelta(days=365 * 3))
    fim = _parse_date(data_fim, hoje)
    if fim < ini:
        raise GlobusOracleError("data_fim deve ser maior ou igual a data_ini.")

    try:
        limite_n = max(1, min(int(limite or 20), 50))
    except (TypeError, ValueError):
        limite_n = 20

    filtros: list[str] = []
    params: dict[str, Any] = {
        "data_ini": ini,
        "data_fim_exclusive": fim + timedelta(days=1),
    }
    if numero:
        filtros.append(
            "("
            "TRIM(TO_CHAR(N.NUMERONF)) = :numero "
            "OR LTRIM(TRIM(TO_CHAR(N.NUMERONF)), '0') = LTRIM(:numero, '0')"
            ")"
        )
        params["numero"] = numero
    if peca:
        if len(peca) < 2:
            raise GlobusOracleError("Informe ao menos 2 caracteres da peça.")
        digits = "".join(ch for ch in peca if ch.isdigit()) or peca
        filtros.append(
            "("
            "UPPER(TRIM(MAT.CODIGOINTERNOMATERIAL)) LIKE UPPER(:peca) "
            "OR UPPER(TRIM(MAT.DESCRICAOMAT)) LIKE UPPER(:peca) "
            "OR LTRIM(TRIM(TO_CHAR(MAT.CODIGOINTERNOMATERIAL)), '0') = LTRIM(:peca_digits, '0')"
            ")"
        )
        params["peca"] = f"%{peca}%"
        params["peca_digits"] = digits

    if not numero and not peca:
        # sem filtro: só últimas NFs garantia (período já limitado)
        pass

    where_extra = (" AND " + " AND ".join(filtros)) if filtros else ""
    sql = SQL_NFS_GARANTIA.format(filtros=where_extra, limite=limite_n)
    client = GlobusOracleClient()
    rows = client.fetch_all(sql, params)
    # dedupe por cod_int_nf + peca (join pode repetir)
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for raw in rows:
        item = _serialize_row(raw)
        key = f"{item.get('cod_int_nf')}|{item.get('peca_codigo')}|{item.get('numero')}"
        if key in seen:
            continue
        seen.add(key)
        item["tipo_garantia"] = "nf_garantia_globus"
        out.append(item)
    return out


def buscar_pecas(q: str) -> list[dict[str, Any]]:
    q = (q or "").strip()
    if len(q) < 2:
        raise GlobusOracleError("Informe ao menos 2 caracteres para buscar peças.")
    client = GlobusOracleClient()
    rows = client.fetch_all(SQL_PECAS, {"q": f"%{q}%"})
    return [_serialize_row(r) for r in rows]


def buscar_veiculos(q: str) -> list[dict[str, Any]]:
    q = (q or "").strip()
    if len(q) < 2:
        raise GlobusOracleError("Informe ao menos 2 caracteres para buscar veículos.")
    digits = "".join(ch for ch in q if ch.isdigit()) or q
    client = GlobusOracleClient()
    rows = client.fetch_all(SQL_VEICULOS, {"q": f"%{q}%", "q_digits": f"%{digits}%"})
    return [_serialize_row(r) for r in rows]


SQL_MOVIMENTOS_BASE = """
SELECT
    M.DATAMOVTO AS data_movto,
    TRIM(H.TIPOHISMOV) AS tipo_his,
    H.CODIGOHISMOV AS codigo_his,
    TRIM(MAT.CODIGOINTERNOMATERIAL) AS peca_codigo,
    TRIM(MAT.DESCRICAOMAT) AS peca_descricao,
    I.QTDEITENSMOVTO AS quantidade,
    I.VALORTOTALITENSMOVTO AS valor,
    M.NUMERORQ AS requisicao,
    M.DOCUMENTO AS documento,
    TRIM(TO_CHAR(NF.NUMERONF)) AS numero_nf,
    TRIM(TO_CHAR(COALESCE(V1.PREFIXOVEIC, V2.PREFIXOVEIC))) AS veiculo_codigo,
    CASE
        WHEN H.CODIGOHISMOV IN (1, 10) THEN 'entrada'
        WHEN TRIM(H.TIPOHISMOV) IN ('SA', 'SV', 'DS', 'RA') THEN 'saida'
        ELSE 'outro'
    END AS tipo_movimento
FROM GLOBUS.EST_MOVTO M
JOIN GLOBUS.EST_ITENSMOVTO I
  ON I.SEQMOVTO = M.SEQMOVTO
JOIN GLOBUS.EST_HISTORICOMOVTO H
  ON H.CODIGOHISMOV = M.CODIGOHISMOV
JOIN GLOBUS.EST_CADMATERIAL MAT
  ON MAT.CODIGOMATINT = I.CODIGOMATINT
LEFT JOIN GLOBUS.BGM_NOTAFISCAL NF
  ON NF.CODINTNF = M.CODINTNF
LEFT JOIN GLOBUS.EST_REQUISICAO R
  ON R.NUMERORQ = M.NUMERORQ
LEFT JOIN GLOBUS.FRT_CADVEICULOS V1
  ON V1.CODIGOVEIC = R.CODIGOVEIC
LEFT JOIN GLOBUS.EST_OUTRASSAIDAS OS
  ON TO_CHAR(OS.NROUTSAI) = TO_CHAR(M.DOCUMENTO)
 AND OS.CODIGOEMPRESA = M.CODIGOEMPRESA
LEFT JOIN GLOBUS.FRT_CADVEICULOS V2
  ON V2.CODIGOVEIC = OS.CODIGOVEIC
WHERE M.DATAMOVTO >= :data_ini
  AND M.DATAMOVTO < :data_fim_exclusive
"""


def _parse_date(value: str | None, fallback: date) -> date:
    if not value:
        return fallback
    try:
        return date.fromisoformat(str(value).strip()[:10])
    except ValueError as exc:
        raise GlobusOracleError(f"Data inválida: {value}. Use AAAA-MM-DD.") from exc


def _classificar_movimento(row: dict[str, Any]) -> str:
    tipo = str(row.get("tipo_movimento") or "").strip().lower()
    if tipo in {"entrada", "saida"}:
        return tipo
    try:
        codigo = int(row.get("codigo_his") or -1)
    except (TypeError, ValueError):
        codigo = -1
    if codigo in CODIGOS_ENTRADA:
        return "entrada"
    if str(row.get("tipo_his") or "").strip().upper() in TIPOS_SAIDA:
        return "saida"
    return "outro"


def buscar_movimentos(
    *,
    peca: str = "",
    veiculo: str = "",
    data_ini: str | None = None,
    data_fim: str | None = None,
    tipo: str = "todos",
    limite: int = 100,
) -> list[dict[str, Any]]:
    """Consulta entrada/saída de peças no Globus (somente leitura)."""
    hoje = date.today()
    ini = _parse_date(data_ini, hoje - timedelta(days=90))
    fim = _parse_date(data_fim, hoje)
    if fim < ini:
        raise GlobusOracleError("data_fim deve ser maior ou igual a data_ini.")

    tipo_norm = (tipo or "todos").strip().lower()
    if tipo_norm not in {"entrada", "saida", "todos"}:
        raise GlobusOracleError("tipo deve ser entrada, saida ou todos.")

    try:
        limite_n = max(1, min(int(limite or 100), 200))
    except (TypeError, ValueError):
        limite_n = 100

    peca = (peca or "").strip()
    veiculo = (veiculo or "").strip()
    if not peca and not veiculo and not data_ini and not data_fim:
        # exige ao menos um filtro útil além do período padrão
        pass

    clauses: list[str] = []
    params: dict[str, Any] = {
        "data_ini": ini,
        "data_fim_exclusive": fim + timedelta(days=1),
    }

    if tipo_norm == "entrada":
        clauses.append("H.CODIGOHISMOV IN (1, 10)")
    elif tipo_norm == "saida":
        clauses.append("TRIM(H.TIPOHISMOV) IN ('SA', 'SV', 'DS', 'RA')")
    else:
        clauses.append(
            "(H.CODIGOHISMOV IN (1, 10) OR TRIM(H.TIPOHISMOV) IN ('SA', 'SV', 'DS', 'RA'))"
        )

    if peca:
        clauses.append(
            "("
            "UPPER(TRIM(MAT.CODIGOINTERNOMATERIAL)) LIKE UPPER(:peca) "
            "OR UPPER(TRIM(MAT.DESCRICAOMAT)) LIKE UPPER(:peca)"
            ")"
        )
        params["peca"] = f"%{peca}%"

    if veiculo:
        digits = "".join(ch for ch in veiculo if ch.isdigit()) or veiculo
        clauses.append(
            "("
            "UPPER(TRIM(TO_CHAR(COALESCE(V1.PREFIXOVEIC, V2.PREFIXOVEIC)))) LIKE UPPER(:veiculo) "
            "OR LTRIM(TRIM(TO_CHAR(COALESCE(V1.PREFIXOVEIC, V2.PREFIXOVEIC))), '0') "
            "LIKE LTRIM(:veiculo_digits, '0')"
            ")"
        )
        params["veiculo"] = f"%{veiculo}%"
        params["veiculo_digits"] = f"%{digits}%"

    where_extra = ""
    if clauses:
        where_extra = " AND " + " AND ".join(clauses)

    sql = (
        SQL_MOVIMENTOS_BASE
        + where_extra
        + f"\nORDER BY M.DATAMOVTO DESC\nFETCH FIRST {limite_n} ROWS ONLY"
    )

    client = GlobusOracleClient()
    rows = client.fetch_all(sql, params)
    results: list[dict[str, Any]] = []
    for raw in rows:
        item = _serialize_row(raw)
        item["tipo_movimento"] = _classificar_movimento(item)
        results.append(item)
    return results


# Padrão do RELATÓRIO_GERAL_DE_COMPRAS_..._AQUISIÇÃO_DE_PEÇAS.sql
# Entradas CODIGOHISMOV 1/10, grupo estoque peças (CODIGOGRE = 01)
SQL_COMPRAS_PECA = """
SELECT
    DECODE(
        A.CODIGOEMPRESA,
        1, 'Viação Redentor Ltda',
        2, 'Transportes Futuro Ltda',
        3, 'Transportes Barra Ltda',
        TO_CHAR(A.CODIGOEMPRESA)
    ) AS empresa,
    F.ENTRADASAIDANF AS data_entrada_nf,
    TRIM(TO_CHAR(F.NUMERONF)) AS numero_nf,
    TRIM(F.SERIENF) AS serie_nf,
    F.DATAEMISSAONF AS data_emissao_nf,
    F.VALORTOTALNF AS valor_total_nf,
    TRIM(C.CODIGOINTERNOMATERIAL) AS peca_codigo,
    TRIM(C.DESCRICAOMAT) AS peca_descricao,
    D.VALORUNITARIOITENSNF AS valor_unitario,
    TRIM(E.NFANTASIAFORN) AS fornecedor_nome,
    TRIM(TO_CHAR(E.NRFORN)) AS fornecedor_codigo,
    A.DATAMOVTO AS data_movto,
    B.QTDEITENSMOVTO AS quantidade
FROM GLOBUS.EST_MOVTO A
JOIN GLOBUS.EST_ITENSMOVTO B
  ON B.SEQMOVTO = A.SEQMOVTO
JOIN GLOBUS.EST_CADMATERIAL C
  ON C.CODIGOMATINT = B.CODIGOMATINT
LEFT JOIN GLOBUS.BGM_NOTAFISCAL F
  ON F.CODINTNF = A.CODINTNF
LEFT JOIN (
    SELECT CODINTNF, MAX(VALORUNITARIOITENSNF) AS VALORUNITARIOITENSNF
    FROM GLOBUS.EST_ITENSNF
    GROUP BY CODINTNF
) D ON D.CODINTNF = F.CODINTNF
LEFT JOIN GLOBUS.BGM_FORNECEDOR E
  ON E.CODIGOFORN = F.CODIGOFORN
WHERE A.CODIGOHISMOV IN (1, 10)
  AND A.CODIGOEMPRESA IN (1, 2, 3)
  AND C.CODIGOGRE = 01
  AND A.DATAMOVTO >= :data_ini
  AND A.DATAMOVTO < :data_fim_exclusive
  AND (
        UPPER(TRIM(C.CODIGOINTERNOMATERIAL)) LIKE UPPER(:peca)
     OR UPPER(TRIM(C.DESCRICAOMAT)) LIKE UPPER(:peca)
     OR LTRIM(TRIM(TO_CHAR(C.CODIGOINTERNOMATERIAL)), '0') = LTRIM(:peca_digits, '0')
  )
ORDER BY A.DATAMOVTO DESC
FETCH FIRST {limite} ROWS ONLY
"""

SQL_COMPRAS_RECENTES = """
SELECT
    DECODE(
        A.CODIGOEMPRESA,
        1, 'Viação Redentor Ltda',
        2, 'Transportes Futuro Ltda',
        3, 'Transportes Barra Ltda',
        TO_CHAR(A.CODIGOEMPRESA)
    ) AS empresa,
    F.ENTRADASAIDANF AS data_entrada_nf,
    TRIM(TO_CHAR(F.NUMERONF)) AS numero_nf,
    TRIM(F.SERIENF) AS serie_nf,
    F.DATAEMISSAONF AS data_emissao_nf,
    F.VALORTOTALNF AS valor_total_nf,
    TRIM(C.CODIGOINTERNOMATERIAL) AS peca_codigo,
    TRIM(C.DESCRICAOMAT) AS peca_descricao,
    D.VALORUNITARIOITENSNF AS valor_unitario,
    TRIM(E.NFANTASIAFORN) AS fornecedor_nome,
    TRIM(TO_CHAR(E.NRFORN)) AS fornecedor_codigo,
    A.DATAMOVTO AS data_movto,
    B.QTDEITENSMOVTO AS quantidade
FROM GLOBUS.EST_MOVTO A
JOIN GLOBUS.EST_ITENSMOVTO B
  ON B.SEQMOVTO = A.SEQMOVTO
JOIN GLOBUS.EST_CADMATERIAL C
  ON C.CODIGOMATINT = B.CODIGOMATINT
LEFT JOIN GLOBUS.BGM_NOTAFISCAL F
  ON F.CODINTNF = A.CODINTNF
LEFT JOIN (
    SELECT CODINTNF, MAX(VALORUNITARIOITENSNF) AS VALORUNITARIOITENSNF
    FROM GLOBUS.EST_ITENSNF
    GROUP BY CODINTNF
) D ON D.CODINTNF = F.CODINTNF
LEFT JOIN GLOBUS.BGM_FORNECEDOR E
  ON E.CODIGOFORN = F.CODIGOFORN
WHERE A.CODIGOHISMOV IN (1, 10)
  AND A.CODIGOEMPRESA IN (1, 2, 3)
  AND C.CODIGOGRE = 01
  AND A.DATAMOVTO >= :data_ini
  AND A.DATAMOVTO < :data_fim_exclusive
ORDER BY A.DATAMOVTO DESC
FETCH FIRST {limite} ROWS ONLY
"""


def buscar_compras_recentes(
    *,
    data_ini: str | None = None,
    data_fim: str | None = None,
    limite: int = 10,
) -> list[dict[str, Any]]:
    """Últimas aquisições de peças no Globus (somente leitura)."""
    hoje = date.today()
    ini = _parse_date(data_ini, hoje - timedelta(days=30))
    fim = _parse_date(data_fim, hoje)
    if fim < ini:
        raise GlobusOracleError("data_fim deve ser maior ou igual a data_ini.")
    try:
        limite_n = max(1, min(int(limite or 10), 50))
    except (TypeError, ValueError):
        limite_n = 10
    sql = SQL_COMPRAS_RECENTES.format(limite=limite_n)
    client = GlobusOracleClient()
    rows = client.fetch_all(
        sql,
        {"data_ini": ini, "data_fim_exclusive": fim + timedelta(days=1)},
    )
    return [_serialize_row(r) for r in rows]


def buscar_compras_peca(
    peca: str,
    *,
    data_ini: str | None = None,
    data_fim: str | None = None,
    limite: int = 10,
) -> list[dict[str, Any]]:
    """Compras/aquisição de peças no Globus (somente leitura) — padrão do relatório interno."""
    peca = (peca or "").strip()
    if not peca:
        raise GlobusOracleError("Informe o código ou descrição da peça.")

    hoje = date.today()
    # histórico amplo para cruzar com garantia (compras podem ser anteriores ao ano da garantia)
    ini = _parse_date(data_ini, date(hoje.year - 5, 1, 1))
    fim = _parse_date(data_fim, hoje)
    if fim < ini:
        raise GlobusOracleError("data_fim deve ser maior ou igual a data_ini.")

    try:
        limite_n = max(1, min(int(limite or 10), 50))
    except (TypeError, ValueError):
        limite_n = 10

    digits = "".join(ch for ch in peca if ch.isdigit()) or peca
    sql = SQL_COMPRAS_PECA.format(limite=limite_n)
    client = GlobusOracleClient()
    rows = client.fetch_all(
        sql,
        {
            "data_ini": ini,
            "data_fim_exclusive": fim + timedelta(days=1),
            "peca": f"%{peca}%",
            "peca_digits": digits,
        },
    )
    return [_serialize_row(r) for r in rows]


def buscar_compras_por_codigos(
    codigos: list[str],
    *,
    data_ini: str | None = None,
    data_fim: str | None = None,
    limite_por_peca: int = 5,
) -> dict[str, list[dict[str, Any]]]:
    """Busca compras Globus para vários códigos (cache por código)."""
    out: dict[str, list[dict[str, Any]]] = {}
    seen: set[str] = set()
    for codigo in codigos:
        key = (codigo or "").strip()
        if not key or key.lower() in seen:
            continue
        seen.add(key.lower())
        try:
            out[key] = buscar_compras_peca(
                key,
                data_ini=data_ini,
                data_fim=data_fim,
                limite=limite_por_peca,
            )
        except GlobusOracleError:
            out[key] = []
        except Exception:
            out[key] = []
    return out
