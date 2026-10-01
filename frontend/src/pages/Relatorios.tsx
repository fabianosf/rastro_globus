import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError, getToken } from "../api/client";
import { statusLabel } from "../components/BadgeStatus";
import GlobusStatusBadge from "../components/GlobusStatusBadge";
import KpiCard from "../components/KpiCard";

type Resumo = {
  ano: number;
  contagem_status: Record<string, number>;
  valor_procedente: string;
  valor_improcedente: string;
  valor_aberto: string;
};

type CompraGlobus = {
  numero_nf?: string;
  serie_nf?: string;
  data_entrada_nf?: string;
  data_emissao_nf?: string;
  valor_unitario?: string | number;
  valor_total_nf?: string | number;
  fornecedor_nome?: string;
  peca_codigo?: string;
};

type ImprocedenteRow = {
  id: number;
  protocolo: string;
  peca_codigo: string;
  peca_nome: string;
  veiculo_codigo: string;
  fornecedor_nome: string;
  valor_peca: string | null;
  motivo_improcedente: string;
  nf_compra_rg: string;
  ultima_compra_globus: CompraGlobus | null;
  compras_globus: CompraGlobus[];
};

type ImprocedentesPayload = {
  ano: number;
  count: number;
  results: ImprocedenteRow[];
  globus_ok: boolean;
  globus_detail: string;
  aviso: string;
};

function money(v: string | number | null | undefined) {
  if (v === undefined || v === null || v === "") return "—";
  const n = Number(v);
  if (Number.isNaN(n)) return String(v);
  return n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export default function Relatorios() {
  const [ano, setAno] = useState(String(new Date().getFullYear()));
  const [pecaFiltro, setPecaFiltro] = useState("");
  const [data, setData] = useState<Resumo | null>(null);
  const [cruzamento, setCruzamento] = useState<ImprocedentesPayload | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadingCruz, setLoadingCruz] = useState(true);

  useEffect(() => {
    setLoading(true);
    api<Resumo>(`/api/relatorios/resumo/?ano=${ano}`)
      .then(setData)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Erro ao carregar relatório."))
      .finally(() => setLoading(false));
  }, [ano]);

  useEffect(() => {
    setLoadingCruz(true);
    const q = new URLSearchParams({ ano });
    if (pecaFiltro.trim()) q.set("peca", pecaFiltro.trim());
    api<ImprocedentesPayload>(`/api/relatorios/improcedentes-compras/?${q}`)
      .then(setCruzamento)
      .catch(() =>
        setCruzamento({
          ano: Number(ano),
          count: 0,
          results: [],
          globus_ok: false,
          globus_detail: "Falha ao carregar cruzamento.",
          aviso: "",
        })
      )
      .finally(() => setLoadingCruz(false));
  }, [ano, pecaFiltro]);

  async function exportCsv() {
    setError("");
    try {
      const token = getToken();
      const res = await fetch(`/api/relatorios/export.csv/?ano=${ano}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error("Falha no export.");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `garantias-${ano}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setError("Não foi possível baixar o CSV.");
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <label className="text-sm text-muted">Ano</label>
          <input
            className="w-28 rounded-lg border border-line bg-panel px-3 py-2 text-sm"
            value={ano}
            onChange={(e) => setAno(e.target.value)}
          />
          <GlobusStatusBadge />
        </div>
        <button
          type="button"
          onClick={exportCsv}
          className="rounded-lg bg-cyan px-4 py-2 text-sm font-semibold text-bg"
        >
          Exportar CSV
        </button>
      </div>

      {error ? <p className="text-red">{error}</p> : null}
      {loading ? <p className="text-muted">Carregando...</p> : null}

      {data ? (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <KpiCard title="Valor procedente" value={money(data.valor_procedente)} accent="green" />
            <KpiCard title="Valor improcedente" value={money(data.valor_improcedente)} accent="red" />
            <KpiCard title="Valor em aberto" value={money(data.valor_aberto)} accent="amber" />
          </div>

          <section className="overflow-x-auto rounded-xl border border-line bg-panel">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-line text-muted">
                <tr>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Quantidade</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(data.contagem_status).map(([status, total]) => (
                  <tr key={status} className="border-t border-line">
                    <td className="px-4 py-3">{statusLabel(status)}</td>
                    <td className="px-4 py-3">{total}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      ) : null}

      <section className="space-y-3">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="font-semibold">Improcedentes × compras Globus</h2>
            <p className="text-xs text-muted">
              Improcedente vem do RastroGlobus. Compras vêm do Globus (leitura). Estoque continua no
              Globo.
            </p>
          </div>
          <input
            className="w-56 rounded-lg border border-line bg-panel px-3 py-2 text-sm"
            placeholder="Filtrar peça..."
            value={pecaFiltro}
            onChange={(e) => setPecaFiltro(e.target.value)}
          />
        </div>

        <div className="rounded-lg border border-amber/40 bg-amber/10 px-4 py-3 text-sm text-amber">
          {cruzamento?.aviso ||
            "Consulta somente leitura. Improcedente não é status do estoque Globus."}
          {cruzamento && !cruzamento.globus_ok ? (
            <span className="mt-1 block text-xs">
              Globus: {cruzamento.globus_detail || "compras indisponíveis"}
            </span>
          ) : null}
        </div>

        {loadingCruz ? <p className="text-sm text-muted">Carregando cruzamento...</p> : null}

        <div className="overflow-x-auto rounded-xl border border-line bg-panel">
          <table className="w-full min-w-[960px] text-left text-sm">
            <thead className="border-b border-line text-muted">
              <tr>
                <th className="px-3 py-3 font-medium">Protocolo</th>
                <th className="px-3 py-3 font-medium">Peça</th>
                <th className="px-3 py-3 font-medium">Veículo</th>
                <th className="px-3 py-3 font-medium">Motivo</th>
                <th className="px-3 py-3 font-medium">NF compra Globus</th>
                <th className="px-3 py-3 font-medium">Data</th>
                <th className="px-3 py-3 font-medium">Valor</th>
                <th className="px-3 py-3 font-medium">Links</th>
              </tr>
            </thead>
            <tbody>
              {(cruzamento?.results || []).map((r) => {
                const c = r.ultima_compra_globus;
                const dataNf = c?.data_entrada_nf || c?.data_emissao_nf;
                return (
                  <tr key={r.id} className="border-t border-line">
                    <td className="px-3 py-2">
                      <Link className="text-cyan hover:underline" to={`/garantias/${r.id}`}>
                        {r.protocolo}
                      </Link>
                    </td>
                    <td className="px-3 py-2">
                      <div>{r.peca_nome}</div>
                      <div className="text-xs text-muted">{r.fornecedor_nome}</div>
                    </td>
                    <td className="px-3 py-2">{r.veiculo_codigo}</td>
                    <td className="px-3 py-2 max-w-[200px] text-xs text-muted">
                      {r.motivo_improcedente || "—"}
                    </td>
                    <td className="px-3 py-2">
                      {c?.numero_nf ? (
                        <div>
                          <div>{c.numero_nf}{c.serie_nf ? ` / ${c.serie_nf}` : ""}</div>
                          <div className="text-xs text-muted">{c.fornecedor_nome || ""}</div>
                        </div>
                      ) : (
                        <span className="text-muted">
                          {cruzamento?.globus_ok ? "Sem compra no período" : "—"}
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap">
                      {dataNf ? String(dataNf).slice(0, 10) : "—"}
                    </td>
                    <td className="px-3 py-2">
                      {money(c?.valor_unitario ?? c?.valor_total_nf ?? r.valor_peca)}
                    </td>
                    <td className="px-3 py-2 text-xs">
                      <Link
                        className="text-cyan hover:underline"
                        to={`/movimentos-globus?peca=${encodeURIComponent(r.peca_codigo)}&tipo=compras`}
                      >
                        Compras
                      </Link>
                    </td>
                  </tr>
                );
              })}
              {!loadingCruz && !(cruzamento?.results || []).length ? (
                <tr>
                  <td colSpan={8} className="px-3 py-6 text-center text-muted">
                    Nenhuma garantia improcedente no ano {ano}.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
