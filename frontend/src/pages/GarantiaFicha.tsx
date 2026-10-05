import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import {
  canAdvanceStatus,
  canAnexar,
  canCancel,
  canCloseStatus,
  canDeleteGarantia,
  canEditGarantia,
  canVincularNf,
} from "../auth/permissions";
import BadgeStatus from "../components/BadgeStatus";
import {
  buscarNfGlobus,
  buscarNfsGarantiaGlobus,
  labelNfGlobus,
  type GlobusNf,
} from "../components/GlobusStatusBadge";
import Timeline, { type Evento } from "../components/Timeline";

type Garantia = {
  id: number;
  protocolo: string;
  status: string;
  peca: number;
  veiculo: number;
  fornecedor: number;
  peca_nome: string;
  peca_detalhe?: { codigo_interno?: string; descricao?: string };
  veiculo_codigo: string;
  fornecedor_nome: string;
  nf_compra: string;
  nf_remessa: string;
  nf_remessa_serie?: string;
  nf_remessa_data?: string;
  chave_nfe_remessa?: string;
  nf_retorno: string;
  nf_entrada_globo: string;
  valor_peca: string | null;
  km_aplicacao: number | null;
  requisicao_anterior: string;
  requisicao_atual: string;
  observacoes: string;
  laudo_resumo: string;
  laudo_pdf?: string | null;
  motivo_improcedente: string;
  causa_improcedente?: string;
  responsavel_tipo?: string;
  responsavel_nome?: string;
  cobranca_interna?: boolean;
  observacao_cobranca?: string;
  nf_venda_fornecedor?: string;
  nf_venda_data?: string;
  data_aplicacao?: string;
  prazo_garantia_dias?: number | null;
  data_fim_garantia?: string | null;
  dias_garantia_restantes?: number | null;
  dias_aberta: number;
  eventos: Evento[];
  anexos: Array<{ id: number; descricao: string; arquivo: string; enviado_em: string }>;
};

const STATUS_ABERTO = new Set(["aberta", "enviada", "em_analise"]);

const field =
  "w-full rounded-lg border border-line bg-bg px-3 py-2 text-sm outline-none focus:border-cyan";

export default function GarantiaFicha() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const [g, setG] = useState<Garantia | null>(null);
  const [error, setError] = useState(
    () => (location.state as { warning?: string } | null)?.warning || ""
  );
  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(true);
  const [savingEdit, setSavingEdit] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const [editNfRemessa, setEditNfRemessa] = useState("");
  const [editNfSerie, setEditNfSerie] = useState("");
  const [editNfData, setEditNfData] = useState("");
  const [editChave, setEditChave] = useState("");
  const [editValor, setEditValor] = useState("");
  const [editPecaCod, setEditPecaCod] = useState("");
  const [editVeiculo, setEditVeiculo] = useState("");
  const [editFornecedor, setEditFornecedor] = useState("");
  const [editDefeito, setEditDefeito] = useState("");
  const [editNfOrigem, setEditNfOrigem] = useState("");
  const [editNfOrigemData, setEditNfOrigemData] = useState("");

  const [nfRemessa, setNfRemessa] = useState("");
  const [nfRetorno, setNfRetorno] = useState("");
  const [nfData, setNfData] = useState(new Date().toISOString().slice(0, 10));
  const [descricao, setDescricao] = useState("");
  const [motivo, setMotivo] = useState("");
  const [causa, setCausa] = useState("erro_aplicacao");
  const [respTipo, setRespTipo] = useState("oficina");
  const [respNome, setRespNome] = useState("");
  const [cobrancaInterna, setCobrancaInterna] = useState(true);
  const [obsCobranca, setObsCobranca] = useState("");
  const [nfGlobo, setNfGlobo] = useState("");
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [buscandoNf, setBuscandoNf] = useState<"remessa" | "retorno" | "globo" | null>(null);
  const [hitsNfGlobus, setHitsNfGlobus] = useState<GlobusNf[]>([]);
  const [hitsNfTipo, setHitsNfTipo] = useState<"remessa" | "retorno" | "globo" | null>(null);
  const nfPickRef = useRef<{
    onFound: (numero: string, dataEmissao?: string, valor?: string) => void;
    numero: string;
  } | null>(null);
  const [nfsGarantia, setNfsGarantia] = useState<GlobusNf[]>([]);
  const [qNfGarantia, setQNfGarantia] = useState("");
  const [avisoNfsGarantia, setAvisoNfsGarantia] = useState("");
  const [loadingNfsGarantia, setLoadingNfsGarantia] = useState(false);
  const [laudoEdit, setLaudoEdit] = useState("");
  const [savingLaudo, setSavingLaudo] = useState(false);

  const perfil = user?.perfil;
  const allowNf = canVincularNf(perfil);
  const allowAdvance = canAdvanceStatus(perfil);
  const allowClose = canCloseStatus(perfil);
  const allowEdit = canEditGarantia(perfil);
  const allowAnexar = canAnexar(perfil);
  const allowCancel = canCancel(perfil, g?.status);
  const allowDelete = canDeleteGarantia(perfil, g?.status);
  const podeEditarDanfe = allowEdit && !!g && STATUS_ABERTO.has(g.status);
  const showActions = allowNf || allowAdvance || allowClose || allowAnexar || allowCancel || allowEdit;

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

  useEffect(() => {
    if (!g) return;
    setLaudoEdit(g.laudo_resumo || "");
    setEditNfRemessa(g.nf_remessa || "");
    setEditNfSerie(g.nf_remessa_serie || "");
    setEditNfData((g.nf_remessa_data || "").slice(0, 10));
    setEditChave(g.chave_nfe_remessa || "");
    setEditValor(g.valor_peca != null ? String(g.valor_peca) : "");
    setEditPecaCod(
      g.peca_detalhe?.codigo_interno || (g.peca_nome || "").split(" - ")[0]?.trim() || ""
    );
    setEditVeiculo(g.veiculo_codigo || "");
    setEditFornecedor(g.fornecedor_nome || "");
    setEditDefeito(g.laudo_resumo || "");
    setEditNfOrigem(g.nf_venda_fornecedor || g.nf_compra || "");
    setEditNfOrigemData((g.nf_venda_data || g.data_aplicacao || "").slice(0, 10));
  }, [g]);

  // código da peça (uma única declaração no componente)
  const pecaCodigo =
    g?.peca_detalhe?.codigo_interno ||
    (g?.peca_nome || "").split(" - ")[0]?.trim() ||
    "";

  async function salvarDadosDanfe() {
    if (!g || !podeEditarDanfe) return;
    if (!editNfRemessa.trim()) {
      setError("Informe o número da NF remessa.");
      return;
    }
    if (!editNfData.trim()) {
      setError("Informe a data de emissão da DANFE.");
      return;
    }
    setSavingEdit(true);
    setError("");
    setMsg("");
    try {
      let pecaId = g.peca;
      let veiculoId = g.veiculo;
      let fornId = g.fornecedor;

      const pecaCod = editPecaCod.trim();
      if (pecaCod && pecaCod !== pecaCodigo) {
        const peca = await api<{ id: number }>("/api/pecas/ensure/", {
          method: "POST",
          body: { codigo_interno: pecaCod.slice(0, 40), descricao: pecaCod },
        });
        pecaId = peca.id;
      }

      const veicCod = editVeiculo.trim();
      if (veicCod && veicCod !== g.veiculo_codigo) {
        const veic = await api<{ id: number }>("/api/veiculos/ensure/", {
          method: "POST",
          body: { codigo: veicCod, descricao: `Veículo ${veicCod}` },
        });
        veiculoId = veic.id;
      }

      const fornNome = editFornecedor.trim();
      if (fornNome && fornNome !== g.fornecedor_nome) {
        const forn = await api<{ id: number }>("/api/fornecedores/ensure/", {
          method: "POST",
          body: {
            nome_fantasia: fornNome,
            razao_social: fornNome,
          },
        });
        fornId = forn.id;
      }

      const origem = editNfOrigem.trim();
      const origemData = (editNfOrigemData || editNfData).slice(0, 10);
      const updated = await api<Garantia>(`/api/garantias/${g.id}/`, {
        method: "PATCH",
        body: {
          peca: pecaId,
          veiculo: veiculoId,
          fornecedor: fornId,
          valor_peca: editValor || null,
          observacoes: g.observacoes,
          laudo_resumo: editDefeito.trim(),
          nf_venda_fornecedor: origem || g.nf_venda_fornecedor || editNfRemessa.trim(),
          nf_venda_data: origemData,
          data_aplicacao: origemData,
          nf_remessa_numero: editNfRemessa.trim(),
          nf_remessa_serie: editNfSerie.trim(),
          nf_remessa_data: editNfData.slice(0, 10),
          chave_nfe_remessa: editChave.replace(/\D/g, ""),
          nf_compra_numero: origem || undefined,
          nf_compra_data: origem ? origemData : undefined,
        },
      });
      setG(updated);
      setMsg("Dados salvos.");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Erro ao salvar.");
    } finally {
      setSavingEdit(false);
    }
  }

  async function excluirGarantia() {
    if (!g || !allowDelete) return;
    const ok = window.confirm(
      `Excluir ${g.protocolo}${g.nf_remessa ? ` (NF ${g.nf_remessa})` : ""}? Esta ação não tem volta.`
    );
    if (!ok) return;
    setDeleting(true);
    setError("");
    try {
      await api(`/api/garantias/${g.id}/`, { method: "DELETE" });
      navigate("/");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Erro ao excluir.");
      setDeleting(false);
    }
  }

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
          "NFs Globus = espelho. Improcedente: seção Ações abaixo (só em análise / manutenção)."
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

  function aplicarNfEncontrada(
    tipo: "remessa" | "retorno" | "globo",
    nf: GlobusNf,
    onFound: (numero: string, dataEmissao?: string, valor?: string) => void,
    numeroBusca: string
  ) {
    setHitsNfGlobus([]);
    setHitsNfTipo(null);
    const dataIso = nf.data_emissao ? String(nf.data_emissao).slice(0, 10) : undefined;
    onFound(nf.numero || numeroBusca, dataIso, nf.valor ? String(nf.valor) : undefined);
    setMsg(
      `Globus (24 meses): NF ${nf.numero} · ${tipo} (somente leitura).`
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
    setHitsNfGlobus([]);
    setHitsNfTipo(null);
    setBuscandoNf(tipo);
    try {
      const rows = await buscarNfGlobus(numero.trim(), { meses: 24 });
      if (!rows.length) {
        setError("NF não encontrada nos últimos 24 meses no Globus.");
        return;
      }
      if (rows.length === 1) {
        aplicarNfEncontrada(tipo, rows[0], onFound, numero);
        return;
      }
      setHitsNfGlobus(rows);
      setHitsNfTipo(tipo);
      nfPickRef.current = { onFound, numero };
      setMsg(
        `${rows.length} NFs nos últimos 24 meses. Selecione a correta para ${tipo}.`
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

  async function salvarLaudo(): Promise<boolean> {
    if (!g) return false;
    setError("");
    setMsg("");
    setSavingLaudo(true);
    try {
      const updated = await api<Garantia>(`/api/garantias/${g.id}/`, {
        method: "PATCH",
        body: { laudo_resumo: laudoEdit },
      });
      setG(updated);
      setMsg("Laudo atualizado.");
      return true;
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Erro ao salvar laudo.");
      return false;
    } finally {
      setSavingLaudo(false);
    }
  }

  async function mudarStatus(status: string): Promise<boolean> {
    if (!g) return false;
    setError("");
    setMsg("");
    if (status === "improcedente") {
      const temLaudo = Boolean((g.laudo_resumo || "").trim() || g.laudo_pdf);
      const laudoDraft = (laudoEdit || "").trim();
      if (!temLaudo && laudoDraft) {
        const okLaudo = await salvarLaudo();
        if (!okLaudo) return false;
      } else if (!temLaudo && !laudoDraft) {
        setError(
          "Improcedente exige laudo (resumo ou PDF no campo laudo). Preencha o laudo na seção Ações antes de fechar."
        );
        return false;
      }
    }
    try {
      const updated = await api<Garantia>(`/api/garantias/${g.id}/status/`, {
        method: "POST",
        body: {
          status,
          descricao,
          motivo_improcedente: motivo,
          causa_improcedente: status === "improcedente" ? causa : "",
          responsavel_tipo: status === "improcedente" ? respTipo : "",
          responsavel_nome: status === "improcedente" ? respNome : "",
          cobranca_interna: status === "improcedente" ? cobrancaInterna : false,
          observacao_cobranca: status === "improcedente" ? obsCobranca : "",
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

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link to="/" className="text-xs text-cyan hover:underline">
            ← Minhas NFs
          </Link>
          <h2 className="text-xl font-semibold">{g.protocolo}</h2>
          <p className="text-sm text-muted">
            {g.peca_nome} · CARRO {g.veiculo_codigo} · {g.fornecedor_nome}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <BadgeStatus status={g.status} />
          {allowDelete ? (
            <button
              type="button"
              disabled={deleting}
              onClick={() => void excluirGarantia()}
              className="rounded-lg border border-red/40 px-3 py-1.5 text-sm text-red disabled:opacity-50"
            >
              {deleting ? "Excluindo…" : "Excluir"}
            </button>
          ) : null}
        </div>
      </div>

      {showEstoqueWarning ? (
        <div className="rounded-lg border border-amber/40 bg-amber/10 px-4 py-3 text-sm text-amber">
          Estoque do Globo não deve ser movimentado neste status.
        </div>
      ) : (
        <div className="rounded-lg border border-green/40 bg-green/10 px-4 py-3 text-sm text-green">
          Procedente: informe apenas o número espelho da NF de entrada no Globo (texto). O
          SGGI não movimenta estoque.
        </div>
      )}

      {error ? <p className="text-sm text-red">{error}</p> : null}
      {msg ? <p className="text-sm text-green">{msg}</p> : null}

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="space-y-3 rounded-xl border border-line bg-panel p-4 text-sm">
          <h3 className="font-semibold">Dados</h3>
          {podeEditarDanfe ? (
            <div className="space-y-3">
              <div className="grid gap-2 sm:grid-cols-2">
                <label>
                  <span className="mb-1 block text-xs text-muted">Nº NF remessa *</span>
                  <input
                    className={field}
                    value={editNfRemessa}
                    onChange={(e) => setEditNfRemessa(e.target.value)}
                  />
                </label>
                <label>
                  <span className="mb-1 block text-xs text-muted">Série</span>
                  <input
                    className={field}
                    value={editNfSerie}
                    onChange={(e) => setEditNfSerie(e.target.value)}
                  />
                </label>
                <label>
                  <span className="mb-1 block text-xs text-muted">Emissão *</span>
                  <input
                    type="date"
                    className={field}
                    value={editNfData}
                    onChange={(e) => setEditNfData(e.target.value)}
                  />
                </label>
                <label>
                  <span className="mb-1 block text-xs text-muted">Valor</span>
                  <input
                    className={field}
                    value={editValor}
                    onChange={(e) => setEditValor(e.target.value)}
                  />
                </label>
                <label className="sm:col-span-2">
                  <span className="mb-1 block text-xs text-muted">Chave NFe (opcional)</span>
                  <input
                    className={field}
                    value={editChave}
                    onChange={(e) => setEditChave(e.target.value)}
                  />
                </label>
                <label>
                  <span className="mb-1 block text-xs text-muted">Peça (código)</span>
                  <input
                    className={field}
                    value={editPecaCod}
                    onChange={(e) => setEditPecaCod(e.target.value)}
                  />
                </label>
                <label>
                  <span className="mb-1 block text-xs text-muted">CARRO</span>
                  <input
                    className={field}
                    value={editVeiculo}
                    onChange={(e) => setEditVeiculo(e.target.value)}
                  />
                </label>
                <label className="sm:col-span-2">
                  <span className="mb-1 block text-xs text-muted">Fornecedor</span>
                  <input
                    className={field}
                    value={editFornecedor}
                    onChange={(e) => setEditFornecedor(e.target.value)}
                  />
                </label>
                <label>
                  <span className="mb-1 block text-xs text-muted">NF origem</span>
                  <input
                    className={field}
                    value={editNfOrigem}
                    onChange={(e) => setEditNfOrigem(e.target.value)}
                  />
                </label>
                <label>
                  <span className="mb-1 block text-xs text-muted">Data NF origem</span>
                  <input
                    type="date"
                    className={field}
                    value={editNfOrigemData}
                    onChange={(e) => setEditNfOrigemData(e.target.value)}
                  />
                </label>
                <label className="sm:col-span-2">
                  <span className="mb-1 block text-xs text-muted">Defeito / laudo</span>
                  <input
                    className={field}
                    value={editDefeito}
                    onChange={(e) => setEditDefeito(e.target.value)}
                  />
                </label>
              </div>
              <button
                type="button"
                disabled={savingEdit}
                onClick={() => void salvarDadosDanfe()}
                className="rounded-lg bg-cyan px-4 py-2 text-sm font-semibold text-bg disabled:opacity-60"
              >
                {savingEdit ? "Salvando…" : "Salvar alterações"}
              </button>
            </div>
          ) : (
            <>
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
                <span className="text-muted">NF venda / origem:</span>{" "}
                {g.nf_venda_fornecedor || "—"}
                {g.nf_venda_data ? ` · ${String(g.nf_venda_data).slice(0, 10)}` : ""}
              </p>
              <p>
                <span className="text-muted">Observações:</span> {g.observacoes || "—"}
              </p>
              <p>
                <span className="text-muted">Laudo:</span>{" "}
                {g.laudo_resumo || (g.laudo_pdf ? "PDF anexado" : "—")}
              </p>
              {g.causa_improcedente ? (
                <p>
                  <span className="text-muted">Causa improcedente:</span> {g.causa_improcedente}
                </p>
              ) : null}
            </>
          )}
        </section>

        <section className="space-y-3 rounded-xl border border-line bg-panel p-4 text-sm">
          <h3 className="font-semibold">NFs SGGI</h3>
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
                  className="shrink-0 rounded-lg border border-line px-3 text-cyan"
                  onClick={() => vincularNota("retorno", nfRetorno)}
                >
                  Vincular retorno
                </button>
              </div>

              <details className="rounded-lg border border-line bg-bg/40 px-3 py-2">
                <summary className="cursor-pointer text-xs text-muted hover:text-ink">
                  Buscar no Globus (opcional)
                </summary>
                <div className="mt-2 space-y-2 border-t border-line pt-2">
                  <p className="text-xs text-muted">Últimos 24 meses · somente leitura.</p>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      className="rounded-lg border border-line px-3 py-1.5 text-xs text-cyan disabled:opacity-60"
                      disabled={buscandoNf === "remessa" || !nfRemessa.trim()}
                      onClick={() =>
                        buscarNoGlobus("remessa", nfRemessa, (n, d) => {
                          setNfRemessa(n);
                          if (d) setNfData(d);
                        })
                      }
                    >
                      {buscandoNf === "remessa" ? "…" : "Globus → remessa"}
                    </button>
                    <button
                      type="button"
                      className="rounded-lg border border-line px-3 py-1.5 text-xs text-cyan disabled:opacity-60"
                      disabled={buscandoNf === "retorno" || !nfRetorno.trim()}
                      onClick={() =>
                        buscarNoGlobus("retorno", nfRetorno, (n, d) => {
                          setNfRetorno(n);
                          if (d) setNfData(d);
                        })
                      }
                    >
                      {buscandoNf === "retorno" ? "…" : "Globus → retorno"}
                    </button>
                  </div>
                  {hitsNfGlobus.length && hitsNfTipo ? (
                    <ul className="max-h-40 overflow-auto rounded-lg border border-line bg-bg text-sm">
                      {hitsNfGlobus.map((nf, idx) => (
                        <li key={`${nf.cod_int_nf ?? nf.numero}-${nf.serie}-${idx}`}>
                          <button
                            type="button"
                            className="w-full px-3 py-2 text-left hover:bg-cyan/10"
                            onClick={() => {
                              const ctx = nfPickRef.current;
                              if (!ctx || !hitsNfTipo) return;
                              aplicarNfEncontrada(hitsNfTipo, nf, ctx.onFound, ctx.numero);
                            }}
                          >
                            {labelNfGlobus(nf)}
                          </button>
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              </details>
            </div>
          ) : null}
        </section>
      </div>

      <section
        id="acoes"
        className="space-y-3 rounded-xl border border-line bg-panel p-4 scroll-mt-4"
      >
        <div>
          <h3 className="font-semibold">Ações</h3>
          <p className="text-xs text-muted">
            Decisão no SGGI — não grava estoque Globus. Fluxo: Oficina cadastra → Compras
            avança → Manutenção fecha.
          </p>
        </div>

        {!allowClose && g.status === "em_analise" ? (
          <div className="rounded-lg border border-amber/40 bg-amber/10 px-3 py-2 text-xs text-amber">
            Esta garantia está em análise. Apenas manutenção (ou admin) pode fechar como
            procedente / improcedente / cortesia.
          </div>
        ) : null}

        {!allowClose && g.status !== "em_analise" && !["procedente", "improcedente", "cortesia", "cancelada"].includes(g.status) ? (
          <div className="rounded-lg border border-line bg-bg/60 px-3 py-2 text-xs text-muted">
            Próximo passo:{" "}
            {g.status === "aberta"
              ? "Compras vincula NF de remessa e marca como enviada."
              : g.status === "enviada"
                ? "Compras/manutenção marca em análise; depois manutenção fecha."
                : "Aguarde o fluxo operacional."}
            {perfil === "direcao" ? " Seu perfil (direção) é somente leitura nas decisões." : ""}
          </div>
        ) : null}

        {allowEdit &&
        !["procedente", "improcedente", "cortesia", "cancelada"].includes(g.status) ? (
          <div className="space-y-2 border-b border-line pb-3">
            <label className="block text-xs text-muted">
              Laudo (resumo) — obrigatório para improcedente
            </label>
            <textarea
              className={field}
              rows={3}
              value={laudoEdit}
              onChange={(e) => setLaudoEdit(e.target.value)}
              placeholder="Descreva o laudo técnico…"
            />
            <button
              type="button"
              disabled={savingLaudo}
              onClick={() => salvarLaudo()}
              className="rounded-lg border border-line px-3 py-1.5 text-sm text-cyan disabled:opacity-60"
            >
              {savingLaudo ? "Salvando…" : "Salvar laudo"}
            </button>
          </div>
        ) : null}

        {showActions ? (
          <>
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
              <div className="space-y-4">
                <p className="text-sm font-medium text-ink">
                  Decisão no SGGI — não grava estoque Globus
                </p>

                <div className="space-y-3 rounded-lg border border-green/30 bg-green/5 p-3">
                  <h4 className="text-sm font-semibold text-green">Fechar procedente</h4>
                  <p className="text-xs text-muted">
                    Informe o número espelho da NF de entrada no Globo (texto). Não movimenta estoque.
                  </p>
                  <div>
                    <label className="mb-1 block text-xs text-muted">NF entrada Globo</label>
                    <input
                      className={field}
                      value={nfGlobo}
                      onChange={(e) => setNfGlobo(e.target.value)}
                      placeholder="Ex: ENT-9901"
                    />
                    <details className="mt-2 rounded-lg border border-line bg-bg/40 px-3 py-2">
                      <summary className="cursor-pointer text-xs text-muted hover:text-ink">
                        Buscar no Globus (opcional)
                      </summary>
                      <button
                        type="button"
                        className="mt-2 rounded-lg border border-line px-3 py-1.5 text-xs text-cyan disabled:opacity-60"
                        disabled={buscandoNf === "globo" || !nfGlobo.trim()}
                        onClick={() =>
                          buscarNoGlobus("globo", nfGlobo, (n) => setNfGlobo(n))
                        }
                      >
                        {buscandoNf === "globo" ? "…" : "Confirmar NF nos últimos 24 meses"}
                      </button>
                    </details>
                  </div>
                  <button
                    type="button"
                    className="rounded-lg bg-green/20 px-4 py-2 text-sm text-green"
                    onClick={() => mudarStatus("procedente")}
                  >
                    Marcar procedente
                  </button>
                </div>

                <div className="space-y-3 rounded-lg border border-red/30 bg-red/5 p-3">
                  <h4 className="text-sm font-semibold text-red">
                    Fechar improcedente / cortesia
                  </h4>
                  <p className="text-xs text-muted">
                    Laudo ou PDF obrigatório para improcedente. Globus não registra esta decisão.
                  </p>
                  {!((g.laudo_resumo || "").trim() || g.laudo_pdf || (laudoEdit || "").trim()) ? (
                    <p className="text-xs text-amber">
                      Laudo vazio — preencha o laudo acima antes de marcar improcedente.
                    </p>
                  ) : null}
                  <div className="grid gap-2 sm:grid-cols-2">
                    <label className="text-xs">
                      <span className="mb-1 block text-muted">Causa improcedente *</span>
                      <select
                        className={field}
                        value={causa}
                        onChange={(e) => setCausa(e.target.value)}
                      >
                        <option value="erro_aplicacao">Erro aplicacao (oficina)</option>
                        <option value="erro_operacao">Erro operacao (motorista)</option>
                        <option value="falha_sistemica_veiculo">Falha sistemica veiculo</option>
                        <option value="outro">Outro</option>
                      </select>
                    </label>
                    <label className="text-xs">
                      <span className="mb-1 block text-muted">Responsavel tipo *</span>
                      <select
                        className={field}
                        value={respTipo}
                        onChange={(e) => setRespTipo(e.target.value)}
                      >
                        <option value="oficina">Oficina</option>
                        <option value="mecanico">Mecanico</option>
                        <option value="motorista">Motorista</option>
                        <option value="sistema">Sistema</option>
                        <option value="outro">Outro</option>
                      </select>
                    </label>
                    <label className="text-xs sm:col-span-2">
                      <span className="mb-1 block text-muted">Responsavel nome</span>
                      <input
                        className={field}
                        value={respNome}
                        onChange={(e) => setRespNome(e.target.value)}
                        placeholder="Obrigatorio exceto tipo=sistema"
                      />
                    </label>
                    <label className="flex items-center gap-2 text-xs sm:col-span-2">
                      <input
                        type="checkbox"
                        checked={cobrancaInterna}
                        onChange={(e) => setCobrancaInterna(e.target.checked)}
                      />
                      Cobranca interna
                    </label>
                    <label className="text-xs sm:col-span-2">
                      <span className="mb-1 block text-muted">Obs. cobranca</span>
                      <input
                        className={field}
                        value={obsCobranca}
                        onChange={(e) => setObsCobranca(e.target.value)}
                      />
                    </label>
                    <label className="text-xs sm:col-span-2">
                      <span className="mb-1 block text-muted">Motivo / detalhe</span>
                      <input
                        className={field}
                        value={motivo}
                        onChange={(e) => setMotivo(e.target.value)}
                      />
                    </label>
                  </div>
                  <div className="flex flex-wrap gap-2">
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
          </>
        ) : (
          <p className="text-sm text-muted">Perfil somente leitura — sem ações de alteração.</p>
        )}
      </section>

      <details className="rounded-xl border border-line bg-panel p-4 text-sm">
        <summary className="cursor-pointer font-semibold text-muted hover:text-ink">
          NFs garantia Globus (NEG/NFG) — opcional
        </summary>
        <div className="mt-3 space-y-3 border-t border-line pt-3">
          <p className="text-xs text-muted">
            Espelho Globus. Improcedente fecha na seção Ações (só em análise / manutenção).
          </p>
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
                      Abra e busque para listar NEG/NFG desta peça.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </div>
      </details>

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
