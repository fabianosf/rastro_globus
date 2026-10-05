import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { canCreateGarantia } from "../auth/permissions";
import {
  buscarPecasGlobus,
  buscarPecasLocal,
  buscarVeiculosGlobus,
  buscarVeiculosLocal,
  GlobusPeca,
  GlobusVeiculo,
} from "../components/GlobusStatusBadge";

type Option = { id: number; label: string };

function useDebounced(value: string, ms: number) {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = window.setTimeout(() => setV(value), ms);
    return () => window.clearTimeout(t);
  }, [value, ms]);
  return v;
}

function codigoVeiculoStr(v: Pick<GlobusVeiculo, "codigo" | "codigo_veic_globus">) {
  return String(v.codigo_veic_globus ?? v.codigo ?? "").trim();
}

function labelVeiculo(v: GlobusVeiculo) {
  const pref = v.prefixo || v.descricao || "";
  const cod = codigoVeiculoStr(v);
  const base = pref && String(pref) !== cod ? `${pref} (${cod})` : cod || String(pref);
  return v.placa ? `${base} · ${v.placa}` : base;
}

const field =
  "w-full rounded-lg border border-line bg-bg px-3 py-2 text-sm outline-none focus:border-cyan";

function toDateInput(value?: string) {
  if (!value) return "";
  const s = String(value).trim();
  if (/^\d{4}-\d{2}-\d{2}/.test(s)) return s.slice(0, 10);
  const m = s.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (m) return `${m[3]}-${m[2]}-${m[1]}`;
  const m2 = s.match(/^(\d{2})-(\d{2})-(\d{4})$/);
  if (m2) return `${m2[3]}-${m2[2]}-${m2[1]}`;
  return "";
}

/** Máscara DD/MM/AAAA enquanto digita (só números). */
function maskDateBr(value: string) {
  const digits = value.replace(/\D/g, "").slice(0, 8);
  if (digits.length <= 2) return digits;
  if (digits.length <= 4) return `${digits.slice(0, 2)}/${digits.slice(2)}`;
  return `${digits.slice(0, 2)}/${digits.slice(2, 4)}/${digits.slice(4)}`;
}

/** Código interno local: até 40 chars (modelo Peca). */
function codigoPecaLocal(texto: string) {
  const t = texto.trim().replace(/\s+/g, " ");
  if (t.length <= 40) return t;
  return t.slice(0, 40);
}

/** Digitação livre de valor: só dígitos e um separador decimal. */
function maskValorInput(raw: string) {
  const normalized = raw.replace(/\./g, ",").replace(/[^\d,]/g, "");
  const comma = normalized.indexOf(",");
  if (comma === -1) return normalized;
  const intPart = normalized.slice(0, comma).replace(/,/g, "");
  const decPart = normalized.slice(comma + 1).replace(/,/g, "").slice(0, 2);
  return `${intPart},${decPart}`;
}

/** Completa zeros: 500 → 500,00; 5,5 → 5,50. */
function formatValorBr(raw: string) {
  const t = raw.trim();
  if (!t) return "";
  const n = Number(t.replace(/\./g, "").replace(",", "."));
  if (!Number.isFinite(n)) return "";
  return n.toFixed(2).replace(".", ",");
}

/** "500,00" → "500.00" para a API. */
function valorToApi(br: string) {
  const formatted = formatValorBr(br);
  if (!formatted) return null;
  return formatted.replace(",", ".");
}

export default function GarantiaDanfe() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const allowed = canCreateGarantia(user?.perfil);

  const [fornecedores, setFornecedores] = useState<Option[]>([]);
  const [veiculo, setVeiculo] = useState("");
  const [peca, setPeca] = useState("");
  const [fornecedor, setFornecedor] = useState("");
  const [veiculoLabel, setVeiculoLabel] = useState("");
  const [pecaLabel, setPecaLabel] = useState("");
  const [qVeiculo, setQVeiculo] = useState("");
  const [qPeca, setQPeca] = useState("");
  const [qFornecedor, setQFornecedor] = useState("");
  const [hitsVeiculo, setHitsVeiculo] = useState<GlobusVeiculo[]>([]);
  const [hitsPeca, setHitsPeca] = useState<GlobusPeca[]>([]);

  const [nfRemessa, setNfRemessa] = useState("");
  const [nfSerie, setNfSerie] = useState("1");
  const [nfRemessaData, setNfRemessaData] = useState("");
  const [chaveNfe, setChaveNfe] = useState("");
  const [nfOrigem, setNfOrigem] = useState("");
  const [nfOrigemData, setNfOrigemData] = useState("");
  const [valor, setValor] = useState("");
  const [defeito, setDefeito] = useState("");
  const [fotoDanfe, setFotoDanfe] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(false);

  const qVeiculoDebounced = useDebounced(qVeiculo.trim(), 350);
  const qPecaDebounced = useDebounced(qPeca.trim(), 350);

  const fornecedoresFiltrados = useMemo(() => {
    const q = qFornecedor.trim().toLowerCase();
    let list = !q
      ? fornecedores
      : fornecedores.filter((f) => f.label.toLowerCase().includes(q));
    if (fornecedor && !list.some((f) => String(f.id) === fornecedor)) {
      const cur = fornecedores.find((f) => String(f.id) === fornecedor);
      if (cur) list = [cur, ...list];
    }
    return list;
  }, [fornecedores, qFornecedor, fornecedor]);

  useEffect(() => {
    if (!allowed) return;
    api<Array<{ id: number; nome_fantasia: string; razao_social: string }>>("/api/fornecedores/")
      .then((f) =>
        setFornecedores(
          f.map((x) => ({ id: x.id, label: x.nome_fantasia || x.razao_social }))
        )
      )
      .catch((e) => setError(e instanceof ApiError ? e.message : "Erro ao carregar fornecedores."));
  }, [allowed]);

  useEffect(() => {
    if (!allowed || qVeiculoDebounced.length < 2) {
      setHitsVeiculo([]);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        let rows = await buscarVeiculosLocal(qVeiculoDebounced);
        if (!rows.length) rows = await buscarVeiculosGlobus(qVeiculoDebounced);
        if (!cancelled) setHitsVeiculo(rows);
      } catch {
        if (!cancelled) setHitsVeiculo([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [qVeiculoDebounced, allowed]);

  useEffect(() => {
    if (!allowed || qPecaDebounced.length < 2) {
      setHitsPeca([]);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        let rows = await buscarPecasLocal(qPecaDebounced);
        if (!rows.length) rows = await buscarPecasGlobus(qPecaDebounced);
        if (cancelled) return;
        setHitsPeca(rows);
        const lower = qPecaDebounced.toLowerCase();
        const exact = rows.find((p) => p.codigo_interno.toLowerCase() === lower);
        if (exact) {
          setPecaLabel(`${exact.codigo_interno} — ${exact.descricao || exact.codigo_interno}`);
        }
      } catch {
        if (!cancelled) setHitsPeca([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [qPecaDebounced, allowed]);

  async function escolherVeiculo(v: GlobusVeiculo) {
    const codigo = codigoVeiculoStr(v);
    if (!codigo) {
      setError("Veículo sem código Globus.");
      return;
    }
    try {
      const local = await api<{ id: number; codigo: string }>("/api/veiculos/ensure/", {
        method: "POST",
        body: {
          codigo,
          placa: v.placa || "",
          descricao: v.descricao || v.prefixo || `Veiculo ${codigo}`,
        },
      });
      setVeiculo(String(local.id));
      setVeiculoLabel(labelVeiculo({ ...v, codigo: local.codigo }));
      setHitsVeiculo([]);
      setQVeiculo(codigo);
      setMsg(`Veículo ${local.codigo} selecionado.`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Falha ao espelhar veículo.");
    }
  }

  async function escolherPeca(p: GlobusPeca) {
    try {
      const local = await api<{ id: number; codigo_interno: string; descricao: string }>(
        "/api/pecas/ensure/",
        {
          method: "POST",
          body: {
            codigo_interno: p.codigo_interno,
            descricao: p.descricao || p.codigo_interno,
          },
        }
      );
      setPeca(String(local.id));
      setPecaLabel(`${local.codigo_interno} — ${local.descricao}`);
      setHitsPeca([]);
      setQPeca(local.codigo_interno);
      setMsg(`Peça ${local.codigo_interno} selecionada.`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Falha ao espelhar peça.");
    }
  }

  async function ensureFornecedorPorNome() {
    const nome = qFornecedor.trim();
    if (!nome) return fornecedor;
    if (fornecedor) return fornecedor;
    const forn = await api<{ id: number; nome_fantasia: string; razao_social: string }>(
      "/api/fornecedores/ensure/",
      {
        method: "POST",
        body: {
          codigo_externo: "",
          nome_fantasia: nome,
          razao_social: nome,
        },
      }
    );
    setFornecedor(String(forn.id));
    setFornecedores((prev) => {
      if (prev.some((x) => x.id === forn.id)) return prev;
      return [...prev, { id: forn.id, label: forn.nome_fantasia || forn.razao_social }];
    });
    return String(forn.id);
  }

  /** Grava o texto digitado; usa Globus só se código/descrição forem exatamente iguais. */
  async function resolvePecaId(): Promise<string> {
    if (peca) return peca;
    const texto = qPeca.trim();
    if (!texto) return "";
    let hits = hitsPeca.length ? hitsPeca : await buscarPecasLocal(texto);
    if (!hits.length) {
      try {
        hits = await buscarPecasGlobus(texto);
      } catch {
        hits = [];
      }
    }
    const lower = texto.toLowerCase();
    const match =
      hits.find((p) => p.codigo_interno.toLowerCase() === lower) ||
      hits.find((p) => (p.descricao || "").toLowerCase() === lower);
    const codigoInterno = match?.codigo_interno || codigoPecaLocal(texto);
    const descricao = (match?.descricao || texto).slice(0, 255);
    const local = await api<{ id: number; codigo_interno: string; descricao: string }>(
      "/api/pecas/ensure/",
      {
        method: "POST",
        body: {
          codigo_interno: codigoInterno,
          descricao,
        },
      }
    );
    setPeca(String(local.id));
    setPecaLabel(`${local.codigo_interno} — ${local.descricao}`);
    setHitsPeca([]);
    return String(local.id);
  }

  /** CARRO digitado na DANFE — não troca por outro da lista. */
  async function resolveVeiculoId(): Promise<string> {
    if (veiculo) return veiculo;
    const codigo = qVeiculo.trim();
    if (!codigo) return "";
    let hits = hitsVeiculo.length ? hitsVeiculo : await buscarVeiculosLocal(codigo);
    if (!hits.length) {
      try {
        hits = await buscarVeiculosGlobus(codigo);
      } catch {
        hits = [];
      }
    }
    const lower = codigo.toLowerCase();
    const match = hits.find(
      (v) =>
        codigoVeiculoStr(v).toLowerCase() === lower ||
        String(v.prefixo || "").toLowerCase() === lower
    );
    const cod = codigo;
    const local = await api<{ id: number; codigo: string }>("/api/veiculos/ensure/", {
      method: "POST",
      body: {
        codigo: cod,
        placa: match?.placa || "",
        descricao: match?.descricao || match?.prefixo || `Veiculo ${cod}`,
      },
    });
    setVeiculo(String(local.id));
    setVeiculoLabel(
      labelVeiculo({ ...(match || { codigo: cod }), codigo: local.codigo })
    );
    setHitsVeiculo([]);
    return String(local.id);
  }

  if (!allowed) {
    return <Navigate to="/" replace />;
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setMsg("");
    if (!nfRemessa.trim()) {
      setError("Informe o número da NF remessa.");
      return;
    }
    const dataRemessaIso = toDateInput(nfRemessaData);
    if (!dataRemessaIso) {
      setError("Informe a data de emissão da DANFE (ex.: 16/07/2026).");
      return;
    }
    if (!nfOrigem.trim()) {
      setError("Informe a NF de origem citada nas informações complementares (ex.: 39511).");
      return;
    }
    if (!peca && !qPeca.trim()) {
      setError("Informe o código ou o nome do produto da DANFE.");
      return;
    }
    if (!veiculo && !qVeiculo.trim()) {
      setError("Informe o CARRO / código do veículo da DANFE (ex.: 30059).");
      return;
    }
    if (!fotoDanfe) {
      setError("Anexe a foto ou PDF da DANFE para registrar.");
      return;
    }
    const dataOrigemIso = toDateInput(nfOrigemData) || dataRemessaIso;
    const dataAplicacao = dataOrigemIso;
    setLoading(true);
    try {
      const [pecaId, veiculoId, fornId] = await Promise.all([
        resolvePecaId(),
        resolveVeiculoId(),
        ensureFornecedorPorNome(),
      ]);
      if (!pecaId || !veiculoId) {
        setError(
          "Não foi possível espelhar veículo ou peça. Confira o texto digitado (código ou nome)."
        );
        setLoading(false);
        return;
      }
      if (!fornId) {
        setError("Informe o fornecedor destinatário (ex.: JHC AUTO IMPORTS).");
        setLoading(false);
        return;
      }
      const obsParts = [
        defeito.trim() ? `DEFEITO: ${defeito.trim()}` : "",
        chaveNfe.trim() ? `Chave NFe remessa: ${chaveNfe.trim()}` : "",
        `Remessa DANFE NF ${nfRemessa.trim()}${nfSerie.trim() ? ` série ${nfSerie.trim()}` : ""}.`,
        "Caso aberto na remessa — improcedente só após análise na ficha.",
      ].filter(Boolean);

      const created = await api<{ id: number; status: string }>("/api/garantias/", {
        method: "POST",
        body: {
          veiculo: Number(veiculoId),
          peca: Number(pecaId),
          fornecedor: Number(fornId),
          nf_venda_fornecedor: nfOrigem.trim(),
          nf_venda_data: dataAplicacao,
          data_aplicacao: dataAplicacao,
          nf_compra_numero: nfOrigem.trim(),
          nf_compra_data: dataAplicacao,
          valor_peca: valorToApi(valor),
          observacoes: obsParts.join(" "),
          laudo_resumo: defeito.trim() ? `Defeito informado: ${defeito.trim()}` : "",
          nf_remessa_numero: nfRemessa.trim(),
          nf_remessa_serie: nfSerie.trim(),
          nf_remessa_data: dataRemessaIso,
          chave_nfe_remessa: chaveNfe.replace(/\D/g, ""),
        },
      });

      try {
        const fd = new FormData();
        fd.append("arquivo", fotoDanfe);
        fd.append("descricao", "Foto DANFE");
        await api(`/api/garantias/${created.id}/anexos/`, {
          method: "POST",
          formData: fd,
        });
      } catch {
        navigate(`/garantias/${created.id}`, {
          state: {
            warning:
              "Remessa criada, mas o anexo da DANFE falhou. Anexe de novo abaixo.",
          },
        });
        return;
      }

      navigate(`/garantias/${created.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erro ao registrar remessa.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-lg font-semibold">Registrar a partir da DANFE</h2>
          <p className="text-xs text-muted">
            Digite a DANFE e salve no SGGI. Se o código da peça existir, a descrição preenche.
            CARRO: informe o número. Abre como <span className="text-amber">enviada</span>.
          </p>
        </div>
        <Link to="/" className="text-sm text-cyan hover:underline">
          Voltar às minhas NFs
        </Link>
      </div>

      <form onSubmit={onSubmit} className="space-y-4 rounded-xl border border-line bg-panel p-6">
        <section className="space-y-3">
          <h3 className="text-sm font-semibold text-cyan">NF remessa (DANFE emitida)</h3>
          <label className="block text-sm">
            <span className="mb-1 block text-muted">Nº NF *</span>
            <input
              className={field}
              value={nfRemessa}
              onChange={(e) => setNfRemessa(e.target.value)}
              placeholder="7427"
            />
          </label>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="text-sm">
              <span className="mb-1 block text-muted">Série</span>
              <input
                className={field}
                value={nfSerie}
                onChange={(e) => setNfSerie(e.target.value)}
                placeholder="1"
              />
            </label>
            <label className="text-sm">
              <span className="mb-1 block text-muted">Emissão * (obrigatório para salvar)</span>
              <input
                className={field}
                value={nfRemessaData}
                onChange={(e) => setNfRemessaData(maskDateBr(e.target.value))}
                placeholder="dd/MM/aaaa"
                inputMode="numeric"
                maxLength={10}
              />
              <span className="mt-1 block text-xs text-muted">
                Digite só os números; as barras entram sozinhas (ex.: 16072026 → 16/07/2026).
              </span>
            </label>
          </div>
          <label className="block text-sm">
            <span className="mb-1 block text-muted">Chave de acesso NFe (opcional)</span>
            <input
              className={field}
              value={chaveNfe}
              onChange={(e) => setChaveNfe(e.target.value)}
              placeholder="44 dígitos"
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block text-muted">Valor da peça (R$)</span>
            <input
              className={field}
              value={valor}
              onChange={(e) => setValor(maskValorInput(e.target.value))}
              onBlur={() => setValor((v) => formatValorBr(v))}
              placeholder="0,00"
              inputMode="decimal"
            />
          </label>
        </section>

        <section className="space-y-3 border-t border-line pt-4">
          <h3 className="text-sm font-semibold text-cyan">Produto / veículo / fornecedor</h3>

          <div>
            <label className="mb-1 block text-sm text-muted">
              Produto (código ou nome) * {pecaLabel ? `· ${pecaLabel}` : ""}
            </label>
            <input
              className={field}
              value={qPeca}
              onChange={(e) => {
                setQPeca(e.target.value);
                setPeca("");
                setPecaLabel("");
              }}
              placeholder="Ex.: 03120026 ou VALVULA…"
            />
            <p className="mt-1 text-xs text-muted">
              Se o código existir, a descrição preenche. Senão, grava o que você digitou.
            </p>
            {hitsPeca.length ? (
              <ul className="mt-1 max-h-36 overflow-auto rounded-lg border border-line bg-bg text-sm">
                {hitsPeca.map((p) => (
                  <li key={p.codigo_interno}>
                    <button
                      type="button"
                      className="w-full px-3 py-2 text-left hover:bg-cyan/10"
                      onClick={() => escolherPeca(p)}
                    >
                      {p.codigo_interno} — {p.descricao}
                    </button>
                  </li>
                ))}
              </ul>
            ) : null}
          </div>

          <div>
            <label className="mb-1 block text-sm text-muted">
              Veículo (CARRO) * {veiculoLabel ? `· ${veiculoLabel}` : ""}
            </label>
            <input
              className={field}
              value={qVeiculo}
              onChange={(e) => {
                setQVeiculo(e.target.value);
                setVeiculo("");
                setVeiculoLabel("");
              }}
              placeholder="Ex.: 30059"
            />
            <p className="mt-1 text-xs text-muted">
              Digite o CARRO da DANFE e salve — não precisa clicar na sugestão.
            </p>
            {hitsVeiculo.length ? (
              <ul className="mt-1 max-h-36 overflow-auto rounded-lg border border-line bg-bg text-sm">
                {hitsVeiculo.map((v) => (
                  <li key={v.codigo_veic_globus || v.codigo}>
                    <button
                      type="button"
                      className="w-full px-3 py-2 text-left hover:bg-cyan/10"
                      onClick={() => escolherVeiculo(v)}
                    >
                      {labelVeiculo(v)}
                    </button>
                  </li>
                ))}
              </ul>
            ) : null}
          </div>

          <label className="block text-sm">
            <span className="mb-1 block text-muted">Fornecedor destinatário *</span>
            <input
              className={field}
              value={qFornecedor}
              onChange={(e) => {
                setQFornecedor(e.target.value);
                setFornecedor("");
              }}
              placeholder="Ex.: JHC AUTO IMPORTS"
              list="danfe-fornecedores"
            />
            <datalist id="danfe-fornecedores">
              {fornecedoresFiltrados.slice(0, 20).map((f) => (
                <option key={f.id} value={f.label} />
              ))}
            </datalist>
            {fornecedoresFiltrados.length && qFornecedor.trim() ? (
              <ul className="mt-1 max-h-28 overflow-auto rounded-lg border border-line bg-bg text-sm">
                {fornecedoresFiltrados.slice(0, 8).map((f) => (
                  <li key={f.id}>
                    <button
                      type="button"
                      className="w-full px-3 py-2 text-left hover:bg-cyan/10"
                      onClick={() => {
                        setFornecedor(String(f.id));
                        setQFornecedor(f.label);
                      }}
                    >
                      {f.label}
                    </button>
                  </li>
                ))}
              </ul>
            ) : null}
          </label>

          <label className="block text-sm">
            <span className="mb-1 block text-muted">Defeito (infos complementares)</span>
            <input
              className={field}
              value={defeito}
              onChange={(e) => setDefeito(e.target.value)}
              placeholder="Ex.: VAZAMENTO"
            />
          </label>
        </section>

        <section className="space-y-3 border-t border-line pt-4">
          <h3 className="text-sm font-semibold text-cyan">NF origem (complementares)</h3>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="text-sm">
              <span className="mb-1 block text-muted">NF origem / compra *</span>
              <input
                className={field}
                value={nfOrigem}
                onChange={(e) => setNfOrigem(e.target.value)}
                placeholder="Ex.: 39511"
              />
            </label>
            <label className="text-sm">
              <span className="mb-1 block text-muted">Data NF origem (se souber)</span>
              <input
                className={field}
                value={nfOrigemData}
                onChange={(e) => setNfOrigemData(maskDateBr(e.target.value))}
                placeholder="dd/MM/aaaa"
                inputMode="numeric"
                maxLength={10}
              />
            </label>
          </div>
        </section>

        <section className="space-y-2 border-t border-line pt-4">
          <h3 className="text-sm font-semibold text-cyan">Foto / PDF da DANFE *</h3>
          <label className="block text-sm">
            <input
              type="file"
              accept="image/*,.pdf,application/pdf"
              capture="environment"
              className="block w-full text-sm text-muted file:mr-3 file:rounded-lg file:border-0 file:bg-cyan/20 file:px-3 file:py-1.5 file:text-sm file:font-semibold file:text-cyan"
              onChange={(e) => setFotoDanfe(e.target.files?.[0] || null)}
            />
            <span className="mt-1 block text-xs text-muted">
              Obrigatório para registrar. No celular, use a câmera se preferir.
            </span>
            {fotoDanfe ? (
              <span className="mt-1 block text-xs text-green">Selecionado: {fotoDanfe.name}</span>
            ) : null}
          </label>
        </section>

        {error ? <p className="text-sm text-red">{error}</p> : null}
        {msg ? <p className="text-sm text-green">{msg}</p> : null}

        <div className="flex flex-wrap gap-2 pt-2">
          <button
            type="submit"
            disabled={loading}
            className="rounded-lg bg-cyan px-4 py-2 text-sm font-semibold text-bg disabled:opacity-60"
          >
            {loading ? "Salvando…" : "Registrar remessa no SGGI"}
          </button>
          <Link
            to="/garantias/nova"
            className="rounded-lg border border-line px-4 py-2 text-sm text-muted hover:text-ink"
          >
            Formulário completo
          </Link>
        </div>
      </form>
    </div>
  );
}
