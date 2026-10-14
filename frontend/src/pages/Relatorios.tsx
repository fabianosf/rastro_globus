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

type ResumoAno = {
  ano: number;
  contagem_status: Record<string, number>;
  valor_improcedente: string;
  valor_aberto: string;
  valor_procedente?: string;
};

type ErroInternoPayload = {
  ano: number;
  total: number;
  valor_total: string;
  sem_valor: number;
  por_causa: Array<{ causa: string; label: string; total: number; valor: string }>;
  top_pecas: Array<{ codigo: string; descricao: string; total: number; valor: string }>;
  por_mes: Array<{ mes: number; total: number; valor: string }>;
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

export default function Relatorios() {
  const anoAtual = new Date().getFullYear();
  const anos = useMemo(
    () => [anoAtual, anoAtual - 1, anoAtual - 2, anoAtual - 3],
    [anoAtual]
  );
  const [ano, setAno] = useState(anoAtual);
  const [resumo, setResumo] = useState<ResumoAno | null>(null);
  const [erroInt, setErroInt] = useState<ErroInternoPayload | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setError("");
    Promise.all([
      api<ResumoAno>(`/api/relatorios/resumo/?ano=${ano}`),
      api<ErroInternoPayload>(`/api/relatorios/erro-interno/?ano=${ano}`),
    ])
      .then(([r, e]) => {
        setResumo(r);
        setErroInt(e);
      })
      .catch((e) =>
        setError(e instanceof ApiError ? e.message : "Erro ao carregar relatório.")
      )
      .finally(() => setLoading(false));
  }, [ano]);

  const contagem = resumo?.contagem_status || {};
  const qtdTotal = Object.values(contagem).reduce((a, b) => a + (b || 0), 0);
  const qtdAndamento =
    (contagem.aberta || 0) + (contagem.enviada || 0) + (contagem.em_analise || 0);
  const valorTotal =
    Number(resumo?.valor_improcedente || 0) +
    Number(resumo?.valor_aberto || 0) +
    Number(resumo?.valor_procedente || 0);

  const chartCausa = useMemo(
    () =>
      (erroInt?.por_causa || []).map((r) => ({
        name: r.label.length > 22 ? `${r.label.slice(0, 20)}…` : r.label,
        valor: Number(r.valor) || 0,
      })),
    [erroInt]
  );

  const chartMes = useMemo(
    () =>
      (erroInt?.por_mes || []).map((r) => ({
        name: MES_LABEL[r.mes] || String(r.mes),
        valor: Number(r.valor) || 0,
      })),
    [erroInt]
  );

  return (
    <div className="min-w-0 space-y-5">
      <div className="no-print flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end sm:justify-between">
        <div className="min-w-0">
          <p className="text-sm text-muted">
            Notas do ano {ano} — custo improcedente
          </p>
          <p className="text-xs text-muted">
            Improcedente = custo da empresa (não do fornecedor).
          </p>
        </div>
        <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto">
          <select
            className="min-w-[6rem] flex-1 rounded-lg border border-line bg-bg px-2 py-1.5 text-sm sm:flex-none sm:w-24"
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
            className="flex-1 rounded-lg border border-line px-3 py-1.5 text-sm text-muted hover:text-text sm:flex-none"
          >
            Imprimir
          </button>
        </div>
      </div>

      {error ? <p className="text-red">{error}</p> : null}
      {loading ? <p className="text-muted">Carregando…</p> : null}

      {!loading && resumo ? (
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <KpiCard title="Quantidade de notas" value={qtdTotal} accent="cyan" />
            <KpiCard
              title="Valor total"
              value={money(valorTotal)}
              hint="Andamento + improcedente + procedente"
              accent="cyan"
            />
            <KpiCard
              title="Valor improcedente"
              value={money(resumo.valor_improcedente)}
              hint={`${erroInt?.total ?? contagem.improcedente ?? 0} nota(s) · ver lista`}
              accent="red"
              to={`/?ano=${ano}&status=improcedente`}
            />
            <KpiCard
              title="Em andamento"
              value={qtdAndamento}
              hint={money(resumo.valor_aberto)}
              accent="amber"
              to={`/?ano=${ano}&status=abertos`}
            />
          </div>

          {erroInt && erroInt.sem_valor > 0 ? (
            <p className="rounded-lg border border-amber/40 bg-amber/10 px-3 py-2 text-sm text-amber">
              {erroInt.sem_valor} improcedente(s) sem valor informado. O custo real pode ser maior.
            </p>
          ) : null}

          <div className="grid min-w-0 gap-4 lg:grid-cols-2">
            <section className="min-w-0 rounded-xl border border-line bg-panel p-4">
              <h2 className="mb-3 font-semibold">Custo por causa</h2>
              <div className="h-56 w-full min-w-0">
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
                  <p className="text-sm text-muted">Sem improcedentes no período.</p>
                )}
              </div>
            </section>

            <section className="rounded-xl border border-line bg-panel p-4">
              <h2 className="mb-3 font-semibold">Improcedente por mês</h2>
              <div className="h-56 w-full">
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

          <div className="grid gap-4 lg:grid-cols-2">
            <TabelaSimples
              titulo="Por peça (improcedentes)"
              headers={["Código", "Descrição", "Qtd", "Valor"]}
              rows={(erroInt?.top_pecas || []).map((r) => [
                r.codigo,
                r.descricao || "—",
                String(r.total),
                money(r.valor),
              ])}
            />
            <TabelaSimples
              titulo="Por causa"
              headers={["Causa", "Qtd", "Valor"]}
              rows={(erroInt?.por_causa || []).map((r) => [
                r.label,
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
