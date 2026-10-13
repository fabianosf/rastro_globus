import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, ApiError } from "../api/client";
import KpiCard from "../components/KpiCard";

type ErroInternoPayload = {
  ano: number;
  total: number;
  valor_total: string;
  sem_valor: number;
  cobranca: {
    cobrados: number;
    valor_cobrado: string;
    nao_cobrados: number;
    valor_nao_cobrado: string;
  };
  por_causa: Array<{ causa: string; label: string; total: number; valor: string }>;
  por_responsavel_tipo: Array<{ tipo: string; label: string; total: number; valor: string }>;
  top_responsaveis: Array<{ nome: string; tipo: string; total: number; valor: string }>;
  top_pecas: Array<{ codigo: string; descricao: string; total: number; valor: string }>;
  top_veiculos: Array<{ codigo: string; casa: string; total: number; valor: string }>;
  por_mes: Array<{ mes: number; total: number; valor: string }>;
  reincidencia: {
    alertas_novos: number;
    garantias_de_alertas: number;
    valor_recuperado: string;
  };
};

const MES_LABEL = [
  "",
  "Jan",
  "Fev",
  "Mar",
  "Abr",
  "Mai",
  "Jun",
  "Jul",
  "Ago",
  "Set",
  "Out",
  "Nov",
  "Dez",
];

function money(v: string | number | undefined) {
  if (v === undefined || v === null || v === "") return "—";
  const n = Number(v);
  if (Number.isNaN(n)) return String(v);
  return n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export default function RelatorioErroInterno() {
  const anoAtual = new Date().getFullYear();
  const anos = useMemo(
    () => [anoAtual, anoAtual - 1, anoAtual - 2, anoAtual - 3],
    [anoAtual]
  );
  const [ano, setAno] = useState(anoAtual);
  const [data, setData] = useState<ErroInternoPayload | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setError("");
    api<ErroInternoPayload>(`/api/relatorios/erro-interno/?ano=${ano}`)
      .then(setData)
      .catch((e) =>
        setError(e instanceof ApiError ? e.message : "Erro ao carregar relatório.")
      )
      .finally(() => setLoading(false));
  }, [ano]);

  const pctCobrado = useMemo(() => {
    if (!data || data.total === 0) return "—";
    return `${((data.cobranca.cobrados / data.total) * 100).toFixed(0)}%`;
  }, [data]);

  const chartCausa = useMemo(
    () =>
      (data?.por_causa || []).map((r) => ({
        name: r.label.length > 22 ? `${r.label.slice(0, 20)}…` : r.label,
        valor: Number(r.valor) || 0,
      })),
    [data]
  );

  const chartMes = useMemo(
    () =>
      (data?.por_mes || []).map((r) => ({
        name: MES_LABEL[r.mes] || String(r.mes),
        valor: Number(r.valor) || 0,
      })),
    [data]
  );

  return (
    <div className="space-y-4">
      <div className="no-print flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm text-muted">
            Improcedente = erro interno (custo da empresa, não do fornecedor) · ano {ano}
          </p>
          <p className="text-xs text-muted">
            Base: garantias com status improcedente. Valor recuperado = procedentes originadas de alerta.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            className="w-24 rounded-lg border border-line bg-bg px-2 py-1.5 text-sm"
            value={ano}
            onChange={(e) => setAno(Number(e.target.value))}
          >
            {anos.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => window.print()}
            className="rounded-lg border border-line px-3 py-1.5 text-sm text-muted hover:text-text"
          >
            Imprimir
          </button>
        </div>
      </div>

      {error ? <p className="text-red">{error}</p> : null}
      {loading ? <p className="text-muted">Carregando…</p> : null}

      {data && !loading ? (
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <KpiCard
              title="Custo total das improcedências"
              value={money(data.valor_total)}
              accent="red"
            />
            <KpiCard title="Quantidade" value={data.total} accent="amber" />
            <KpiCard
              title="% cobrado internamente"
              value={pctCobrado}
              hint={`${data.cobranca.cobrados} de ${data.total}`}
              accent="cyan"
            />
            <KpiCard
              title="Valor recuperado (reincidência)"
              value={money(data.reincidencia.valor_recuperado)}
              hint={`${data.reincidencia.garantias_de_alertas} garantia(s) de alerta · ${data.reincidencia.alertas_novos} alerta(s) novo(s)`}
              accent="green"
            />
          </div>

          {data.sem_valor > 0 ? (
            <p className="rounded-lg border border-amber/40 bg-amber/10 px-3 py-2 text-sm text-amber">
              {data.sem_valor} improcedente(s) sem valor informado. O custo real é maior.
            </p>
          ) : null}

          <div className="grid gap-4 lg:grid-cols-2">
            <section className="rounded-xl border border-line bg-panel p-4">
              <h2 className="mb-3 font-semibold">Custo por causa</h2>
              <div className="h-64 w-full">
                {chartCausa.length ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartCausa}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                      <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 10 }} />
                      <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
                      <Tooltip
                        contentStyle={{ background: "#0f172a", border: "1px solid #334155" }}
                        formatter={(v: number) => money(v)}
                      />
                      <Bar dataKey="valor" fill="#f87171" name="Valor" />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="text-sm text-muted">Sem dados no período.</p>
                )}
              </div>
            </section>

            <section className="rounded-xl border border-line bg-panel p-4">
              <h2 className="mb-3 font-semibold">Custo por mês</h2>
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartMes}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 10 }} />
                    <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{ background: "#0f172a", border: "1px solid #334155" }}
                      formatter={(v: number) => money(v)}
                    />
                    <Bar dataKey="valor" fill="#38bdf8" name="Valor" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </section>
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <TabelaSimples
              titulo="Top responsáveis"
              headers={["Nome", "Tipo", "Qtd", "Valor"]}
              rows={data.top_responsaveis.map((r) => [
                r.nome,
                r.tipo || "—",
                String(r.total),
                money(r.valor),
              ])}
            />
            <TabelaSimples
              titulo="Top peças"
              headers={["Código", "Descrição", "Qtd", "Valor"]}
              rows={data.top_pecas.map((r) => [
                r.codigo,
                r.descricao || "—",
                String(r.total),
                money(r.valor),
              ])}
            />
            <TabelaSimples
              titulo="Top veículos"
              headers={["Código", "Casa", "Qtd", "Valor"]}
              rows={data.top_veiculos.map((r) => [
                r.codigo,
                r.casa || "—",
                String(r.total),
                money(r.valor),
              ])}
            />
          </div>
        </>
      ) : null}
    </div>
  );
}

function TabelaSimples({
  titulo,
  headers,
  rows,
}: {
  titulo: string;
  headers: string[];
  rows: string[][];
}) {
  return (
    <section className="overflow-x-auto rounded-xl border border-line bg-panel">
      <h2 className="border-b border-line px-3 py-2 font-semibold">{titulo}</h2>
      <table className="w-full text-left text-sm">
        <thead className="text-muted">
          <tr>
            {headers.map((h) => (
              <th key={h} className="px-3 py-2 font-medium">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-t border-line">
              {row.map((cell, j) => (
                <td key={j} className="px-3 py-2">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
          {!rows.length ? (
            <tr>
              <td colSpan={headers.length} className="px-3 py-4 text-center text-muted">
                Sem dados.
              </td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </section>
  );
}
