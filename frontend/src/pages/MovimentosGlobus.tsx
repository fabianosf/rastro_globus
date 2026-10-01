import { FormEvent, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import GlobusStatusBadge from "../components/GlobusStatusBadge";

type Movimento = {
  data_movto?: string;
  data_entrada_nf?: string;
  data_emissao_nf?: string;
  tipo_movimento?: string;
  tipo_his?: string;
  peca_codigo?: string;
  peca_descricao?: string;
  quantidade?: string | number;
  valor?: string | number;
  valor_unitario?: string | number;
  valor_total_nf?: string | number;
  requisicao?: string;
  documento?: string;
  numero_nf?: string;
  serie_nf?: string;
  veiculo_codigo?: string;
  fornecedor_nome?: string;
};

function money(v: string | number | undefined) {
  if (v === undefined || v === null || v === "") return "—";
  const n = Number(v);
  if (Number.isNaN(n)) return String(v);
  return n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function tipoBadge(tipo?: string) {
  if (tipo === "entrada" || tipo === "compras") {
    return "bg-green/15 text-green border-green/40";
  }
  if (tipo === "saida") {
    return "bg-amber/15 text-amber border-amber/40";
  }
  return "bg-muted/15 text-muted border-muted/40";
}

export default function MovimentosGlobus() {
  const [params, setParams] = useSearchParams();
  const [peca, setPeca] = useState(params.get("peca") || "");
  const [veiculo, setVeiculo] = useState(params.get("veiculo") || "");
  const [tipo, setTipo] = useState(params.get("tipo") || "todos");
  const [dataIni, setDataIni] = useState(params.get("data_ini") || "");
  const [dataFim, setDataFim] = useState(params.get("data_fim") || "");
  const [rows, setRows] = useState<Movimento[]>([]);
  const [aviso, setAviso] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const isCompras = tipo === "compras";

  function buildQuery(next?: {
    peca?: string;
    veiculo?: string;
    tipo?: string;
    data_ini?: string;
    data_fim?: string;
  }) {
    const q = new URLSearchParams();
    const p = next?.peca ?? peca;
    const v = next?.veiculo ?? veiculo;
    const t = next?.tipo ?? tipo;
    const di = next?.data_ini ?? dataIni;
    const df = next?.data_fim ?? dataFim;
    if (p) q.set("peca", p);
    if (v && t !== "compras") q.set("veiculo", v);
    if (t) q.set("tipo", t);
    if (di) q.set("data_ini", di);
    if (df) q.set("data_fim", df);
    q.set("limite", "100");
    return q;
  }

  async function carregar(search?: URLSearchParams) {
    setLoading(true);
    setError("");
    try {
      const q = search || buildQuery();
      const t = q.get("tipo") || "todos";
      if (t === "compras") {
        const pecaQ = (q.get("peca") || "").trim();
        if (!pecaQ) {
          setRows([]);
          setAviso("Informe o código da peça para consultar compras/aquisição no Globus.");
          return;
        }
        const cq = new URLSearchParams();
        cq.set("peca", pecaQ);
        if (q.get("data_ini")) cq.set("data_ini", q.get("data_ini")!);
        if (q.get("data_fim")) cq.set("data_fim", q.get("data_fim")!);
        cq.set("limite", q.get("limite") || "100");
        const data = await api<{ results: Movimento[]; aviso?: string }>(
          `/api/globus/compras/?${cq.toString()}`
        );
        setRows(
          (data.results || []).map((r) => ({
            ...r,
            tipo_movimento: "compras",
            data_movto: r.data_entrada_nf || r.data_emissao_nf || r.data_movto,
            valor: r.valor_unitario ?? r.valor_total_nf ?? r.valor,
          }))
        );
        setAviso(data.aviso || "Compras Globus (somente leitura). Não altera estoque.");
      } else {
        const data = await api<{ results: Movimento[]; aviso?: string }>(
          `/api/globus/movimentos/?${q.toString()}`
        );
        setRows(data.results || []);
        setAviso(data.aviso || "Consulta somente leitura. Estoque continua no Globo.");
      }
    } catch (e) {
      setRows([]);
      setError(e instanceof ApiError ? e.message : "Falha ao consultar movimentos.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const q = buildQuery({
      peca: params.get("peca") || "",
      veiculo: params.get("veiculo") || "",
      tipo: params.get("tipo") || "todos",
      data_ini: params.get("data_ini") || "",
      data_fim: params.get("data_fim") || "",
    });
    setPeca(q.get("peca") || "");
    setVeiculo(q.get("veiculo") || "");
    setTipo(q.get("tipo") || "todos");
    setDataIni(q.get("data_ini") || "");
    setDataFim(q.get("data_fim") || "");
    carregar(q);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const q = buildQuery();
    setParams(q);
    carregar(q);
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm text-muted">
            Entrada, saída e compras/aquisição no Globus (espelho). O RastroGlobus não altera saldo.
          </p>
        </div>
        <GlobusStatusBadge />
      </div>

      <div className="rounded-lg border border-amber/40 bg-amber/10 px-4 py-3 text-sm text-amber">
        {aviso || "Consulta somente leitura. Estoque continua no Globo."}
      </div>

      <form
        onSubmit={onSubmit}
        className="grid gap-3 rounded-xl border border-line bg-panel p-4 md:grid-cols-3 lg:grid-cols-6"
      >
        <input
          className="rounded-lg border border-line bg-bg px-3 py-2 text-sm"
          placeholder="Peça (código ou descrição)"
          value={peca}
          onChange={(e) => setPeca(e.target.value)}
          required={isCompras}
        />
        <input
          className="rounded-lg border border-line bg-bg px-3 py-2 text-sm disabled:opacity-50"
          placeholder="Veículo (prefixo)"
          value={veiculo}
          onChange={(e) => setVeiculo(e.target.value)}
          disabled={isCompras}
          title={isCompras ? "Filtro de veículo não se aplica a compras" : undefined}
        />
        <select
          className="rounded-lg border border-line bg-bg px-3 py-2 text-sm"
          value={tipo}
          onChange={(e) => setTipo(e.target.value)}
        >
          <option value="todos">Entrada + saída</option>
          <option value="entrada">Só entrada</option>
          <option value="saida">Só saída</option>
          <option value="compras">Compras / aquisição</option>
        </select>
        <input
          type="date"
          className="rounded-lg border border-line bg-bg px-3 py-2 text-sm"
          value={dataIni}
          onChange={(e) => setDataIni(e.target.value)}
          title="Data inicial"
        />
        <input
          type="date"
          className="rounded-lg border border-line bg-bg px-3 py-2 text-sm"
          value={dataFim}
          onChange={(e) => setDataFim(e.target.value)}
          title="Data final"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-cyan px-4 py-2 text-sm font-semibold text-bg disabled:opacity-60"
        >
          {loading ? "Consultando…" : "Consultar"}
        </button>
      </form>

      {error ? <p className="text-sm text-red">{error}</p> : null}

      <div className="overflow-x-auto rounded-xl border border-line bg-panel">
        <table className="w-full min-w-[900px] text-left text-sm">
          <thead className="border-b border-line text-muted">
            <tr>
              <th className="px-3 py-3 font-medium">{isCompras ? "Data NF" : "Data"}</th>
              <th className="px-3 py-3 font-medium">Tipo</th>
              <th className="px-3 py-3 font-medium">Peça</th>
              <th className="px-3 py-3 font-medium">Qtd</th>
              <th className="px-3 py-3 font-medium">{isCompras ? "Valor unit." : "Valor"}</th>
              <th className="px-3 py-3 font-medium">{isCompras ? "Fornecedor" : "Veículo"}</th>
              <th className="px-3 py-3 font-medium">{isCompras ? "NF" : "RQ / Doc / NF"}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, idx) => (
              <tr key={`${r.data_movto}-${r.peca_codigo}-${r.numero_nf}-${idx}`} className="border-t border-line">
                <td className="px-3 py-2 whitespace-nowrap">
                  {r.data_movto
                    ? String(r.data_movto).slice(0, 10)
                    : r.data_entrada_nf
                      ? String(r.data_entrada_nf).slice(0, 10)
                      : "—"}
                </td>
                <td className="px-3 py-2">
                  <span
                    className={`inline-flex rounded border px-2 py-0.5 text-xs ${tipoBadge(
                      r.tipo_movimento
                    )}`}
                  >
                    {isCompras ? "compras" : r.tipo_movimento || "—"}
                    {!isCompras && r.tipo_his ? ` (${r.tipo_his})` : ""}
                  </span>
                </td>
                <td className="px-3 py-2">
                  <div className="font-medium">{r.peca_codigo || "—"}</div>
                  <div className="text-xs text-muted">{r.peca_descricao || ""}</div>
                </td>
                <td className="px-3 py-2">{r.quantidade ?? "—"}</td>
                <td className="px-3 py-2">
                  {money(isCompras ? r.valor_unitario ?? r.valor : r.valor)}
                </td>
                <td className="px-3 py-2">
                  {isCompras ? r.fornecedor_nome || "—" : r.veiculo_codigo || "—"}
                </td>
                <td className="px-3 py-2 text-xs text-muted">
                  {isCompras ? (
                    <>
                      NF {r.numero_nf || "—"}
                      {r.serie_nf ? ` / ${r.serie_nf}` : ""}
                    </>
                  ) : (
                    <>
                      RQ {r.requisicao || "—"} · Doc {r.documento || "—"} · NF {r.numero_nf || "—"}
                    </>
                  )}
                </td>
              </tr>
            ))}
            {!loading && !rows.length ? (
              <tr>
                <td colSpan={7} className="px-3 py-6 text-center text-muted">
                  {isCompras
                    ? "Nenhuma compra/aquisição encontrada. Informe a peça e o período."
                    : "Nenhum movimento encontrado no período."}
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-muted">
        Período padrão: últimos 90 dias (movimentos) ou histórico amplo (compras), se as datas não
        forem informadas.{" "}
        <Link to="/garantias" className="text-cyan hover:underline">
          Voltar às garantias
        </Link>
      </p>
    </div>
  );
}
