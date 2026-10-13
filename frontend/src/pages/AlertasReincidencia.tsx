import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { canCreateGarantia } from "../auth/permissions";
import KpiCard from "../components/KpiCard";

type Alerta = {
  id: number;
  veiculo_codigo: string;
  peca_codigo: string;
  peca_descricao: string;
  empresa: string;
  data_1: string;
  data_2: string;
  dias_entre: number;
  fornecedor_1: string;
  nf_1: string;
  valor_estimado: string | null;
  status: string;
  motivo_descarte: string;
};

const STATUS_OPTS = [
  { v: "", l: "Todos" },
  { v: "novo", l: "Novo" },
  { v: "em_analise", l: "Em análise" },
  { v: "garantia_aberta", l: "Garantia aberta" },
  { v: "descartado", l: "Descartado" },
];

function money(v: string | number | null | undefined) {
  if (v === undefined || v === null || v === "") return "—";
  const n = Number(v);
  if (Number.isNaN(n)) return String(v);
  return n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function statusLabel(s: string) {
  return STATUS_OPTS.find((o) => o.v === s)?.l || s;
}

export default function AlertasReincidencia() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [rows, setRows] = useState<Alerta[]>([]);
  const [status, setStatus] = useState("novo");
  const [peca, setPeca] = useState("");
  const [fornecedor, setFornecedor] = useState("");
  const [empresa, setEmpresa] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);

  const [kpiNovos, setKpiNovos] = useState(0);
  const [kpiAbertas, setKpiAbertas] = useState(0);
  const [kpiValorNovos, setKpiValorNovos] = useState(0);

  const [discardId, setDiscardId] = useState<number | null>(null);
  const [discardMotivo, setDiscardMotivo] = useState("");
  const [discardError, setDiscardError] = useState("");

  const loadKpis = useCallback(() => {
    Promise.all([
      api<{ count: number }>("/api/alertas-reincidencia/novos-count/"),
      api<Alerta[]>("/api/alertas-reincidencia/?status=garantia_aberta"),
      api<Alerta[]>("/api/alertas-reincidencia/?status=novo"),
    ])
      .then(([novos, abertas, listaNovos]) => {
        setKpiNovos(novos.count);
        setKpiAbertas(abertas.length);
        const soma = listaNovos.reduce((acc, a) => acc + (Number(a.valor_estimado) || 0), 0);
        setKpiValorNovos(soma);
      })
      .catch(() => {
        /* KPIs não bloqueiam a lista */
      });
  }, []);

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    const q = new URLSearchParams();
    if (status) q.set("status", status);
    if (peca.trim()) q.set("peca", peca.trim());
    if (fornecedor.trim()) q.set("fornecedor", fornecedor.trim());
    if (empresa.trim()) q.set("empresa", empresa.trim());
    api<Alerta[]>(`/api/alertas-reincidencia/?${q}`)
      .then(setRows)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Erro ao carregar alertas."))
      .finally(() => setLoading(false));
  }, [status, peca, fornecedor, empresa]);

  useEffect(() => {
    load();
    loadKpis();
    // Recarrega ao mudar status; peça/fornecedor/empresa usam o botão Filtrar.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  async function abrirGarantia(id: number) {
    setBusyId(id);
    setError("");
    try {
      const g = await api<{ id: number }>(`/api/alertas-reincidencia/${id}/abrir-garantia/`, {
        method: "POST",
        body: {},
      });
      loadKpis();
      navigate(`/garantias/${g.id}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Falha ao abrir garantia.");
    } finally {
      setBusyId(null);
    }
  }

  function abrirModalDescarte(id: number) {
    setDiscardId(id);
    setDiscardMotivo("");
    setDiscardError("");
  }

  function fecharModalDescarte() {
    setDiscardId(null);
    setDiscardMotivo("");
    setDiscardError("");
  }

  async function confirmarDescarte(e: FormEvent) {
    e.preventDefault();
    if (!discardId) return;
    const motivo = discardMotivo.trim();
    if (!motivo) {
      setDiscardError("Informe o motivo do descarte.");
      return;
    }
    setBusyId(discardId);
    setDiscardError("");
    setError("");
    try {
      await api(`/api/alertas-reincidencia/${discardId}/descartar/`, {
        method: "POST",
        body: { motivo_descarte: motivo },
      });
      fecharModalDescarte();
      load();
      loadKpis();
    } catch (err) {
      setDiscardError(err instanceof ApiError ? err.message : "Falha ao descartar.");
    } finally {
      setBusyId(null);
    }
  }

  const field =
    "rounded-lg border border-line bg-bg px-3 py-2 text-sm outline-none focus:border-cyan";

  return (
    <div className="space-y-4">
      <div>
        <p className="text-sm text-muted">
          Mesma peça no mesmo veículo dentro do prazo de garantia. Não movimenta estoque.
        </p>
        <p className="text-xs text-muted">
          Os alertas são gerados após o sync do Globus (comando detectar_reincidencia).
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <KpiCard title="Alertas novos" value={kpiNovos} accent="amber" />
        <KpiCard
          title="Garantias abertas a partir de alertas"
          value={kpiAbertas}
          accent="cyan"
        />
        <KpiCard
          title="Valor estimado (novos)"
          value={money(kpiValorNovos)}
          accent="green"
        />
      </div>

      <div className="flex flex-wrap items-end gap-3 rounded-xl border border-line bg-panel p-3">
        <label className="text-sm">
          <span className="mb-1 block text-muted">Status</span>
          <select className={field} value={status} onChange={(e) => setStatus(e.target.value)}>
            {STATUS_OPTS.map((o) => (
              <option key={o.v || "all"} value={o.v}>
                {o.l}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-muted">Peça</span>
          <input className={field} value={peca} onChange={(e) => setPeca(e.target.value)} />
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-muted">Fornecedor</span>
          <input
            className={field}
            value={fornecedor}
            onChange={(e) => setFornecedor(e.target.value)}
          />
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-muted">Empresa</span>
          <input className={field} value={empresa} onChange={(e) => setEmpresa(e.target.value)} />
        </label>
        <button
          type="button"
          onClick={() => {
            load();
            loadKpis();
          }}
          className="rounded-lg bg-cyan/20 px-3 py-2 text-sm text-cyan"
        >
          Filtrar
        </button>
      </div>

      {error ? <p className="text-sm text-red">{error}</p> : null}
      {loading ? <p className="text-muted">Carregando…</p> : null}

      <div className="overflow-x-auto rounded-xl border border-line bg-panel">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-line text-muted">
            <tr>
              <th className="px-3 py-2">Veículo</th>
              <th className="px-3 py-2">Peça</th>
              <th className="px-3 py-2">Datas</th>
              <th className="px-3 py-2">Dias entre aplicações</th>
              <th className="px-3 py-2">Fornecedor / NF</th>
              <th className="px-3 py-2">Valor</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Ações</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((a) => (
              <tr key={a.id} className="border-t border-line">
                <td className="px-3 py-2">
                  <div>{a.veiculo_codigo}</div>
                  <div className="text-xs text-muted">{a.empresa || "—"}</div>
                </td>
                <td className="px-3 py-2">
                  <div className="font-medium">{a.peca_codigo}</div>
                  <div className="text-xs text-muted">{a.peca_descricao}</div>
                </td>
                <td className="px-3 py-2 whitespace-nowrap text-xs">
                  {a.data_1} → {a.data_2}
                </td>
                <td
                  className={`px-3 py-2 font-medium ${
                    a.dias_entre <= 30 ? "text-red" : "text-text"
                  }`}
                >
                  {a.dias_entre}
                </td>
                <td className="px-3 py-2">
                  <div>{a.fornecedor_1 || "—"}</div>
                  <div className="text-xs text-muted">NF {a.nf_1 || "—"}</div>
                </td>
                <td className="px-3 py-2">{money(a.valor_estimado)}</td>
                <td className="px-3 py-2">{statusLabel(a.status)}</td>
                <td className="px-3 py-2 space-y-1">
                  {canCreateGarantia(user?.perfil) &&
                  a.status !== "descartado" &&
                  a.status !== "garantia_aberta" ? (
                    <button
                      type="button"
                      disabled={busyId === a.id}
                      onClick={() => abrirGarantia(a.id)}
                      className="block text-xs text-cyan hover:underline disabled:opacity-50"
                    >
                      Abrir garantia
                    </button>
                  ) : null}
                  {a.status === "garantia_aberta" ? (
                    <Link to="/" className="block text-xs text-muted hover:underline">
                      Ver garantias
                    </Link>
                  ) : null}
                  {a.status !== "descartado" && a.status !== "garantia_aberta" ? (
                    <button
                      type="button"
                      disabled={busyId === a.id}
                      onClick={() => abrirModalDescarte(a.id)}
                      className="block text-xs text-amber hover:underline disabled:opacity-50"
                    >
                      Descartar
                    </button>
                  ) : null}
                </td>
              </tr>
            ))}
            {!loading && !rows.length ? (
              <tr>
                <td colSpan={8} className="px-3 py-8 text-center text-muted">
                  Nenhuma reincidência. Os alertas são gerados após o sync do Globus.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      {discardId !== null ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <form
            onSubmit={confirmarDescarte}
            className="w-full max-w-md space-y-4 rounded-xl border border-line bg-panel p-6 shadow-xl"
          >
            <h2 className="text-lg font-semibold text-text">Descartar alerta</h2>
            <p className="text-sm text-muted">Informe o motivo (obrigatório).</p>
            <textarea
              className={`${field} min-h-[100px] w-full`}
              value={discardMotivo}
              onChange={(e) => setDiscardMotivo(e.target.value)}
              placeholder="Motivo do descarte"
              autoFocus
              required
            />
            {discardError ? <p className="text-sm text-red">{discardError}</p> : null}
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={fecharModalDescarte}
                className="rounded-lg border border-line px-3 py-2 text-sm text-muted"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={busyId === discardId}
                className="rounded-lg bg-amber/20 px-3 py-2 text-sm font-medium text-amber disabled:opacity-50"
              >
                Confirmar descarte
              </button>
            </div>
          </form>
        </div>
      ) : null}
    </div>
  );
}
