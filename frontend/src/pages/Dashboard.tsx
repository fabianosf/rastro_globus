import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, ApiError, getToken } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { canCreateGarantia } from "../auth/permissions";
import BadgeStatus from "../components/BadgeStatus";
import GlobusStatusBadge from "../components/GlobusStatusBadge";
import KpiCard from "../components/KpiCard";

type DashboardData = {
  ano: number;
  contagem_status: Record<string, number>;
  valor_procedente: string;
  valor_improcedente: string;
  valor_aberto: string;
  parados_45_dias: Array<{
    id: number;
    protocolo: string;
    status: string;
    peca: string;
    veiculo: string;
  }>;
  custo_improcedente_por_causa?: Array<{ causa: string; total: number; valor: string }>;
  top_pecas_improcedentes?: Array<{
    codigo: string;
    descricao: string;
    causa: string;
    total: number;
    valor: string;
  }>;
};

type HistoricoRow = {
  competencia?: string;
  empresa?: string;
  fornecedor?: string;
  solicitado: string;
  concedido: string;
  em_analise: string;
  negado: string;
};

type HistoricoData = {
  ano: number;
  por_mes: HistoricoRow[];
  por_empresa: HistoricoRow[];
  ranking_negado: HistoricoRow[];
  totais: {
    solicitado: string;
    concedido: string;
    em_analise: string;
    negado: string;
  };
  merge_app_from?: string;
};

type Tab = "vivo" | "historico";

type CompraGlobus = {
  numero_nf?: string;
  serie_nf?: string;
  data_entrada_nf?: string;
  data_emissao_nf?: string;
  valor_unitario?: string | number;
  valor_total_nf?: string | number;
  fornecedor_nome?: string;
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
  ultima_compra_globus: CompraGlobus | null;
};

type ImprocedentesPayload = {
  ano: number;
  count: number;
  results: ImprocedenteRow[];
  globus_ok: boolean;
  globus_detail: string;
  aviso: string;
};

function money(v: string | number | undefined) {
  if (v === undefined || v === null || v === "") return "—";
  const n = Number(v);
  if (Number.isNaN(n)) return String(v);
  return n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function num(v: string | number | undefined) {
  const n = Number(v);
  return Number.isNaN(n) ? 0 : n;
}

function chartMoney(v: number) {
  return v.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  });
}

const CHART_COLORS = {
  solicitado: "#38bdf8",
  concedido: "#34d399",
  em_analise: "#fbbf24",
  negado: "#f87171",
};

function garantiasStatusHref(status: string, ano: number) {
  return `/garantias?status=${encodeURIComponent(status)}&ano=${ano}`;
}

export default function Dashboard() {
  const currentYear = new Date().getFullYear();
  const [tab, setTab] = useState<Tab>("vivo");
  const [anoVivo] = useState(currentYear);
  const [anoHist, setAnoHist] = useState(currentYear);
  const [pecaFiltro, setPecaFiltro] = useState("");
  const [cruzamento, setCruzamento] = useState<ImprocedentesPayload | null>(null);
  const [cruzLoading, setCruzLoading] = useState(false);
  const [exportError, setExportError] = useState("");
  const [data, setData] = useState<DashboardData | null>(null);
  const [hist, setHist] = useState<HistoricoData | null>(null);
  const [error, setError] = useState("");
  const [histError, setHistError] = useState("");
  const [loading, setLoading] = useState(true);
  const [histLoading, setHistLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    api<DashboardData>(`/api/dashboard/?ano=${anoVivo}`)
      .then(setData)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Erro ao carregar dashboard."))
      .finally(() => setLoading(false));
  }, [anoVivo]);

  useEffect(() => {
    if (tab !== "historico") return;
    setHistLoading(true);
    setHistError("");
    api<HistoricoData>(`/api/relatorios/historico/?ano=${anoHist}`)
      .then(setHist)
      .catch((e) => setHistError(e instanceof ApiError ? e.message : "Erro ao carregar historico."))
      .finally(() => setHistLoading(false));
  }, [tab, anoHist]);

  useEffect(() => {
    if (tab !== "historico") return;
    setCruzLoading(true);
    const q = new URLSearchParams({ ano: String(anoHist) });
    if (pecaFiltro.trim()) q.set("peca", pecaFiltro.trim());
    api<ImprocedentesPayload>(`/api/relatorios/improcedentes-compras/?${q}`)
      .then(setCruzamento)
      .catch(() =>
        setCruzamento({
          ano: anoHist,
          count: 0,
          results: [],
          globus_ok: false,
          globus_detail: "Falha ao carregar cruzamento.",
          aviso: "",
        })
      )
      .finally(() => setCruzLoading(false));
  }, [tab, anoHist, pecaFiltro]);

  async function exportCsv() {
    setExportError("");
    try {
      const token = getToken();
      const res = await fetch(`/api/relatorios/export.csv/?ano=${anoHist}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error("Falha no export.");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `garantias-${anoHist}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setExportError("Nao foi possivel baixar o CSV.");
    }
  }

  const mesChart = useMemo(
    () =>
      (hist?.por_mes || []).map((r) => ({
        name: r.competencia || "",
        solicitado: num(r.solicitado),
        concedido: num(r.concedido),
        em_analise: num(r.em_analise),
        negado: num(r.negado),
      })),
    [hist]
  );

  const empresaChart = useMemo(
    () =>
      (hist?.por_empresa || []).map((r) => ({
        name: r.empresa || "",
        solicitado: num(r.solicitado),
        concedido: num(r.concedido),
        em_analise: num(r.em_analise),
        negado: num(r.negado),
      })),
    [hist]
  );

  const rankingChart = useMemo(
    () =>
      (hist?.ranking_negado || []).slice(0, 10).map((r) => ({
        name: (r.fornecedor || "").slice(0, 22),
        negado: num(r.negado),
      })),
    [hist]
  );

  const anosOpts = useMemo(() => {
    const years: number[] = [];
    for (let y = currentYear; y >= 2023; y -= 1) years.push(y);
    return years;
  }, [currentYear]);

  const emitidoEm = new Date().toLocaleString("pt-BR");

  return (
    <div className="space-y-6">
      <div className="no-print flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm text-muted">Painel de garantias</p>
          <p className="text-xs text-muted">
            O Globo controla estoque. O SGGI controla o rastro da garantia.
          </p>
        </div>
        <GlobusStatusBadge />
      </div>

      <div className="no-print flex flex-wrap gap-2 border-b border-line pb-2">
        <button
          type="button"
          onClick={() => setTab("vivo")}
          className={`rounded-md px-3 py-1.5 text-sm ${
            tab === "vivo" ? "bg-cyan/20 text-cyan" : "text-muted hover:text-ink"
          }`}
        >
          SGGI ao vivo
        </button>
        <button
          type="button"
          onClick={() => setTab("historico")}
          className={`rounded-md px-3 py-1.5 text-sm ${
            tab === "historico" ? "bg-cyan/20 text-cyan" : "text-muted hover:text-ink"
          }`}
        >
          Histórico e export
        </button>
      </div>

      {tab === "vivo" ? (
        loading ? (
          <p className="text-muted">Carregando dashboard...</p>
        ) : error ? (
          <p className="text-red">{error}</p>
        ) : data ? (
          <DashboardVivo data={data} />
        ) : null
      ) : (
        <div className="space-y-6">
          <div className="no-print flex flex-wrap items-end justify-between gap-4">
            <label className="text-sm">
              <span className="mb-1 block text-muted">Ano</span>
              <select
                className="rounded-md border border-line bg-panel px-3 py-2"
                value={anoHist}
                onChange={(e) => setAnoHist(Number(e.target.value))}
              >
                {anosOpts.map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </select>
            </label>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => window.print()}
                className="rounded-lg border border-line px-4 py-2 text-sm font-semibold text-cyan hover:border-cyan/50"
              >
                Imprimir / PDF
              </button>
              <button
                type="button"
                onClick={exportCsv}
                className="rounded-lg bg-cyan px-4 py-2 text-sm font-semibold text-bg"
              >
                Exportar CSV (SGGI)
              </button>
            </div>
          </div>
          <p className="no-print text-xs text-muted">
            Imprimir → Salvar como PDF · CSV para enviar por e-mail ou WhatsApp.
          </p>
          {exportError ? <p className="no-print text-red">{exportError}</p> : null}
          {hist?.merge_app_from ? (
            <p className="no-print text-xs text-muted">
              A partir de {hist.merge_app_from} os totais somam o histórico da planilha com as
              garantias do app.
            </p>
          ) : null}

          {histLoading ? <p className="no-print text-muted">Carregando historico...</p> : null}
          {histError ? <p className="no-print text-red">{histError}</p> : null}

          <div id="relatorio-print" className="space-y-6">
            <div className="print-only mb-4 border-b border-black pb-3">
              <h1 className="text-xl font-bold">SGGI — Relatório</h1>
              <p className="text-sm">
                Ano {anoHist} · Emitido em {emitidoEm}
              </p>
              <p className="text-xs">
                Negado (planilha) = Improcedente (SGGI). Improcedente não é status do estoque Globus.
              </p>
            </div>

          {hist && !histLoading ? (
            <>
              <div className="no-print rounded-lg border border-line bg-panel/80 px-4 py-3 text-sm text-muted">
                Planilha read-only (cutover).{" "}
                <span className="text-ink">Negado (planilha) = Improcedente (SGGI)</span>. Novos casos
                fecham só na ficha do SGGI.
              </div>

              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 text-sm">
                <div>
                  <p className="text-muted">Solicitado</p>
                  <p className="text-lg font-semibold">{money(hist.totais.solicitado)}</p>
                </div>
                <div>
                  <p className="text-muted">Concedido</p>
                  <p className="text-lg font-semibold text-green">{money(hist.totais.concedido)}</p>
                </div>
                <div>
                  <p className="text-muted">Em analise</p>
                  <p className="text-lg font-semibold text-amber">{money(hist.totais.em_analise)}</p>
                </div>
                <div>
                  <p className="text-muted">Negado (= Improcedente SGGI)</p>
                  <p className="text-lg font-semibold text-red">{money(hist.totais.negado)}</p>
                </div>
              </div>

              <section className="space-y-2">
                <h2 className="font-semibold">Por mes</h2>
                <div className="h-72 w-full">
                  {mesChart.length ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={mesChart}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                        <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} />
                        <YAxis
                          tick={{ fill: "#94a3b8", fontSize: 11 }}
                          tickFormatter={(v) => chartMoney(Number(v))}
                          width={90}
                        />
                        <Tooltip
                          formatter={(v: number) => money(v)}
                          contentStyle={{ background: "#0f172a", border: "1px solid #334155" }}
                        />
                        <Legend />
                        <Bar dataKey="solicitado" fill={CHART_COLORS.solicitado} name="Solicitado" />
                        <Bar dataKey="concedido" fill={CHART_COLORS.concedido} name="Concedido" />
                        <Bar dataKey="em_analise" fill={CHART_COLORS.em_analise} name="Em analise" />
                        <Bar
                          dataKey="negado"
                          fill={CHART_COLORS.negado}
                          name="Negado (= Improcedente)"
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <p className="text-sm text-muted">Sem dados da planilha para {anoHist}.</p>
                  )}
                </div>
              </section>

              <section className="space-y-2">
                <h2 className="font-semibold">Por empresa</h2>
                <div className="h-72 w-full">
                  {empresaChart.length ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={empresaChart}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                        <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} />
                        <YAxis
                          tick={{ fill: "#94a3b8", fontSize: 11 }}
                          tickFormatter={(v) => chartMoney(Number(v))}
                          width={90}
                        />
                        <Tooltip
                          formatter={(v: number) => money(v)}
                          contentStyle={{ background: "#0f172a", border: "1px solid #334155" }}
                        />
                        <Legend />
                        <Bar dataKey="solicitado" fill={CHART_COLORS.solicitado} name="Solicitado" />
                        <Bar dataKey="concedido" fill={CHART_COLORS.concedido} name="Concedido" />
                        <Bar dataKey="em_analise" fill={CHART_COLORS.em_analise} name="Em analise" />
                        <Bar
                          dataKey="negado"
                          fill={CHART_COLORS.negado}
                          name="Negado (= Improcedente)"
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <p className="text-sm text-muted">Sem breakdown por empresa.</p>
                  )}
                </div>
              </section>

              <section className="space-y-2">
                <h2 className="font-semibold">Top fornecedores (Negado = Improcedente SGGI)</h2>
                <div className="h-80 w-full">
                  {rankingChart.length ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={rankingChart} layout="vertical" margin={{ left: 24 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                        <XAxis
                          type="number"
                          tick={{ fill: "#94a3b8", fontSize: 11 }}
                          tickFormatter={(v) => chartMoney(Number(v))}
                        />
                        <YAxis
                          type="category"
                          dataKey="name"
                          width={120}
                          tick={{ fill: "#94a3b8", fontSize: 10 }}
                        />
                        <Tooltip
                          formatter={(v: number) => money(v)}
                          contentStyle={{ background: "#0f172a", border: "1px solid #334155" }}
                        />
                        <Bar
                          dataKey="negado"
                          fill={CHART_COLORS.negado}
                          name="Negado (= Improcedente)"
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <p className="text-sm text-muted">Sem ranking.</p>
                  )}
                </div>
              </section>
            </>
          ) : null}

          <section className="space-y-3 border-t border-line pt-6">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <h2 className="font-semibold">Improcedentes × compras Globus</h2>
                <p className="text-xs text-muted">
                  Improcedente vem do SGGI. Compras vêm do espelho Globus (leitura).
                </p>
              </div>
              <input
                className="no-print w-56 rounded-lg border border-line bg-panel px-3 py-2 text-sm"
                placeholder="Filtrar peça..."
                value={pecaFiltro}
                onChange={(e) => setPecaFiltro(e.target.value)}
              />
            </div>
            <div className="no-print rounded-lg border border-amber/40 bg-amber/10 px-4 py-3 text-sm text-amber">
              {cruzamento?.aviso ||
                "Consulta somente leitura. Improcedente não é status do estoque Globus."}
              {cruzamento && !cruzamento.globus_ok ? (
                <span className="mt-1 block text-xs">
                  Globus: {cruzamento.globus_detail || "compras indisponíveis"}
                </span>
              ) : null}
            </div>
            {cruzLoading ? (
              <p className="no-print text-sm text-muted">Carregando cruzamento...</p>
            ) : null}
            <div className="overflow-x-auto rounded-xl border border-line bg-panel">
              <table className="w-full min-w-[900px] text-left text-sm">
                <thead className="border-b border-line text-muted">
                  <tr>
                    <th className="px-3 py-3 font-medium">Protocolo</th>
                    <th className="px-3 py-3 font-medium">Peça</th>
                    <th className="px-3 py-3 font-medium">Veículo</th>
                    <th className="px-3 py-3 font-medium">Motivo</th>
                    <th className="px-3 py-3 font-medium">NF compra Globus</th>
                    <th className="px-3 py-3 font-medium">Data</th>
                    <th className="px-3 py-3 font-medium">Valor</th>
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
                              <div>
                                {c.numero_nf}
                                {c.serie_nf ? ` / ${c.serie_nf}` : ""}
                              </div>
                              <div className="text-xs text-muted">{c.fornecedor_nome || ""}</div>
                            </div>
                          ) : (
                            <span className="text-muted">
                              {cruzamento?.globus_ok ? "Sem compra no periodo" : "—"}
                            </span>
                          )}
                        </td>
                        <td className="px-3 py-2 whitespace-nowrap">
                          {dataNf ? String(dataNf).slice(0, 10) : "—"}
                        </td>
                        <td className="px-3 py-2">
                          {money(c?.valor_unitario ?? c?.valor_total_nf ?? r.valor_peca ?? undefined)}
                        </td>
                      </tr>
                    );
                  })}
                  {!cruzLoading && !(cruzamento?.results || []).length ? (
                    <tr>
                      <td colSpan={7} className="px-3 py-6 text-center text-muted">
                        Nenhuma garantia improcedente no ano {anoHist}.
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </section>
          </div>
        </div>
      )}
    </div>
  );
}

function DashboardVivo({ data }: { data: DashboardData }) {
  const { user } = useAuth();
  const c = data.contagem_status;
  const emAnalise = c.em_analise || 0;
  const ano = data.ano;
  const canNova = canCreateGarantia(user?.perfil);

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-amber/40 bg-amber/10 px-4 py-3 text-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="font-semibold text-amber">
              Fila em análise — fechar no SGGI ({emAnalise})
            </p>
            <p className="mt-1 text-xs text-muted">
              Improcedente só na ficha, após em análise. Globus não registra.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {canNova ? (
              <Link
                to="/garantias/nova-danfe"
                className="rounded-lg bg-cyan px-4 py-2 text-sm font-semibold text-bg hover:opacity-90"
              >
                Registrar DANFE
              </Link>
            ) : null}
            <Link
              to={garantiasStatusHref("em_analise", ano)}
              className="rounded-lg bg-amber/20 px-4 py-2 text-sm font-semibold text-amber hover:bg-amber/30"
            >
              Abrir fila
            </Link>
            <Link
              to={`/garantias?ano=${ano}`}
              className="rounded-lg border border-line bg-panel px-4 py-2 text-sm font-semibold text-cyan hover:border-cyan/50"
            >
              Todas
            </Link>
            {canNova ? (
              <Link
                to="/garantias/nova"
                className="rounded-lg px-2 py-2 text-xs text-muted underline-offset-2 hover:text-cyan hover:underline"
              >
                Formulário completo
              </Link>
            ) : null}
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-line bg-panel/80 px-4 py-3 text-sm text-muted">
        Ano {ano}: digite a DANFE e salve no SGGI. Improcedente só na ficha.
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          title="Abertas"
          value={c.aberta || 0}
          accent="cyan"
          to={garantiasStatusHref("aberta", ano)}
        />
        <KpiCard
          title="Em análise"
          value={emAnalise}
          accent="amber"
          hint="Fila para fechar no SGGI"
          to={garantiasStatusHref("em_analise", ano)}
        />
        <KpiCard
          title="Improcedentes"
          value={c.improcedente || 0}
          accent="red"
          to={garantiasStatusHref("improcedente", ano)}
        />
        <KpiCard
          title="Procedentes"
          value={c.procedente || 0}
          accent="green"
          to={garantiasStatusHref("procedente", ano)}
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <KpiCard title="Valor procedente" value={money(data.valor_procedente)} accent="green" />
        <KpiCard title="Valor improcedente" value={money(data.valor_improcedente)} accent="red" />
        <KpiCard title="Valor em aberto" value={money(data.valor_aberto)} accent="amber" />
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
                {p.protocolo} · {p.peca} · veiculo {p.veiculo}
              </span>
              <BadgeStatus status={p.status} />
            </Link>
          ))}
          {!data.parados_45_dias.length ? (
            <p className="text-sm text-muted">Nenhum item parado.</p>
          ) : null}
        </div>
      </section>

      <details className="rounded-xl border border-line bg-panel p-4 text-sm">
        <summary className="cursor-pointer font-semibold text-muted hover:text-ink">
          Detalhes (custo por causa · top peças)
        </summary>
        <div className="mt-4 grid gap-6 lg:grid-cols-2">
          <section>
            <h3 className="mb-2 font-medium">Custo improcedente por causa</h3>
            <ul className="space-y-2">
              {(data.custo_improcedente_por_causa || []).map((r) => (
                <li key={r.causa} className="flex justify-between border-b border-line py-1">
                  <span>{r.causa}</span>
                  <span>{money(r.valor)}</span>
                </li>
              ))}
              {!(data.custo_improcedente_por_causa || []).length ? (
                <li className="text-muted">Sem dados.</li>
              ) : null}
            </ul>
          </section>
          <section>
            <h3 className="mb-2 font-medium">Top peças improcedentes</h3>
            <ul className="space-y-2">
              {(data.top_pecas_improcedentes || []).map((r, i) => (
                <li key={`${r.codigo}-${r.causa}-${i}`} className="border-b border-line py-1">
                  <div className="flex justify-between">
                    <span className="font-medium">{r.codigo}</span>
                    <span>{r.total}x</span>
                  </div>
                  <div className="text-xs text-muted">
                    {r.causa} · {money(r.valor)}
                  </div>
                </li>
              ))}
              {!(data.top_pecas_improcedentes || []).length ? (
                <li className="text-muted">Sem dados.</li>
              ) : null}
            </ul>
          </section>
        </div>
      </details>
    </div>
  );
}
