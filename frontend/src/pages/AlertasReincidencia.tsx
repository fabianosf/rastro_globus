import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { canCreateGarantia } from "../auth/permissions";

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
  { v: "em_analise", l: "Em analise" },
  { v: "garantia_aberta", l: "Garantia aberta" },
  { v: "descartado", l: "Descartado" },
];

function money(v: string | number | null | undefined) {
  if (v === undefined || v === null || v === "") return "—";
  const n = Number(v);
  if (Number.isNaN(n)) return String(v);
  return n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
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

  function load() {
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
  }

  useEffect(() => {
    load();
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
      navigate(`/garantias/${g.id}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Falha ao abrir garantia.");
    } finally {
      setBusyId(null);
    }
  }

  async function descartar(id: number) {
    const motivo = window.prompt("Motivo do descarte:");
    if (!motivo || !motivo.trim()) return;
    setBusyId(id);
    setError("");
    try {
      await api(`/api/alertas-reincidencia/${id}/descartar/`, {
        method: "POST",
        body: { motivo_descarte: motivo.trim() },
      });
      load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Falha ao descartar.");
    } finally {
      setBusyId(null);
    }
  }

  const field =
    "rounded-lg border border-line bg-bg px-3 py-2 text-sm outline-none focus:border-cyan";

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted">
        Alertas gerados por <code className="text-xs">detectar_reincidencia</code> apos sync de
        saidas Globus. Nao movimenta estoque.
      </p>

      <div className="flex flex-wrap items-end gap-3">
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
          <span className="mb-1 block text-muted">Peca</span>
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
          onClick={load}
          className="rounded-lg bg-cyan/20 px-3 py-2 text-sm text-cyan"
        >
          Filtrar
        </button>
      </div>

      {error ? <p className="text-sm text-red">{error}</p> : null}
      {loading ? <p className="text-muted">Carregando...</p> : null}

      <div className="overflow-x-auto rounded-xl border border-line bg-panel">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-line text-muted">
            <tr>
              <th className="px-3 py-2">Veiculo</th>
              <th className="px-3 py-2">Peca</th>
              <th className="px-3 py-2">Datas</th>
              <th className="px-3 py-2">Dias</th>
              <th className="px-3 py-2">Fornecedor / NF</th>
              <th className="px-3 py-2">Valor</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Acoes</th>
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
                <td className="px-3 py-2">{a.dias_entre}</td>
                <td className="px-3 py-2">
                  <div>{a.fornecedor_1 || "—"}</div>
                  <div className="text-xs text-muted">NF {a.nf_1 || "—"}</div>
                </td>
                <td className="px-3 py-2">{money(a.valor_estimado)}</td>
                <td className="px-3 py-2">{a.status}</td>
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
                    <Link to="/garantias" className="block text-xs text-muted hover:underline">
                      Ver garantias
                    </Link>
                  ) : null}
                  {a.status !== "descartado" && a.status !== "garantia_aberta" ? (
                    <button
                      type="button"
                      disabled={busyId === a.id}
                      onClick={() => descartar(a.id)}
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
                <td colSpan={8} className="px-3 py-6 text-center text-muted">
                  Nenhum alerta.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}
