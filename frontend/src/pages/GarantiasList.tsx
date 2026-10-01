import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { canCreateGarantia } from "../auth/permissions";
import BadgeStatus, { statusLabel } from "../components/BadgeStatus";

type CompraGlobus = {
  numero_nf?: string;
  serie_nf?: string;
  data_entrada_nf?: string;
  data_emissao_nf?: string;
  valor_unitario?: string | number;
  fornecedor_nome?: string;
};

type GarantiaRow = {
  id: number;
  protocolo: string;
  peca_nome: string;
  peca_codigo?: string;
  veiculo_codigo: string;
  fornecedor_nome: string;
  nf_remessa: string;
  nf_retorno: string;
  status: string;
  valor_peca: string | null;
  dias_aberta: number;
  ultima_compra_globus?: CompraGlobus | null;
  globus_ok?: boolean;
};

const CHIP_STATUSES = ["", "aberta", "em_analise", "improcedente", "procedente"] as const;
const MORE_STATUSES = ["enviada", "cortesia", "cancelada"] as const;

function money(v: string | number | null | undefined) {
  if (v === undefined || v === null || v === "") return "—";
  const n = Number(v);
  if (Number.isNaN(n)) return String(v);
  return n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function useDebounced(value: string, ms: number) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = window.setTimeout(() => setDebounced(value), ms);
    return () => window.clearTimeout(t);
  }, [value, ms]);
  return debounced;
}

function flagOn(v: string | null) {
  return v === "1" || v === "true";
}

export default function GarantiasList() {
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const anoAtual = new Date().getFullYear();
  const anos = useMemo(() => [anoAtual, anoAtual - 1, anoAtual - 2].map(String), [anoAtual]);

  const status = params.get("status") || "";
  const ano = params.get("ano") || String(anoAtual);
  const qParam = params.get("q") || "";
  const peca = params.get("peca") || "";
  const veiculo = params.get("veiculo") || "";
  const fornecedor = params.get("fornecedor") || "";
  const dataIni = params.get("data_ini") || "";
  const dataFim = params.get("data_fim") || "";
  const comNf = flagOn(params.get("com_nf_globus"));
  const semNf = flagOn(params.get("sem_nf_globus"));
  const parado45 = flagOn(params.get("parado_45"));
  const periodoAtivo = Boolean(dataIni || dataFim);

  const [qInput, setQInput] = useState(qParam);
  const qDebounced = useDebounced(qInput, 350);
  const [maisFiltros, setMaisFiltros] = useState(
    Boolean(peca || veiculo || fornecedor || dataIni || dataFim)
  );

  const [rows, setRows] = useState<GarantiaRow[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setQInput(qParam);
  }, [qParam]);

  useEffect(() => {
    const qNext = qDebounced.trim();
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        const qPrev = next.get("q") || "";
        const anoWasMissing = !next.get("ano") && !next.get("data_ini") && !next.get("data_fim");
        if (qNext) next.set("q", qNext);
        else next.delete("q");
        if (anoWasMissing) next.set("ano", String(anoAtual));
        if (qPrev === qNext && !anoWasMissing) return prev;
        return next;
      },
      { replace: true }
    );
  }, [qDebounced, anoAtual, setParams]);

  useEffect(() => {
    const qs = new URLSearchParams();
    if (status) qs.set("status", status);
    if (periodoAtivo) {
      if (dataIni) qs.set("data_ini", dataIni);
      if (dataFim) qs.set("data_fim", dataFim);
    } else if (ano) {
      qs.set("ano", ano);
    }
    if (qDebounced.trim()) qs.set("q", qDebounced.trim());
    if (peca) qs.set("peca", peca);
    if (veiculo) qs.set("veiculo", veiculo);
    if (fornecedor) qs.set("fornecedor", fornecedor);
    if (comNf) qs.set("com_nf_globus", "1");
    if (semNf) qs.set("sem_nf_globus", "1");
    if (parado45) qs.set("parado_45", "1");

    setLoading(true);
    setError("");
    api<GarantiaRow[]>(`/api/garantias/?${qs}`)
      .then(setRows)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Erro ao listar."))
      .finally(() => setLoading(false));
  }, [
    status,
    ano,
    qDebounced,
    peca,
    veiculo,
    fornecedor,
    dataIni,
    dataFim,
    periodoAtivo,
    comNf,
    semNf,
    parado45,
  ]);

  type Patch = {
    status?: string;
    ano?: string;
    q?: string;
    peca?: string;
    veiculo?: string;
    fornecedor?: string;
    data_ini?: string;
    data_fim?: string;
    com_nf_globus?: boolean;
    sem_nf_globus?: boolean;
    parado_45?: boolean;
    clear?: boolean;
  };

  function patchParams(patch: Patch) {
    if (patch.clear) {
      setQInput("");
      setMaisFiltros(false);
      setParams(new URLSearchParams({ ano: String(anoAtual) }), { replace: true });
      return;
    }
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        const setOrDel = (key: string, value?: string) => {
          if (value) next.set(key, value);
          else next.delete(key);
        };
        if (patch.status !== undefined) setOrDel("status", patch.status);
        if (patch.ano !== undefined) setOrDel("ano", patch.ano);
        if (patch.q !== undefined) setOrDel("q", patch.q);
        if (patch.peca !== undefined) setOrDel("peca", patch.peca);
        if (patch.veiculo !== undefined) setOrDel("veiculo", patch.veiculo);
        if (patch.fornecedor !== undefined) setOrDel("fornecedor", patch.fornecedor);
        if (patch.data_ini !== undefined) setOrDel("data_ini", patch.data_ini);
        if (patch.data_fim !== undefined) setOrDel("data_fim", patch.data_fim);

        if (patch.com_nf_globus !== undefined) {
          if (patch.com_nf_globus) {
            next.set("com_nf_globus", "1");
            next.delete("sem_nf_globus");
          } else next.delete("com_nf_globus");
        }
        if (patch.sem_nf_globus !== undefined) {
          if (patch.sem_nf_globus) {
            next.set("sem_nf_globus", "1");
            next.delete("com_nf_globus");
          } else next.delete("sem_nf_globus");
        }
        if (patch.parado_45 !== undefined) {
          if (patch.parado_45) next.set("parado_45", "1");
          else next.delete("parado_45");
        }

        const hasPeriodo = Boolean(next.get("data_ini") || next.get("data_fim"));
        if (hasPeriodo) next.delete("ano");
        else if (!next.get("ano")) next.set("ano", String(anoAtual));

        return next;
      },
      { replace: true }
    );
  }

  const isChipStatus = (CHIP_STATUSES as readonly string[]).includes(status);
  const moreSelectValue = !status || isChipStatus ? "" : status;

  function chipClass(active: boolean) {
    return `rounded-lg border px-3 py-1.5 text-sm transition ${
      active
        ? "border-cyan/50 bg-cyan/15 text-cyan"
        : "border-line bg-bg text-muted hover:border-cyan/30"
    }`;
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted">Filtre por status, período, peça ou atalhos Globus.</p>
        {canCreateGarantia(user?.perfil) ? (
          <Link
            to="/garantias/nova"
            className="rounded-lg bg-cyan px-4 py-2 text-sm font-semibold text-bg"
          >
            Nova garantia
          </Link>
        ) : null}
      </div>

      <div className="rounded-lg border border-line bg-panel/80 px-4 py-3 text-sm text-muted">
        Garantias são cadastro do RastroGlobus. Coluna <span className="text-cyan">NF compra Globus</span>{" "}
        vem do Oracle (leitura).
      </div>

      <div className="space-y-2 rounded-xl border border-line bg-panel p-3">
        <div className="flex flex-wrap items-center gap-2">
          {CHIP_STATUSES.map((s) => {
            const active = s === "" ? status === "" : status === s;
            return (
              <button
                key={s || "todos"}
                type="button"
                className={chipClass(active)}
                onClick={() => patchParams({ status: s })}
              >
                {s === "" ? "Todos" : statusLabel(s)}
              </button>
            );
          })}

          <select
            className="rounded-lg border border-line bg-bg px-2 py-1.5 text-sm"
            value={moreSelectValue}
            onChange={(e) => patchParams({ status: e.target.value })}
            title="Mais status"
          >
            <option value="">Mais status…</option>
            {MORE_STATUSES.map((s) => (
              <option key={s} value={s}>
                {statusLabel(s)}
              </option>
            ))}
          </select>

          <input
            className="min-w-[180px] flex-1 rounded-lg border border-line bg-bg px-3 py-1.5 text-sm"
            placeholder="Protocolo, peça, veículo, fornecedor…"
            value={qInput}
            onChange={(e) => setQInput(e.target.value)}
          />

          <select
            className="w-24 rounded-lg border border-line bg-bg px-2 py-1.5 text-sm disabled:opacity-50"
            value={ano}
            disabled={periodoAtivo}
            title={periodoAtivo ? "Ano desativado quando há período" : "Ano"}
            onChange={(e) => patchParams({ ano: e.target.value })}
          >
            {anos.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>

          <button
            type="button"
            className={chipClass(comNf)}
            onClick={() => patchParams({ com_nf_globus: !comNf, sem_nf_globus: false })}
          >
            Com NF Globus
          </button>
          <button
            type="button"
            className={chipClass(semNf)}
            onClick={() => patchParams({ sem_nf_globus: !semNf, com_nf_globus: false })}
          >
            Sem compra Globus
          </button>
          <button
            type="button"
            className={chipClass(parado45)}
            onClick={() => patchParams({ parado_45: !parado45 })}
          >
            Paradas +45d
          </button>

          <button
            type="button"
            className="rounded-lg border border-line px-3 py-1.5 text-sm text-muted"
            onClick={() => setMaisFiltros((v) => !v)}
          >
            {maisFiltros ? "Menos filtros" : "Mais filtros"}
          </button>
          <button
            type="button"
            className="rounded-lg border border-line px-3 py-1.5 text-sm text-muted"
            onClick={() => patchParams({ clear: true })}
          >
            Limpar
          </button>
        </div>

        {maisFiltros ? (
          <div className="grid gap-2 border-t border-line pt-3 md:grid-cols-3 lg:grid-cols-5">
            <input
              className="rounded-lg border border-line bg-bg px-3 py-1.5 text-sm"
              placeholder="Peça"
              value={peca}
              onChange={(e) => patchParams({ peca: e.target.value })}
            />
            <input
              className="rounded-lg border border-line bg-bg px-3 py-1.5 text-sm"
              placeholder="Veículo"
              value={veiculo}
              onChange={(e) => patchParams({ veiculo: e.target.value })}
            />
            <input
              className="rounded-lg border border-line bg-bg px-3 py-1.5 text-sm"
              placeholder="Fornecedor"
              value={fornecedor}
              onChange={(e) => patchParams({ fornecedor: e.target.value })}
            />
            <input
              type="date"
              className="rounded-lg border border-line bg-bg px-3 py-1.5 text-sm"
              value={dataIni}
              title="Data início"
              onChange={(e) => patchParams({ data_ini: e.target.value })}
            />
            <input
              type="date"
              className="rounded-lg border border-line bg-bg px-3 py-1.5 text-sm"
              value={dataFim}
              title="Data fim"
              onChange={(e) => patchParams({ data_fim: e.target.value })}
            />
          </div>
        ) : null}
      </div>

      {error ? <p className="text-red">{error}</p> : null}
      {loading ? <p className="text-muted">Carregando...</p> : null}

      <div className="overflow-x-auto rounded-xl border border-line bg-panel">
        <table className="w-full min-w-[1100px] text-left text-sm">
          <thead className="border-b border-line text-muted">
            <tr>
              <th className="px-3 py-3 font-medium">Protocolo</th>
              <th className="px-3 py-3 font-medium">Peça</th>
              <th className="px-3 py-3 font-medium">Veículo</th>
              <th className="px-3 py-3 font-medium">Fornecedor</th>
              <th className="px-3 py-3 font-medium">NF compra Globus</th>
              <th className="px-3 py-3 font-medium">Data / valor</th>
              <th className="px-3 py-3 font-medium">NF remessa</th>
              <th className="px-3 py-3 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const c = r.ultima_compra_globus;
              const dataNf = c?.data_entrada_nf || c?.data_emissao_nf;
              return (
                <tr key={r.id} className="border-t border-line hover:bg-bg/40">
                  <td className="px-3 py-3">
                    <Link className="text-cyan hover:underline" to={`/garantias/${r.id}`}>
                      {r.protocolo}
                    </Link>
                  </td>
                  <td className="px-3 py-3">{r.peca_nome}</td>
                  <td className="px-3 py-3">{r.veiculo_codigo}</td>
                  <td className="px-3 py-3">{r.fornecedor_nome}</td>
                  <td className="px-3 py-3">
                    {c?.numero_nf ? (
                      <div>
                        <div>
                          {c.numero_nf}
                          {c.serie_nf ? ` / ${c.serie_nf}` : ""}
                        </div>
                        <div className="text-xs text-muted">{c.fornecedor_nome || ""}</div>
                      </div>
                    ) : (
                      <span className="text-muted">
                        {r.globus_ok === false ? "Globus offline" : "Sem compra"}
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-3 whitespace-nowrap text-xs text-muted">
                    {dataNf ? String(dataNf).slice(0, 10) : "—"}
                    <br />
                    {money(c?.valor_unitario ?? r.valor_peca)}
                  </td>
                  <td className="px-3 py-3">{r.nf_remessa || "—"}</td>
                  <td className="px-3 py-3">
                    <BadgeStatus status={r.status} />
                  </td>
                </tr>
              );
            })}
            {!loading && !rows.length ? (
              <tr>
                <td colSpan={8} className="px-3 py-6 text-center text-muted">
                  Nenhuma garantia encontrada.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}
