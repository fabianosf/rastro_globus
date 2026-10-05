import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { canCreateGarantia, canDeleteGarantia, canEditGarantia } from "../auth/permissions";
import BadgeStatus, { statusLabel } from "../components/BadgeStatus";

type GarantiaRow = {
  id: number;
  protocolo: string;
  peca_nome: string;
  peca_codigo?: string;
  veiculo_codigo: string;
  fornecedor_nome: string;
  nf_remessa: string;
  status: string;
  valor_peca: string | null;
};

const STATUS_OPTS = [
  { value: "", label: "Todos" },
  { value: "abertos", label: "Abertos" },
  { value: "enviada", label: "Enviada" },
  { value: "em_analise", label: "Em análise" },
  { value: "improcedente", label: "Improcedente" },
  { value: "procedente", label: "Procedente" },
] as const;

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

/** Compara queries ignorando ordem das chaves. */
function sameQuery(a: URLSearchParams, b: URLSearchParams) {
  const ka = [...a.keys()].sort();
  const kb = [...b.keys()].sort();
  if (ka.length !== kb.length) return false;
  for (let i = 0; i < ka.length; i += 1) {
    if (ka[i] !== kb[i]) return false;
    if ((a.get(ka[i]) || "") !== (b.get(kb[i]) || "")) return false;
  }
  return true;
}

export default function GarantiasList() {
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const anoAtual = new Date().getFullYear();
  const anos = useMemo(
    () => [anoAtual, anoAtual - 1, anoAtual - 2, anoAtual - 3].map(String),
    [anoAtual]
  );

  const paramsKey = params.toString();
  const statusExplicit = params.has("status");
  const status = statusExplicit ? params.get("status") || "" : "abertos";
  const ano = params.get("ano") || String(anoAtual);
  const qParam = params.get("q") || "";
  const dataIni = params.get("data_ini") || "";
  const dataFim = params.get("data_fim") || "";
  const periodoAtivo = Boolean(dataIni || dataFim);

  const [qInput, setQInput] = useState(qParam);
  const qDebounced = useDebounced(qInput, 350);
  const settled = qInput === qDebounced;

  const [rows, setRows] = useState<GarantiaRow[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const fetchGen = useRef(0);

  // URL → input só quando debounce está quieto (evita luta com digitação).
  useEffect(() => {
    if (!settled) return;
    if (qParam === qInput) return;
    setQInput(qParam);
  }, [qParam, qInput, settled]);

  // Um único escritor de URL: defaults + q debounced.
  useEffect(() => {
    const next = new URLSearchParams(paramsKey);
    // Reparse from paramsKey to avoid stale object identity issues
    const current = new URLSearchParams(paramsKey);

    if (!current.get("data_ini") && !current.get("data_fim") && !current.get("ano")) {
      next.set("ano", String(anoAtual));
    }
    if (!current.has("status")) {
      next.set("status", "abertos");
    }

    if (settled) {
      const qNext = qDebounced.trim();
      if (qNext) next.set("q", qNext);
      else next.delete("q");
    }

    if (sameQuery(current, next)) return;
    setParams(next, { replace: true });
  }, [paramsKey, qDebounced, settled, anoAtual, setParams]);

  useEffect(() => {
    const qs = new URLSearchParams();
    if (status) qs.set("status", status);
    if (periodoAtivo) {
      if (dataIni) qs.set("data_ini", dataIni);
      if (dataFim) qs.set("data_fim", dataFim);
    } else {
      qs.set("ano", ano || String(anoAtual));
    }
    if (qParam.trim()) qs.set("q", qParam.trim());

    const gen = ++fetchGen.current;
    setLoading(true);
    setError("");
    api<GarantiaRow[]>(`/api/garantias/?${qs}`)
      .then((data) => {
        if (gen !== fetchGen.current) return;
        setRows(Array.isArray(data) ? data : []);
      })
      .catch((e) => {
        if (gen !== fetchGen.current) return;
        setError(e instanceof ApiError ? e.message : "Erro ao listar.");
        setRows([]);
      })
      .finally(() => {
        if (gen !== fetchGen.current) return;
        setLoading(false);
      });
  }, [status, ano, qParam, dataIni, dataFim, periodoAtivo, anoAtual]);

  async function excluir(row: GarantiaRow) {
    if (!canDeleteGarantia(user?.perfil, row.status)) return;
    const ok = window.confirm(
      `Excluir ${row.protocolo}${row.nf_remessa ? ` (NF ${row.nf_remessa})` : ""}? Esta ação não tem volta.`
    );
    if (!ok) return;
    setDeletingId(row.id);
    setError("");
    try {
      await api(`/api/garantias/${row.id}/`, { method: "DELETE" });
      setRows((prev) => prev.filter((r) => r.id !== row.id));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Erro ao excluir.");
    } finally {
      setDeletingId(null);
    }
  }

  function patchUrl(patch: {
    status?: string;
    ano?: string;
    data_ini?: string;
    data_fim?: string;
  }) {
    const next = new URLSearchParams(params);
    if (patch.status !== undefined) {
      next.set("status", patch.status);
    }
    if (patch.ano !== undefined) {
      next.set("ano", patch.ano);
      next.delete("data_ini");
      next.delete("data_fim");
    }
    if (patch.data_ini !== undefined) {
      if (patch.data_ini) next.set("data_ini", patch.data_ini);
      else next.delete("data_ini");
    }
    if (patch.data_fim !== undefined) {
      if (patch.data_fim) next.set("data_fim", patch.data_fim);
      else next.delete("data_fim");
    }
    if (next.get("data_ini") || next.get("data_fim")) next.delete("ano");
    else if (!next.get("ano")) next.set("ano", String(anoAtual));
    if (sameQuery(params, next)) return;
    setParams(next, { replace: true });
  }

  function limpar() {
    setQInput("");
    const next = new URLSearchParams({ ano: String(anoAtual), status: "abertos" });
    setParams(next, { replace: true });
  }

  const statusEmptyLabel =
    status === "abertos" ? "abertos" : status ? statusLabel(status) : "";
  const periodoLabel = periodoAtivo
    ? `${dataIni || "…"} → ${dataFim || "…"}`
    : `ano ${ano || anoAtual}`;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm text-muted">NFs que você cadastrou no SGGI · {periodoLabel}</p>
          <p className="text-xs text-muted">Edite ou exclua se errou.</p>
        </div>
        {canCreateGarantia(user?.perfil) ? (
          <Link
            to="/garantias/nova-danfe"
            className="rounded-lg bg-cyan px-4 py-2 text-sm font-semibold text-bg"
          >
            Registrar DANFE
          </Link>
        ) : null}
      </div>

      <div className="flex flex-wrap items-center gap-2 rounded-xl border border-line bg-panel p-3">
        <input
          className="min-w-[180px] flex-1 rounded-lg border border-line bg-bg px-3 py-1.5 text-sm"
          placeholder="Protocolo, NF, peça, CARRO, fornecedor…"
          value={qInput}
          onChange={(e) => setQInput(e.target.value)}
        />
        <select
          className="w-24 rounded-lg border border-line bg-bg px-2 py-1.5 text-sm disabled:opacity-50"
          value={anos.includes(ano) ? ano : String(anoAtual)}
          disabled={periodoAtivo}
          title={periodoAtivo ? "Ano desativado quando há período" : "Ano"}
          onChange={(e) => patchUrl({ ano: e.target.value })}
        >
          {anos.map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </select>
        <select
          className="rounded-lg border border-line bg-bg px-2 py-1.5 text-sm"
          value={STATUS_OPTS.some((o) => o.value === status) ? status : ""}
          title="Status"
          onChange={(e) => patchUrl({ status: e.target.value })}
        >
          {STATUS_OPTS.map((o) => (
            <option key={o.value || "todos"} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <label className="flex items-center gap-1 text-xs text-muted">
          De
          <input
            type="date"
            className="rounded-lg border border-line bg-bg px-2 py-1.5 text-sm text-ink"
            value={dataIni}
            onChange={(e) => patchUrl({ data_ini: e.target.value })}
          />
        </label>
        <label className="flex items-center gap-1 text-xs text-muted">
          Até
          <input
            type="date"
            className="rounded-lg border border-line bg-bg px-2 py-1.5 text-sm text-ink"
            value={dataFim}
            onChange={(e) => patchUrl({ data_fim: e.target.value })}
          />
        </label>
        <button
          type="button"
          className="rounded-lg border border-line px-3 py-1.5 text-sm text-muted"
          onClick={limpar}
        >
          Limpar
        </button>
      </div>

      {error ? <p className="text-red">{error}</p> : null}
      {loading ? <p className="text-muted">Carregando...</p> : null}

      <div className="overflow-x-auto rounded-xl border border-line bg-panel">
        <table className="w-full min-w-[800px] text-left text-sm">
          <thead className="border-b border-line text-muted">
            <tr>
              <th className="px-3 py-3 font-medium">Protocolo</th>
              <th className="px-3 py-3 font-medium">NF remessa</th>
              <th className="px-3 py-3 font-medium">Peça</th>
              <th className="px-3 py-3 font-medium">CARRO</th>
              <th className="px-3 py-3 font-medium">Fornecedor</th>
              <th className="px-3 py-3 font-medium">Valor</th>
              <th className="px-3 py-3 font-medium">Status</th>
              <th className="px-3 py-3 font-medium">Ações</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const podeEditar =
                canEditGarantia(user?.perfil) &&
                ["aberta", "enviada", "em_analise"].includes(r.status);
              const podeExcluir = canDeleteGarantia(user?.perfil, r.status);
              return (
                <tr key={r.id} className="border-t border-line hover:bg-bg/40">
                  <td className="px-3 py-3">
                    <Link className="text-cyan hover:underline" to={`/garantias/${r.id}`}>
                      {r.protocolo}
                    </Link>
                  </td>
                  <td className="px-3 py-3">{r.nf_remessa || "—"}</td>
                  <td className="px-3 py-3">{r.peca_nome}</td>
                  <td className="px-3 py-3">{r.veiculo_codigo}</td>
                  <td className="px-3 py-3">{r.fornecedor_nome}</td>
                  <td className="px-3 py-3 whitespace-nowrap text-xs">{money(r.valor_peca)}</td>
                  <td className="px-3 py-3">
                    <BadgeStatus status={r.status} />
                  </td>
                  <td className="px-3 py-3">
                    <div className="flex flex-wrap gap-2">
                      <Link
                        to={`/garantias/${r.id}`}
                        className="text-xs text-cyan hover:underline"
                      >
                        {podeEditar ? "Editar" : "Ver"}
                      </Link>
                      {podeExcluir ? (
                        <button
                          type="button"
                          disabled={deletingId === r.id}
                          onClick={() => void excluir(r)}
                          className="text-xs text-red hover:underline disabled:opacity-50"
                        >
                          {deletingId === r.id ? "…" : "Excluir"}
                        </button>
                      ) : null}
                    </div>
                  </td>
                </tr>
              );
            })}
            {!loading && !rows.length ? (
              <tr>
                <td colSpan={8} className="px-3 py-6 text-center text-muted">
                  Nenhuma NF cadastrada
                  {statusEmptyLabel ? ` com status “${statusEmptyLabel}”` : ""}
                  {` em ${periodoLabel}`}. Use Registrar DANFE.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}
