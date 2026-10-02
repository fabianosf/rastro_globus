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
import { statusLabel } from "../components/BadgeStatus";
import KpiCard from "../components/KpiCard";

type RankPeca = {
  peca_id: number;
  codigo: string;
  descricao: string;
  total: number;
  valor: string;
};

type RankVeiculo = {
  veiculo_id: number;
  codigo: string;
  casa: string;
  total: number;
  valor: string;
};

type RankingsPayload = {
  modo: string;
  status?: string;
  ano?: number;
  data_ini?: string;
  data_fim?: string;
  limite: number;
  total_garantias: number;
  kpis?: {
    total: number;
    abertos: number;
    enviada: number;
    valor_total: string;
  };
  por_status?: Array<{ status: string; total: number }>;
  pecas: RankPeca[];
  veiculos: RankVeiculo[];
};

function money(v: string | number | undefined) {
  if (v === undefined || v === null || v === "") return "—";
  const n = Number(v);
  if (Number.isNaN(n)) return String(v);
  return n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export default function RelatorioRankings() {
  const anoAtual = new Date().getFullYear();
  const anos = useMemo(
    () => [anoAtual, anoAtual - 1, anoAtual - 2, anoAtual - 3],
    [anoAtual]
  );

  const [ano, setAno] = useState(anoAtual);
  const [dataIni, setDataIni] = useState("");
  const [dataFim, setDataFim] = useState("");
  const [escopo, setEscopo] = useState<"abertos" | "todos">("abertos");
  const [data, setData] = useState<RankingsPayload | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const periodoAtivo = Boolean(dataIni || dataFim);

  useEffect(() => {
    const qs = new URLSearchParams({
      limite: "15",
      status: escopo === "todos" ? "todos" : "abertos",
    });
    if (periodoAtivo) {
      if (dataIni) qs.set("data_ini", dataIni);
      if (dataFim) qs.set("data_fim", dataFim);
    } else {
      qs.set("ano", String(ano));
    }

    setLoading(true);
    setError("");
    api<RankingsPayload>(`/api/relatorios/rankings/?${qs}`)
      .then(setData)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Erro ao carregar relatório."))
      .finally(() => setLoading(false));
  }, [ano, dataIni, dataFim, periodoAtivo, escopo]);

  function limparPeriodo() {
    setDataIni("");
    setDataFim("");
  }

  const periodoLabel = periodoAtivo
    ? `${dataIni || "…"} → ${dataFim || "…"}`
    : `ano ${ano}`;

  const chartData = useMemo(
    () =>
      (data?.por_status || []).map((r) => ({
        name: statusLabel(r.status),
        total: r.total,
      })),
    [data]
  );

  const kpis = data?.kpis;

  return (
    <div className="space-y-4">
      <div>
        <p className="text-sm text-muted">
          Relatório do que foi cadastrado no RG · {periodoLabel}
        </p>
        <p className="text-xs text-muted">
          {escopo === "abertos"
            ? "Só casos em aberto (como Minhas NFs) — sem improcedentes antigos."
            : "Todos os status do período (inclui improcedente/procedente)."}
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2 rounded-xl border border-line bg-panel p-3">
        <select
          className="rounded-lg border border-line bg-bg px-2 py-1.5 text-sm"
          value={escopo}
          title="Escopo"
          onChange={(e) => setEscopo(e.target.value as "abertos" | "todos")}
        >
          <option value="abertos">Abertos</option>
          <option value="todos">Todos</option>
        </select>
        <select
          className="w-24 rounded-lg border border-line bg-bg px-2 py-1.5 text-sm disabled:opacity-50"
          value={ano}
          disabled={periodoAtivo}
          title={periodoAtivo ? "Ano desativado quando há período" : "Ano"}
          onChange={(e) => setAno(Number(e.target.value))}
        >
          {anos.map((y) => (
            <option key={y} value={y}>
              {y}
            </option>
          ))}
        </select>
        <label className="flex items-center gap-1 text-xs text-muted">
          De
          <input
            type="date"
            className="rounded-lg border border-line bg-bg px-2 py-1.5 text-sm text-ink"
            value={dataIni}
            onChange={(e) => setDataIni(e.target.value)}
          />
        </label>
        <label className="flex items-center gap-1 text-xs text-muted">
          Até
          <input
            type="date"
            className="rounded-lg border border-line bg-bg px-2 py-1.5 text-sm text-ink"
            value={dataFim}
            onChange={(e) => setDataFim(e.target.value)}
          />
        </label>
        {periodoAtivo ? (
          <button
            type="button"
            className="rounded-lg border border-line px-3 py-1.5 text-sm text-muted"
            onClick={limparPeriodo}
          >
            Usar ano
          </button>
        ) : null}
      </div>

      {error ? <p className="text-red">{error}</p> : null}
      {loading ? <p className="text-muted">Carregando...</p> : null}

      {data && !loading ? (
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <KpiCard title="Total no filtro" value={kpis?.total ?? data.total_garantias} />
            <KpiCard title="Abertos" value={kpis?.abertos ?? "—"} accent="amber" />
            <KpiCard title="Enviadas" value={kpis?.enviada ?? "—"} accent="cyan" />
            <KpiCard
              title="Valor total"
              value={money(kpis?.valor_total)}
              accent="green"
            />
          </div>

          <section className="rounded-xl border border-line bg-panel p-4">
            <h2 className="mb-3 font-semibold">Quantidade por status</h2>
            <div className="h-64 w-full">
              {chartData.length ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} />
                    <YAxis allowDecimals={false} tick={{ fill: "#94a3b8", fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{ background: "#0f172a", border: "1px solid #334155" }}
                    />
                    <Bar dataKey="total" fill="#38bdf8" name="Quantidade" />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-sm text-muted">Sem dados no período.</p>
              )}
            </div>
          </section>

          <p className="text-xs text-muted">
            {data.total_garantias} garantia(s) no filtro · top {data.limite}
          </p>
          <div className="grid gap-4 lg:grid-cols-2">
            <section className="rounded-xl border border-line bg-panel p-4">
              <h2 className="mb-3 font-semibold">CARROs que mais quebram</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-line text-muted">
                    <tr>
                      <th className="px-2 py-2 font-medium">#</th>
                      <th className="px-2 py-2 font-medium">CARRO</th>
                      <th className="px-2 py-2 font-medium">Qtd</th>
                      <th className="px-2 py-2 font-medium">Valor</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.veiculos.map((v, i) => (
                      <tr key={v.veiculo_id} className="border-t border-line">
                        <td className="px-2 py-2 text-muted">{i + 1}</td>
                        <td className="px-2 py-2">
                          <div className="font-medium">{v.codigo}</div>
                          {v.casa ? <div className="text-xs text-muted">{v.casa}</div> : null}
                        </td>
                        <td className="px-2 py-2">{v.total}</td>
                        <td className="px-2 py-2 text-xs">{money(v.valor)}</td>
                      </tr>
                    ))}
                    {!data.veiculos.length ? (
                      <tr>
                        <td colSpan={4} className="px-2 py-4 text-center text-muted">
                          Sem dados no período.
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="rounded-xl border border-line bg-panel p-4">
              <h2 className="mb-3 font-semibold">Peças mais cadastradas</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-line text-muted">
                    <tr>
                      <th className="px-2 py-2 font-medium">#</th>
                      <th className="px-2 py-2 font-medium">Peça</th>
                      <th className="px-2 py-2 font-medium">Qtd</th>
                      <th className="px-2 py-2 font-medium">Valor</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.pecas.map((p, i) => (
                      <tr key={p.peca_id} className="border-t border-line">
                        <td className="px-2 py-2 text-muted">{i + 1}</td>
                        <td className="px-2 py-2">
                          <div className="font-medium">{p.codigo}</div>
                          <div className="text-xs text-muted">{p.descricao}</div>
                        </td>
                        <td className="px-2 py-2">{p.total}</td>
                        <td className="px-2 py-2 text-xs">{money(p.valor)}</td>
                      </tr>
                    ))}
                    {!data.pecas.length ? (
                      <tr>
                        <td colSpan={4} className="px-2 py-4 text-center text-muted">
                          Sem dados no período.
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </section>
          </div>
        </>
      ) : null}
    </div>
  );
}
