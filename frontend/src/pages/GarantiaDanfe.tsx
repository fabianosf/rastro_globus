import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { api, ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { canCloseStatus, canCreateGarantia } from "../auth/permissions";
import {
  buscarPecasGlobus,
  buscarPecasLocal,
  buscarVeiculosGlobus,
  buscarVeiculosLocal,
  GlobusPeca,
  GlobusVeiculo,
} from "../components/GlobusStatusBadge";
import AnexoPickerPreview from "../components/AnexoPickerPreview";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

type Option = { id: number; label: string };

const DEFEITO_ATALHOS = ["Peça ruim", "Peça falha"] as const;

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

function maskDateBr(value: string) {
  const digits = value.replace(/\D/g, "").slice(0, 8);
  if (digits.length <= 2) return digits;
  if (digits.length <= 4) return `${digits.slice(0, 2)}/${digits.slice(2)}`;
  return `${digits.slice(0, 2)}/${digits.slice(2, 4)}/${digits.slice(4)}`;
}

function codigoPecaLocal(texto: string) {
  const t = texto.trim().replace(/\s+/g, " ");
  if (t.length <= 40) return t;
  return t.slice(0, 40);
}

function maskValorInput(raw: string) {
  const normalized = raw.replace(/\./g, ",").replace(/[^\d,]/g, "");
  const comma = normalized.indexOf(",");
  if (comma === -1) return normalized;
  const intPart = normalized.slice(0, comma).replace(/,/g, "");
  const decPart = normalized.slice(comma + 1).replace(/,/g, "").slice(0, 2);
  return `${intPart},${decPart}`;
}

function formatValorBr(raw: string) {
  const t = raw.trim();
  if (!t) return "";
  const n = Number(t.replace(/\./g, "").replace(",", "."));
  if (!Number.isFinite(n)) return "";
  return n.toFixed(2).replace(".", ",");
}

function valorToApi(br: string) {
  const formatted = formatValorBr(br);
  if (!formatted) return null;
  return formatted.replace(",", ".");
}

function nomeUsuario(user: {
  first_name?: string;
  last_name?: string;
  username?: string;
} | null) {
  if (!user) return "";
  const full = `${user.first_name || ""} ${user.last_name || ""}`.trim();
  return full || user.username || "";
}

export default function GarantiaDanfe() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const allowed = canCreateGarantia(user?.perfil);
  const podeFecharImp = canCloseStatus(user?.perfil);

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
  const [nfOrigem, setNfOrigem] = useState("");
  const [nfOrigemData, setNfOrigemData] = useState("");
  const [valor, setValor] = useState("");
  const [defeito, setDefeito] = useState("");
  const [observacao, setObservacao] = useState("");
  const [anexos, setAnexos] = useState<File[]>([]);
  const [comoImprocedente, setComoImprocedente] = useState(false);
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
        body: { codigo_interno: codigoInterno, descricao },
      }
    );
    setPeca(String(local.id));
    setPecaLabel(`${local.codigo_interno} — ${local.descricao}`);
    setHitsPeca([]);
    return String(local.id);
  }

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
    const local = await api<{ id: number; codigo: string }>("/api/veiculos/ensure/", {
      method: "POST",
      body: {
        codigo,
        placa: match?.placa || "",
        descricao: match?.descricao || match?.prefixo || `Veiculo ${codigo}`,
      },
    });
    setVeiculo(String(local.id));
    setVeiculoLabel(labelVeiculo({ ...(match || { codigo }), codigo: local.codigo }));
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
      setError("Informe o número da NF.");
      return;
    }
    const dataRemessaIso = toDateInput(nfRemessaData);
    if (!dataRemessaIso) {
      setError("Informe a data de emissão (ex.: 16/07/2026).");
      return;
    }
    if (!nfOrigem.trim()) {
      setError("Informe a NF de origem (ex.: 39511).");
      return;
    }
    if (!peca && !qPeca.trim()) {
      setError("Informe o código ou o nome da peça.");
      return;
    }
    if (!veiculo && !qVeiculo.trim()) {
      setError("Informe o CARRO / código do veículo.");
      return;
    }
    if (!anexos.length) {
      setError("Anexe ao menos um arquivo (foto, PDF ou DOC).");
      return;
    }
    const fecharImp = podeFecharImp && comoImprocedente;
    if (fecharImp && !defeito.trim()) {
      setError("Para improcedente, informe o defeito (ex.: Peça ruim).");
      return;
    }

    const dataOrigemIso = toDateInput(nfOrigemData) || dataRemessaIso;
    setLoading(true);
    try {
      const [pecaId, veiculoId, fornId] = await Promise.all([
        resolvePecaId(),
        resolveVeiculoId(),
        ensureFornecedorPorNome(),
      ]);
      if (!pecaId || !veiculoId) {
        setError("Não foi possível gravar peça ou veículo. Confira o texto.");
        setLoading(false);
        return;
      }
      if (!fornId) {
        setError("Informe o fornecedor.");
        setLoading(false);
        return;
      }

      const defeitoTxt = defeito.trim();
      const obsTxt = observacao.trim();
      const obsParts = [
        defeitoTxt ? `DEFEITO: ${defeitoTxt}` : "",
        obsTxt ? `OBS: ${obsTxt}` : "",
        `Remessa NF ${nfRemessa.trim()}${nfSerie.trim() ? ` série ${nfSerie.trim()}` : ""}.`,
        fecharImp
          ? "Registrada e encerrada como improcedente."
          : "Caso aberto na remessa — improcedente só após análise na ficha.",
      ].filter(Boolean);

      const created = await api<{ id: number; status: string }>("/api/garantias/", {
        method: "POST",
        body: {
          veiculo: Number(veiculoId),
          peca: Number(pecaId),
          fornecedor: Number(fornId),
          nf_venda_fornecedor: nfOrigem.trim(),
          nf_venda_data: dataOrigemIso,
          data_aplicacao: dataOrigemIso,
          nf_compra_numero: nfOrigem.trim(),
          nf_compra_data: dataOrigemIso,
          valor_peca: valorToApi(valor),
          observacoes: obsParts.join(" "),
          laudo_resumo: defeitoTxt ? `Defeito informado: ${defeitoTxt}` : "",
          nf_remessa_numero: nfRemessa.trim(),
          nf_remessa_serie: nfSerie.trim(),
          nf_remessa_data: dataRemessaIso,
          chave_nfe_remessa: "",
        },
      });

      let anexosOk = 0;
      const falhas: string[] = [];
      for (let i = 0; i < anexos.length; i += 1) {
        const file = anexos[i];
        try {
          const fd = new FormData();
          fd.append("arquivo", file);
          fd.append(
            "descricao",
            anexos.length === 1 ? "Comprovante da nota" : `Anexo ${i + 1}: ${file.name}`
          );
          await api(`/api/garantias/${created.id}/anexos/`, {
            method: "POST",
            formData: fd,
          });
          anexosOk += 1;
        } catch {
          falhas.push(file.name);
        }
      }
      if (anexosOk === 0) {
        toast.warning("Nota criada, mas nenhum anexo foi enviado. Anexe na ficha.");
        navigate(`/garantias/${created.id}`, {
          state: {
            warning: "Nota criada, mas nenhum anexo foi enviado. Anexe na ficha.",
          },
        });
        return;
      }

      const avisoAnexos = falhas.length
        ? `Falhou enviar: ${falhas.join(", ")}. Complete na ficha.`
        : "";

      if (fecharImp) {
        try {
          await api(`/api/garantias/${created.id}/fechar-improcedente-direto/`, {
            method: "POST",
            body: {
              descricao: "Encerrado na Nova remessa",
              motivo_improcedente: defeitoTxt,
              causa_improcedente: "outro",
              responsavel_tipo: "oficina",
              responsavel_nome: nomeUsuario(user),
              cobranca_interna: false,
              observacao_cobranca: "",
              laudo_resumo: `Defeito informado: ${defeitoTxt}`,
            },
          });
        } catch (err) {
          const avisoImp =
            err instanceof ApiError
              ? `Não fechou improcedente: ${err.message}`
              : "Não fechou improcedente. Feche na ficha.";
          toast.warning([avisoAnexos, avisoImp].filter(Boolean).join(" "));
          navigate(`/garantias/${created.id}`, {
            state: {
              warning: [avisoAnexos, avisoImp].filter(Boolean).join(" "),
            },
          });
          return;
        }
      }

      if (avisoAnexos) {
        toast.warning(avisoAnexos);
        navigate(`/garantias/${created.id}`, { state: { warning: avisoAnexos } });
        return;
      }

      toast.success(
        fecharImp ? "Nota salva e encerrada como improcedente." : "Nota cadastrada com sucesso."
      );
      navigate(`/garantias/${created.id}`);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Erro ao registrar remessa.";
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-lg font-semibold">Cadastrar nota</h2>
          <p className="text-xs text-muted">
            Informe a nota, anexe a foto e os dados básicos.
            {podeFecharImp ? " Pode já marcar como improcedente." : ""}
          </p>
        </div>
        <Link to="/" className="text-sm text-cyan hover:underline">
          Voltar às minhas NFs
        </Link>
      </div>

      <form onSubmit={onSubmit} className="space-y-4 rounded-xl border border-line bg-panel p-4 sm:p-6">
        <section className="space-y-3">
          <h3 className="text-sm font-semibold text-cyan">Nota fiscal</h3>
          <div className="grid min-w-0 gap-3 sm:grid-cols-3">
            <div className="min-w-0 sm:col-span-2">
              <Label htmlFor="nf-remessa">Nº NF remessa *</Label>
              <Input
                id="nf-remessa"
                value={nfRemessa}
                onChange={(e) => setNfRemessa(e.target.value)}
                placeholder="7427"
              />
            </div>
            <div>
              <Label htmlFor="nf-serie">Série</Label>
              <Input
                id="nf-serie"
                value={nfSerie}
                onChange={(e) => setNfSerie(e.target.value)}
                placeholder="1"
              />
            </div>
          </div>
          <div className="grid min-w-0 gap-3 sm:grid-cols-2">
            <div className="min-w-0">
              <Label htmlFor="nf-emissao">Emissão *</Label>
              <Input
                id="nf-emissao"
                value={nfRemessaData}
                onChange={(e) => setNfRemessaData(maskDateBr(e.target.value))}
                placeholder="dd/MM/aaaa"
                inputMode="numeric"
                maxLength={10}
              />
            </div>
            <div>
              <Label htmlFor="nf-valor">Valor (R$)</Label>
              <Input
                id="nf-valor"
                value={valor}
                onChange={(e) => setValor(maskValorInput(e.target.value))}
                onBlur={() => setValor((v) => formatValorBr(v))}
                placeholder="0,00"
                inputMode="decimal"
              />
            </div>
          </div>
          <div className="grid min-w-0 gap-3 sm:grid-cols-2">
            <div className="min-w-0">
              <Label htmlFor="nf-origem">NF origem *</Label>
              <Input
                id="nf-origem"
                value={nfOrigem}
                onChange={(e) => setNfOrigem(e.target.value)}
                placeholder="Ex.: 39511"
              />
            </div>
            <div>
              <Label htmlFor="nf-origem-data">Data NF origem</Label>
              <Input
                id="nf-origem-data"
                value={nfOrigemData}
                onChange={(e) => setNfOrigemData(maskDateBr(e.target.value))}
                placeholder="dd/MM/aaaa"
                inputMode="numeric"
                maxLength={10}
              />
            </div>
          </div>
        </section>

        <section className="space-y-3 border-t border-line pt-4">
          <h3 className="text-sm font-semibold text-cyan">Peça / veículo / fornecedor</h3>

          <div>
            <Label htmlFor="peca-q">
              Peça * {pecaLabel ? `· ${pecaLabel}` : ""}
            </Label>
            <Input
              id="peca-q"
              value={qPeca}
              onChange={(e) => {
                setQPeca(e.target.value);
                setPeca("");
                setPecaLabel("");
              }}
              placeholder="Código ou nome"
              autoComplete="off"
            />
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
            <Label htmlFor="veiculo-q">
              Veículo (CARRO) * {veiculoLabel ? `· ${veiculoLabel}` : ""}
            </Label>
            <Input
              id="veiculo-q"
              value={qVeiculo}
              onChange={(e) => {
                setQVeiculo(e.target.value);
                setVeiculo("");
                setVeiculoLabel("");
              }}
              placeholder="Ex.: 30059"
              autoComplete="off"
            />
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

          <div>
            <Label htmlFor="fornecedor-q">Fornecedor *</Label>
            <Input
              id="fornecedor-q"
              value={qFornecedor}
              onChange={(e) => {
                setQFornecedor(e.target.value);
                setFornecedor("");
              }}
              placeholder="Nome do fornecedor"
              list="danfe-fornecedores"
              autoComplete="off"
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
          </div>

          <div>
            <Label>Defeito</Label>
            <div className="mb-2 flex flex-wrap gap-2">
              {DEFEITO_ATALHOS.map((label) => (
                <Button
                  key={label}
                  type="button"
                  size="sm"
                  variant={defeito === label ? "default" : "outline"}
                  onClick={() => setDefeito(label)}
                >
                  {label}
                </Button>
              ))}
            </div>
            <Input
              value={defeito}
              onChange={(e) => setDefeito(e.target.value)}
              placeholder="Peça ruim, peça falha ou descreva…"
            />
          </div>

          <div>
            <Label htmlFor="observacao">Observação (opcional)</Label>
            <Textarea
              id="observacao"
              className="min-h-[96px] resize-y"
              value={observacao}
              onChange={(e) => setObservacao(e.target.value)}
              placeholder="O que aconteceu, falha, quem reportou…"
              rows={4}
            />
          </div>
        </section>

        <section className="space-y-2 border-t border-line pt-4">
          <h3 className="text-sm font-semibold text-cyan">Anexos (comprovante) *</h3>
          <AnexoPickerPreview
            files={anexos}
            onChange={setAnexos}
            multiple
            label="Selecionar arquivo(s)"
            hint="Foto, PDF ou DOC. Confira a prévia — pode trocar ou remover antes de salvar."
          />
        </section>

        {podeFecharImp ? (
          <label className="flex items-start gap-2 rounded-lg border border-line bg-bg/40 px-3 py-3 text-sm">
            <input
              type="checkbox"
              className="mt-0.5"
              checked={comoImprocedente}
              onChange={(e) => setComoImprocedente(e.target.checked)}
            />
            <span>
              <span className="font-semibold">Já é improcedente</span>
              <span className="mt-0.5 block text-xs text-muted">
                Salva a nota com os anexos e encerra na hora (informe o defeito).
              </span>
            </span>
          </label>
        ) : null}

        {error ? <p className="text-sm text-red">{error}</p> : null}
        {msg ? <p className="text-sm text-green">{msg}</p> : null}

        <div className="flex flex-wrap gap-2 border-t border-line pt-4">
          <Button type="submit" disabled={loading} size="lg" className="w-full sm:w-auto">
            {loading
              ? "Salvando…"
              : podeFecharImp && comoImprocedente
                ? "Salvar e fechar improcedente"
                : "Salvar nota"}
          </Button>
        </div>
      </form>
    </div>
  );
}
