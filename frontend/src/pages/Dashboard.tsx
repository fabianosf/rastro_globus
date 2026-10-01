import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import BadgeStatus from "../components/BadgeStatus";
import GlobusStatusBadge from "../components/GlobusStatusBadge";
import KpiCard from "../components/KpiCard";

type MovRow = {
  data_movto?: string;
  tipo_movimento?: string;
  peca_codigo?: string;
  peca_descricao?: string;
  quantidade?: string | number;
  numero_nf?: string;
  veiculo_codigo?: string;
};

type CompraRow = {
  data_entrada_nf?: string;
  data_emissao_nf?: string;
  data_movto?: string;
  numero_nf?: string;
  peca_codigo?: string;
  peca_descricao?: string;
  valor_unitario?: string | number;
  fornecedor_nome?: string;
};

type DashboardData = {
  ano: number;
  contagem_status: Record<string, number>;
  valor_procedente: string;
  valor_improcedente: string;
  valor_aberto: string;
  ranking_pecas: Array<{
    peca_id: number;
    codigo: string;
    descricao: string;
    total: number;
    valor: string;
  }>;
  veiculos_alerta: Array<{
    veiculo_id: number;
    codigo: string;
    casa: string;
    total: number;
  }>;
  parados_45_dias: Array<{
    id: number;
    protocolo: string;
    status: string;
    peca: string;
    veiculo: string;
  }>;
  globus?: {
    ok: boolean;
    detail: string;
    movimentos_recentes: MovRow[];
    compras_recentes: CompraRow[];
    aviso?: string;
  };
};

function money(v: string | number | undefined) {
  if (v === undefined || v === null || v === "") return "—";
  const n = Number(v);
  if (Number.isNaN(n)) return String(v);
  return n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function sliceDate(v?: string) {
  return v ? String(v).slice(0, 10) : "—";
}

export default function Dashboard() {
  const ano = new Date().getFullYear();
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api<DashboardData>(`/api/dashboard/?ano=${ano}`)
      .then(setData)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Erro ao carregar dashboard."))
      .finally(() => setLoading(false));
  }, [ano]);

  if (loading) return <p className="text-muted">Carregando dashboard...</p>;
  if (error) return <p className="text-red">{error}</p>;
  if (!data) return null;

  const c = data.contagem_status;
  const g = data.globus;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm text-muted">Visão do ano {data.ano}</p>
          <p className="text-xs text-muted">O Globo controla estoque. O RastroGlobus controla o rastro.</p>
        </div>
        <GlobusStatusBadge />
      </div>

      <div className="rounded-lg border border-line bg-panel/80 px-4 py-3 text-sm text-muted">
        Garantias são cadastro do RastroGlobus. Peças, NF e movimentos vêm do Globus (somente leitura).
      </div>

      <section className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="font-semibold">Globus ao vivo</h2>
            <p className="text-xs text-muted">
              {g?.aviso || "Compras e movimentos recentes (leitura)."}
            </p>
          </div>
          <Link to="/movimentos-globus" className="text-sm text-cyan hover:underline">
            Ver movimentos
          </Link>
        </div>

        {!g?.ok ? (
          <div className="rounded-lg border border-amber/40 bg-amber/10 px-4 py-3 text-sm text-amber">
            {g?.detail || "Globus indisponível."}
          </div>
        ) : null}

        <div className="grid gap-4 lg:grid-cols-2">
          <div className="overflow-x-auto rounded-xl border border-line bg-panel">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-line text-muted">
                <tr>
                  <th className="px-3 py-2 font-medium" colSpan={4}>
                    Últimas compras / aquisição
                  </th>
                </tr>
                <tr className="text-xs">
                  <th className="px-3 py-2 font-medium">Data</th>
                  <th className="px-3 py-2 font-medium">NF</th>
                  <th className="px-3 py-2 font-medium">Peça</th>
                  <th className="px-3 py-2 font-medium">Valor</th>
                </tr>
              </thead>
              <tbody>
                {(g?.compras_recentes || []).map((r, i) => (
                  <tr key={`${r.numero_nf}-${r.peca_codigo}-${i}`} className="border-t border-line">
                    <td className="px-3 py-2 whitespace-nowrap">
                      {sliceDate(r.data_entrada_nf || r.data_emissao_nf || r.data_movto)}
                    </td>
                    <td className="px-3 py-2">{r.numero_nf || "—"}</td>
                    <td className="px-3 py-2">
                      <div className="font-medium">{r.peca_codigo || "—"}</div>
                      <div className="text-xs text-muted">{r.fornecedor_nome || r.peca_descricao || ""}</div>
                    </td>
                    <td className="px-3 py-2">{money(r.valor_unitario)}</td>
                  </tr>
                ))}
                {g?.ok && !(g.compras_recentes || []).length ? (
                  <tr>
                    <td colSpan={4} className="px-3 py-4 text-center text-muted">
                      Nenhuma compra recente.
                    </td>
                  </tr>
                ) : null}
                {!g?.ok ? (
                  <tr>
                    <td colSpan={4} className="px-3 py-4 text-center text-muted">
                      —
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>

          <div className="overflow-x-auto rounded-xl border border-line bg-panel">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-line text-muted">
                <tr>
                  <th className="px-3 py-2 font-medium" colSpan={4}>
                    Últimos movimentos
                  </th>
                </tr>
                <tr className="text-xs">
                  <th className="px-3 py-2 font-medium">Data</th>
                  <th className="px-3 py-2 font-medium">Tipo</th>
                  <th className="px-3 py-2 font-medium">Peça</th>
                  <th className="px-3 py-2 font-medium">Qtd / NF</th>
                </tr>
              </thead>
              <tbody>
                {(g?.movimentos_recentes || []).map((r, i) => (
                  <tr key={`${r.data_movto}-${r.peca_codigo}-${i}`} className="border-t border-line">
                    <td className="px-3 py-2 whitespace-nowrap">{sliceDate(r.data_movto)}</td>
                    <td className="px-3 py-2">{r.tipo_movimento || "—"}</td>
                    <td className="px-3 py-2">
                      <div className="font-medium">{r.peca_codigo || "—"}</div>
                      <div className="text-xs text-muted">{r.veiculo_codigo || r.peca_descricao || ""}</div>
                    </td>
                    <td className="px-3 py-2 text-xs text-muted">
                      {r.quantidade ?? "—"} · NF {r.numero_nf || "—"}
                    </td>
                  </tr>
                ))}
                {g?.ok && !(g.movimentos_recentes || []).length ? (
                  <tr>
                    <td colSpan={4} className="px-3 py-4 text-center text-muted">
                      Nenhum movimento recente.
                    </td>
                  </tr>
                ) : null}
                {!g?.ok ? (
                  <tr>
                    <td colSpan={4} className="px-3 py-4 text-center text-muted">
                      —
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <KpiCard title="Abertas" value={c.aberta || 0} accent="cyan" />
        <KpiCard title="Em análise / enviadas" value={(c.em_analise || 0) + (c.enviada || 0)} accent="amber" />
        <KpiCard title="Procedentes" value={c.procedente || 0} accent="green" />
        <KpiCard title="Improcedentes" value={c.improcedente || 0} accent="red" />
        <KpiCard title="Cortesia" value={c.cortesia || 0} accent="violet" />
        <KpiCard title="Canceladas" value={c.cancelada || 0} accent="amber" />
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <KpiCard title="Valor procedente" value={money(data.valor_procedente)} accent="green" />
        <KpiCard title="Valor improcedente" value={money(data.valor_improcedente)} accent="red" />
        <KpiCard title="Valor em aberto" value={money(data.valor_aberto)} accent="amber" />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-xl border border-line bg-panel p-4">
          <h2 className="mb-3 font-semibold">Ranking de peças (garantias RG)</h2>
          <table className="w-full text-left text-sm">
            <thead className="text-muted">
              <tr>
                <th className="pb-2 font-medium">Peça</th>
                <th className="pb-2 font-medium">Qtd</th>
                <th className="pb-2 font-medium">Valor</th>
              </tr>
            </thead>
            <tbody>
              {data.ranking_pecas.map((p) => (
                <tr key={p.peca_id} className="border-t border-line">
                  <td className="py-2">
                    {p.codigo} — {p.descricao}
                  </td>
                  <td className="py-2">{p.total}</td>
                  <td className="py-2">{money(p.valor)}</td>
                </tr>
              ))}
              {!data.ranking_pecas.length ? (
                <tr>
                  <td colSpan={3} className="py-3 text-muted">
                    Sem dados.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </section>

        <section className="rounded-xl border border-line bg-panel p-4">
          <h2 className="mb-3 font-semibold">Veículos com 2+ garantias</h2>
          <ul className="space-y-2 text-sm">
            {data.veiculos_alerta.map((v) => (
              <li key={v.veiculo_id} className="flex justify-between border-b border-line py-2">
                <span>
                  {v.codigo} <span className="text-muted">({v.casa})</span>
                </span>
                <span className="text-amber">{v.total} garantias</span>
              </li>
            ))}
            {!data.veiculos_alerta.length ? (
              <li className="text-muted">Nenhum alerta no período.</li>
            ) : null}
          </ul>
        </section>
      </div>

      <section className="rounded-xl border border-line bg-panel p-4">
        <h2 className="mb-3 font-semibold">Parados há mais de 45 dias</h2>
        <div className="space-y-2">
          {data.parados_45_dias.map((p) => (
            <Link
              key={p.id}
              to={`/garantias/${p.id}`}
              className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-line px-3 py-2 text-sm hover:border-cyan/50"
            >
              <span>
                {p.protocolo} · {p.peca} · veículo {p.veiculo}
              </span>
              <BadgeStatus status={p.status} />
            </Link>
          ))}
          {!data.parados_45_dias.length ? (
            <p className="text-sm text-muted">Nenhum item parado.</p>
          ) : null}
        </div>
      </section>
    </div>
  );
}
