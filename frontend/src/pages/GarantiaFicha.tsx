import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import {
  canAdvanceStatus,
  canAnexar,
  canCancel,
  canCloseStatus,
  canVincularNf,
} from "../auth/permissions";
import BadgeStatus from "../components/BadgeStatus";
import {
  buscarNfGlobus,
  buscarNfsGarantiaGlobus,
  type GlobusNf,
} from "../components/GlobusStatusBadge";
import Timeline, { type Evento } from "../components/Timeline";

type Garantia = {
  id: number;
  protocolo: string;
  status: string;
  peca_nome: string;
  peca_detalhe?: { codigo_interno?: string; descricao?: string };
  veiculo_codigo: string;
  fornecedor_nome: string;
  nf_compra: string;
  nf_remessa: string;
  nf_retorno: string;
  nf_entrada_globo: string;
  valor_peca: string | null;
  km_aplicacao: number | null;
  requisicao_anterior: string;
  requisicao_atual: string;
  observacoes: string;
  laudo_resumo: string;
  motivo_improcedente: string;
  dias_aberta: number;
  eventos: Evento[];
  anexos: Array<{ id: number; descricao: string; arquivo: string; enviado_em: string }>;
};

const field =
  "w-full rounded-lg border border-line bg-bg px-3 py-2 text-sm outline-none focus:border-cyan";

export default function GarantiaFicha() {
  const { id } = useParams();
  const { user } = useAuth();
  const [g, setG] = useState<Garantia | null>(null);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(true);

  const [nfRemessa, setNfRemessa] = useState("");
  const [nfRetorno, setNfRetorno] = useState("");
  const [nfData, setNfData] = useState(new Date().toISOString().slice(0, 10));
  const [descricao, setDescricao] = useState("");
  const [motivo, setMotivo] = useState("");
  const [nfGlobo, setNfGlobo] = useState("");
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [buscandoNf, setBuscandoNf] = useState<"remessa" | "retorno" | "globo" | null>(null);
  const [nfsGarantia, setNfsGarantia] = useState<GlobusNf[]>([]);
  const [qNfGarantia, setQNfGarantia] = useState("");
  const [avisoNfsGarantia, setAvisoNfsGarantia] = useState("");
  const [loadingNfsGarantia, setLoadingNfsGarantia] = useState(false);

  const perfil = user?.perfil;
  const allowNf = canVincularNf(perfil);
  const allowAdvance = canAdvanceStatus(perfil);
  const allowClose = canCloseStatus(perfil);
  const allowAnexar = canAnexar(perfil);
  const allowCancel = canCancel(perfil, g?.status);
  const showActions = allowNf || allowAdvance || allowClose || allowAnexar || allowCancel;

  const load = useCallback(() => {
    if (!id) return;
    setLoading(true);
    api<Garantia>(`/api/garantias/${id}/`)
      .then(setG)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Erro ao carregar ficha."))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  // código da peça (uma única declaração no componente)
  const pecaCodigo =
    g?.peca_detalhe?.codigo_interno ||
    (g?.peca_nome || "").split(" - ")[0]?.trim() ||
    "";

  async function carregarNfsGarantia(opts?: { numero?: string; peca?: string }) {
    setLoadingNfsGarantia(true);
    setAvisoNfsGarantia("");
    try {
      const peca = opts?.peca ?? pecaCodigo;
      const numero = opts?.numero ?? "";
      const data = await buscarNfsGarantiaGlobus({
        peca: peca || undefined,
        numero: numero || undefined,
        limite: 15,
      });
      setNfsGarantia(data.results || []);
      setAvisoNfsGarantia(
        data.aviso ||
          "NFs Globus NEG/NFG (garantia) — somente leitura. Não define improcedente."
      );
    } catch (e) {
      setNfsGarantia([]);
      setAvisoNfsGarantia(
        e instanceof ApiError ? e.message : "NFs garantia Globus indisponíveis."
      );
    } finally {
      setLoadingNfsGarantia(false);
    }
  }

  useEffect(() => {
    if (!pecaCodigo) return;
    carregarNfsGarantia({ peca: pecaCodigo });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pecaCodigo]);

  function usarNfComo(tipo: "remessa" | "retorno", nf: GlobusNf) {
    const dataIso = nf.data_emissao
      ? String(nf.data_emissao).slice(0, 10)
      : nf.data_entrada
        ? String(nf.data_entrada).slice(0, 10)
        : undefined;
    if (tipo === "remessa") {
      setNfRemessa(nf.numero);
    } else {
      setNfRetorno(nf.numero);
    }
    if (dataIso) setNfData(dataIso);
    setMsg(
      `NF ${nf.numero} (${nf.tipo_doc || "NEG/NFG"}) pronta para vincular como ${tipo}.`
    );
  }

  async function buscarNoGlobus(
    tipo: "remessa" | "retorno" | "globo",
    numero: string,
    onFound: (numero: string, dataEmissao?: string, valor?: string) => void
  ) {
    if (!numero.trim()) {
      setError("Informe o número da NF para buscar no Globus.");
      return;
    }
    setError("");
    setMsg("");
    setBuscandoNf(tipo);
    try {
      const rows = await buscarNfGlobus(numero.trim());
      if (!rows.length) {
        setError("NF não encontrada no Globus (somente leitura).");
        return;
      }
      const nf = rows[0];
      const dataIso = nf.data_emissao ? String(nf.data_emissao).slice(0, 10) : undefined;
      onFound(nf.numero || numero, dataIso, nf.valor ? String(nf.valor) : undefined);
      setMsg(
        `Globus: NF ${nf.numero} encontrada (espelho — sem movimentar estoque).`
      );
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Falha ao buscar NF no Globus.");
    } finally {
      setBuscandoNf(null);
    }
  }

  async function vincularNota(tipo: "remessa" | "retorno", numero: string): Promise<boolean> {
    if (!g || !numero) return false;
    setError("");
    setMsg("");
    try {
      const updated = await api<Garantia>(`/api/garantias/${g.id}/notas/`, {
        method: "POST",
        body: {
          tipo,
          numero,
          serie: "",
          data_emissao: nfData,
          valor: g.valor_peca,
        },
      });
      setG(updated);
      setMsg(`NF de ${tipo} vinculada.`);
      if (tipo === "remessa") setNfRemessa("");
      else setNfRetorno("");
      return true;
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Erro ao vincular NF.");
      return false;
    }
  }

  async function mudarStatus(status: string): Promise<boolean> {
    if (!g) return false;
    setError("");
    setMsg("");
    try {
      const updated = await api<Garantia>(`/api/garantias/${g.id}/status/`, {
        method: "POST",
        body: {
          status,
          descricao,
          motivo_improcedente: motivo,
          nf_entrada_globo: status === "procedente" ? nfGlobo : "",
        },
      });
      setG(updated);
      setMsg(`Status atualizado para ${status}.`);
      setDescricao("");
      setMotivo("");
      setNfGlobo("");
      return true;
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Erro ao alterar status.");
      return false;
    }
  }

  async function uploadAnexo(e: FormEvent) {
    e.preventDefault();
    if (!g || !arquivo) return;
    setError("");
    setMsg("");
    const fd = new FormData();
    fd.append("arquivo", arquivo);
    fd.append("descricao", "Anexo da ficha");
    try {
      await api(`/api/garantias/${g.id}/anexos/`, { method: "POST", formData: fd });
      setArquivo(null);
      setMsg("Anexo enviado.");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erro no upload.");
    }
  }

  async function avancarFluxo() {
    if (!g) return;
    setError("");
    if (g.status === "aberta") {
      if (!g.nf_remessa && !nfRemessa) {
        setError("Vincule a NF de remessa antes de marcar como enviada.");
        return;
      }
      if (nfRemessa && !g.nf_remessa) {
        const ok = await vincularNota("remessa", nfRemessa);
        if (!ok) return;
      }
      await mudarStatus("enviada");
    } else if (g.status === "enviada") {
      await mudarStatus("em_analise");
    }
  }

  if (loading) return <p className="text-muted">Carregando ficha...</p>;
  if (!g) return <p className="text-red">{error || "Garantia não encontrada."}</p>;

  const showEstoqueWarning = g.status !== "procedente";
  const movimentosHref = `/movimentos-globus?peca=${encodeURIComponent(pecaCodigo)}&veiculo=${encodeURIComponent(
    g.veiculo_codigo || ""
  )}`;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold">{g.protocolo}</h2>
          <p className="text-sm text-muted">
            {g.peca_nome} · veículo {g.veiculo_codigo} · {g.fornecedor_nome}
          </p>
          {pecaCodigo ? (
            <Link
              to={movimentosHref}
              className="mt-2 inline-flex text-sm text-cyan hover:underline"
            >
              Ver movimentos desta peça no Globus
            </Link>
          ) : null}
        </div>
        <BadgeStatus status={g.status} />
      </div>

      {showEstoqueWarning ? (
        <div className="rounded-lg border border-amber/40 bg-amber/10 px-4 py-3 text-sm text-amber">
          Estoque do Globo não deve ser movimentado neste status.
        </div>
      ) : (
        <div className="rounded-lg border border-green/40 bg-green/10 px-4 py-3 text-sm text-green">
          Procedente: informe apenas o número espelho da NF de entrada no Globo (texto). O
          RastroGlobus não movimenta estoque.
        </div>
      )}

      {error ? <p className="text-sm text-red">{error}</p> : null}
      {msg ? <p className="text-sm text-green">{msg}</p> : null}

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="space-y-3 rounded-xl border border-line bg-panel p-4 text-sm">
          <h3 className="font-semibold">Dados</h3>
          <p>
            <span className="text-muted">Valor:</span>{" "}
            {g.valor_peca
              ? Number(g.valor_peca).toLocaleString("pt-BR", {
                  style: "currency",
                  currency: "BRL",
                })
              : "—"}
          </p>
          <p>
            <span className="text-muted">Km:</span> {g.km_aplicacao ?? "—"}
          </p>
          <p>
            <span className="text-muted">Req. anterior / atual:</span>{" "}
            {g.requisicao_anterior || "—"} / {g.requisicao_atual || "—"}
          </p>
          <p>
            <span className="text-muted">Dias aberta:</span> {g.dias_aberta}
          </p>
          <p>
            <span className="text-muted">Observações:</span> {g.observacoes || "—"}
          </p>
          <p>
            <span className="text-muted">Laudo:</span> {g.laudo_resumo || "—"}
          </p>
          {g.motivo_improcedente ? (
            <p>
              <span className="text-muted">Motivo improcedente:</span> {g.motivo_improcedente}
            </p>
          ) : null}
        </section>

        <section className="space-y-3 rounded-xl border border-line bg-panel p-4 text-sm">
          <h3 className="font-semibold">Notas fiscais</h3>
          <p>
            <span className="text-muted">NF compra:</span> {g.nf_compra || "—"}
          </p>
          <p>
            <span className="text-muted">NF remessa:</span> {g.nf_remessa || "—"}
          </p>
          <p>
            <span className="text-muted">NF retorno:</span> {g.nf_retorno || "—"}
          </p>
          <p>
            <span className="text-muted">NF entrada Globo:</span>{" "}
            {g.status === "procedente" ? g.nf_entrada_globo || "—" : "(só em procedente)"}
          </p>

          {allowNf ? (
            <div className="space-y-2 border-t border-line pt-3">
              <label className="block text-xs text-muted">Data emissão NF</label>
              <input
                type="date"
                className={field}
                value={nfData}
                onChange={(e) => setNfData(e.target.value)}
              />
              <div className="flex flex-wrap gap-2">
                <input
                  className={field}
                  placeholder="Nº NF remessa"
                  value={nfRemessa}
                  onChange={(e) => setNfRemessa(e.target.value)}
                />
                <button
                  type="button"
                  className="shrink-0 rounded-lg border border-line px-3 text-cyan disabled:opacity-60"
                  disabled={buscandoNf === "remessa"}
                  onClick={() =>
                    buscarNoGlobus("remessa", nfRemessa, (n, d) => {
                      setNfRemessa(n);
                      if (d) setNfData(d);
                    })
                  }
                >
                  {buscandoNf === "remessa" ? "…" : "Buscar Globus"}
                </button>
                <button
                  type="button"
                  className="shrink-0 rounded-lg border border-line px-3 text-cyan"
                  onClick={() => vincularNota("remessa", nfRemessa)}
                >
                  Vincular remessa
                </button>
              </div>
              <div className="flex flex-wrap gap-2">
                <input
                  className={field}
                  placeholder="Nº NF retorno"
                  value={nfRetorno}
                  onChange={(e) => setNfRetorno(e.target.value)}
                />
                <button
                  type="button"
                  className="shrink-0 rounded-lg border border-line px-3 text-cyan disabled:opacity-60"
                  disabled={buscandoNf === "retorno"}
                  onClick={() =>
                    buscarNoGlobus("retorno", nfRetorno, (n, d) => {
                      setNfRetorno(n);
                      if (d) setNfData(d);
                    })
                  }
                >
                  {buscandoNf === "retorno" ? "…" : "Buscar Globus"}
                </button>
                <button
                  type="button"
                  className="shrink-0 rounded-lg border border-line px-3 text-cyan"
                  onClick={() => vincularNota("retorno", nfRetorno)}
                >
                  Vincular retorno
                </button>
              </div>
            </div>
          ) : null}
        </section>

        <section className="space-y-3 rounded-xl border border-line bg-panel p-4 text-sm lg:col-span-2">
          <div className="flex flex-wrap items-end justify-between gap-2">
            <div>
              <h3 className="font-semibold">NFs garantia Globus (NEG/NFG)</h3>
              <p className="text-xs text-muted">
                Espelho Oracle — não altera estoque e não define improcedente.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <input
                className={`${field} w-40`}
                placeholder="Nº NF…"
                value={qNfGarantia}
                onChange={(e) => setQNfGarantia(e.target.value)}
              />
              <button
                type="button"
                className="rounded-lg border border-line px-3 text-cyan disabled:opacity-60"
                disabled={loadingNfsGarantia}
                onClick={() =>
                  carregarNfsGarantia({
                    numero: qNfGarantia.trim() || undefined,
                    peca: pecaCodigo || undefined,
                  })
                }
              >
                {loadingNfsGarantia ? "…" : "Buscar"}
              </button>
              {pecaCodigo ? (
                <button
                  type="button"
                  className="rounded-lg border border-line px-3 text-cyan disabled:opacity-60"
                  disabled={loadingNfsGarantia}
                  onClick={() => carregarNfsGarantia({ peca: pecaCodigo })}
                >
                  Por peça
                </button>
              ) : null}
            </div>
          </div>

          {avisoNfsGarantia ? (
            <div className="rounded-lg border border-amber/40 bg-amber/10 px-3 py-2 text-xs text-amber">
              {avisoNfsGarantia}
            </div>
          ) : null}

          <div className="overflow-x-auto rounded-lg border border-line">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="border-b border-line text-muted">
                <tr>
                  <th className="px-3 py-2 font-medium">NF</th>
                  <th className="px-3 py-2 font-medium">Tipo</th>
                  <th className="px-3 py-2 font-medium">Data</th>
                  <th className="px-3 py-2 font-medium">Valor</th>
                  <th className="px-3 py-2 font-medium">Fornecedor</th>
                  <th className="px-3 py-2 font-medium">Usar</th>
                </tr>
              </thead>
              <tbody>
                {nfsGarantia.map((nf, idx) => (
                  <tr
                    key={`${nf.cod_int_nf || nf.numero}-${nf.peca_codigo}-${idx}`}
                    className="border-t border-line"
                  >
                    <td className="px-3 py-2">
                      <div>
                        {nf.numero}
                        {nf.serie ? ` / ${nf.serie}` : ""}
                      </div>
                      {nf.peca_codigo ? (
                        <div className="text-xs text-muted">{nf.peca_codigo}</div>
                      ) : null}
                    </td>
                    <td className="px-3 py-2">{nf.tipo_doc || "—"}</td>
                    <td className="px-3 py-2 whitespace-nowrap">
                      {nf.data_emissao
                        ? String(nf.data_emissao).slice(0, 10)
                        : nf.data_entrada
                          ? String(nf.data_entrada).slice(0, 10)
                          : "—"}
                    </td>
                    <td className="px-3 py-2">
                      {nf.valor != null && nf.valor !== ""
                        ? Number(nf.valor).toLocaleString("pt-BR", {
                            style: "currency",
                            currency: "BRL",
                          })
                        : "—"}
                    </td>
                    <td className="px-3 py-2 text-xs">{nf.fornecedor_nome || "—"}</td>
                    <td className="px-3 py-2">
                      {allowNf ? (
                        <div className="flex flex-wrap gap-1">
                          <button
                            type="button"
                            className="rounded border border-line px-2 py-0.5 text-xs text-cyan"
                            onClick={() => usarNfComo("remessa", nf)}
                          >
                            Remessa
                          </button>
                          <button
                            type="button"
                            className="rounded border border-line px-2 py-0.5 text-xs text-cyan"
                            onClick={() => usarNfComo("retorno", nf)}
                          >
                            Retorno
                          </button>
                        </div>
                      ) : (
                        <span className="text-xs text-muted">—</span>
                      )}
                    </td>
                  </tr>
                ))}
                {!loadingNfsGarantia && !nfsGarantia.length ? (
                  <tr>
                    <td colSpan={6} className="px-3 py-4 text-center text-muted">
                      Nenhuma NF NEG/NFG encontrada para esta peça/número.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      {showActions ? (
        <section className="space-y-3 rounded-xl border border-line bg-panel p-4">
          <h3 className="font-semibold">Ações</h3>
          {(allowAdvance || allowClose) && (
            <textarea
              className={field}
              rows={2}
              placeholder="Descrição / observação comercial"
              value={descricao}
              onChange={(e) => setDescricao(e.target.value)}
            />
          )}
          {allowAdvance && (g.status === "aberta" || g.status === "enviada") && (
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={avancarFluxo}
                className="rounded-lg bg-amber/20 px-4 py-2 text-sm text-amber"
              >
                {g.status === "aberta" ? "Marcar como enviada" : "Marcar em análise"}
              </button>
              {allowCancel && (
                <button
                  type="button"
                  onClick={() => mudarStatus("cancelada")}
                  className="rounded-lg border border-muted/40 px-4 py-2 text-sm text-muted"
                >
                  Cancelar garantia
                </button>
              )}
            </div>
          )}

          {allowClose && g.status === "em_analise" && (
            <div className="space-y-3">
              <div>
                <label className="mb-1 block text-xs text-muted">
                  NF entrada Globo (somente texto, só procedente)
                </label>
                <div className="flex flex-wrap gap-2">
                  <input
                    className={field}
                    value={nfGlobo}
                    onChange={(e) => setNfGlobo(e.target.value)}
                    placeholder="Ex: ENT-9901"
                  />
                  <button
                    type="button"
                    className="shrink-0 rounded-lg border border-line px-3 text-sm text-cyan disabled:opacity-60"
                    disabled={buscandoNf === "globo"}
                    onClick={() =>
                      buscarNoGlobus("globo", nfGlobo, (n) => setNfGlobo(n))
                    }
                  >
                    {buscandoNf === "globo" ? "…" : "Buscar Globus"}
                  </button>
                </div>
              </div>
              <div>
                <label className="mb-1 block text-xs text-muted">
                  Motivo improcedente (obrigatório com laudo)
                </label>
                <input
                  className={field}
                  value={motivo}
                  onChange={(e) => setMotivo(e.target.value)}
                />
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  className="rounded-lg bg-green/20 px-4 py-2 text-sm text-green"
                  onClick={() => mudarStatus("procedente")}
                >
                  Marcar procedente
                </button>
                <button
                  type="button"
                  className="rounded-lg bg-red/20 px-4 py-2 text-sm text-red"
                  onClick={() => mudarStatus("improcedente")}
                >
                  Improcedente
                </button>
                <button
                  type="button"
                  className="rounded-lg bg-violet/20 px-4 py-2 text-sm text-violet"
                  onClick={() => mudarStatus("cortesia")}
                >
                  Cortesia
                </button>
              </div>
            </div>
          )}

          {allowAnexar ? (
            <form
              onSubmit={uploadAnexo}
              className="flex flex-wrap items-end gap-2 border-t border-line pt-3"
            >
              <div>
                <label className="mb-1 block text-xs text-muted">Anexar PDF</label>
                <input
                  type="file"
                  accept=".pdf,image/*"
                  onChange={(e) => setArquivo(e.target.files?.[0] || null)}
                />
              </div>
              <button
                type="submit"
                className="rounded-lg border border-line px-3 py-2 text-sm text-cyan"
              >
                Enviar anexo
              </button>
            </form>
          ) : null}
        </section>
      ) : (
        <p className="text-sm text-muted">Perfil somente leitura — sem ações de alteração.</p>
      )}

      <section className="rounded-xl border border-line bg-panel p-4">
        <h3 className="mb-3 font-semibold">Timeline</h3>
        <Timeline eventos={g.eventos || []} />
      </section>

      {g.anexos?.length ? (
        <section className="rounded-xl border border-line bg-panel p-4">
          <h3 className="mb-3 font-semibold">Anexos</h3>
          <ul className="space-y-2 text-sm">
            {g.anexos.map((a) => (
              <li key={a.id}>
                <a
                  className="text-cyan hover:underline"
                  href={a.arquivo}
                  target="_blank"
                  rel="noreferrer"
                >
                  {a.descricao || "Arquivo"} — {new Date(a.enviado_em).toLocaleString("pt-BR")}
                </a>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
