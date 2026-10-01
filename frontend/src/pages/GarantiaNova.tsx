import { FormEvent, KeyboardEvent, useEffect, useMemo, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { canCreateGarantia } from "../auth/permissions";
import GlobusStatusBadge, {
  buscarNfGlobus,
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

function labelVeiculo(v: GlobusVeiculo) {
  const pref = v.prefixo || v.descricao || "";
  const cod = v.codigo_veic_globus || v.codigo;
  const base = pref && pref !== cod ? `${pref} (${cod})` : cod;
  return v.placa ? `${base} · ${v.placa}` : base;
}

export default function GarantiaNova() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [veiculosLocais, setVeiculosLocais] = useState<Option[]>([]);
  const [pecasLocais, setPecasLocais] = useState<Option[]>([]);
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
  const [nfCompra, setNfCompra] = useState("");
  const [nfVenda, setNfVenda] = useState("");
  const [nfVendaData, setNfVendaData] = useState("");
  const [dataAplicacao, setDataAplicacao] = useState("");
  const [reqAnt, setReqAnt] = useState("");
  const [reqAtual, setReqAtual] = useState("");
  const [km, setKm] = useState("");
  const [valor, setValor] = useState("");
  const [obs, setObs] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [buscandoNf, setBuscandoNf] = useState(false);
  const [buscandoVeiculo, setBuscandoVeiculo] = useState(false);
  const [buscandoPeca, setBuscandoPeca] = useState(false);
  const [msgGlobus, setMsgGlobus] = useState("");
  const [globusOffline, setGlobusOffline] = useState(false);
  const allowed = canCreateGarantia(user?.perfil);

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
    Promise.all([
      api<Array<{ id: number; codigo: string }>>("/api/veiculos/"),
      api<Array<{ id: number; codigo_interno: string; descricao: string }>>("/api/pecas/"),
      api<Array<{ id: number; nome_fantasia: string; razao_social: string }>>("/api/fornecedores/"),
    ])
      .then(([v, p, f]) => {
        setVeiculosLocais(v.map((x) => ({ id: x.id, label: x.codigo })));
        setPecasLocais(
          p.map((x) => ({ id: x.id, label: `${x.codigo_interno} — ${x.descricao}` }))
        );
        setFornecedores(
          f.map((x) => ({ id: x.id, label: x.nome_fantasia || x.razao_social }))
        );
      })
      .catch((e) => setError(e instanceof ApiError ? e.message : "Erro ao carregar cadastros."));
  }, [allowed]);

  async function buscarVeiculoLocal(query?: string) {
    const q = (query ?? qVeiculo).trim();
    if (q.length < 2) {
      setHitsVeiculo([]);
      return;
    }
    setError("");
    setMsgGlobus("");
    setBuscandoVeiculo(true);
    try {
      const rows = await buscarVeiculosLocal(q);
      setHitsVeiculo(rows);
      setGlobusOffline(false);
      if (!rows.length) {
        setMsgGlobus("Nenhum veiculo no espelho local. Tente sync_globus ou busca ao vivo.");
      } else {
        setMsgGlobus(`Espelho local: ${rows.length} veiculo(s).`);
      }
    } catch (e) {
      setHitsVeiculo([]);
      setError(e instanceof ApiError ? e.message : "Falha ao buscar veiculos locais.");
    } finally {
      setBuscandoVeiculo(false);
    }
  }

  async function buscarVeiculoAoVivo() {
    if (qVeiculo.trim().length < 2) {
      setError("Informe ao menos 2 caracteres para buscar veiculo no Globus ao vivo.");
      return;
    }
    setError("");
    setMsgGlobus("");
    setBuscandoVeiculo(true);
    try {
      const rows = await buscarVeiculosGlobus(qVeiculo.trim());
      setHitsVeiculo(rows);
      setGlobusOffline(false);
      if (!rows.length) setMsgGlobus("Nenhum veiculo encontrado no Globus ao vivo.");
      else setMsgGlobus(`Globus ao vivo: ${rows.length} veiculo(s).`);
    } catch (e) {
      setHitsVeiculo([]);
      setGlobusOffline(true);
      setError(e instanceof ApiError ? e.message : "Falha ao buscar veiculos no Globus ao vivo.");
    } finally {
      setBuscandoVeiculo(false);
    }
  }

  async function buscarPecaLocal(query?: string) {
    const q = (query ?? qPeca).trim();
    if (q.length < 2) {
      setHitsPeca([]);
      return;
    }
    setError("");
    setMsgGlobus("");
    setBuscandoPeca(true);
    try {
      const rows = await buscarPecasLocal(q);
      setHitsPeca(rows);
      setGlobusOffline(false);
      if (!rows.length) {
        setMsgGlobus("Nenhuma peca no espelho local. Tente sync_globus ou busca ao vivo.");
      } else {
        setMsgGlobus(`Espelho local: ${rows.length} peca(s).`);
      }
    } catch (e) {
      setHitsPeca([]);
      setError(e instanceof ApiError ? e.message : "Falha ao buscar pecas locais.");
    } finally {
      setBuscandoPeca(false);
    }
  }

  async function buscarPecaAoVivo() {
    if (qPeca.trim().length < 2) {
      setError("Informe ao menos 2 caracteres para buscar peca no Globus ao vivo.");
      return;
    }
    setError("");
    setMsgGlobus("");
    setBuscandoPeca(true);
    try {
      const rows = await buscarPecasGlobus(qPeca.trim());
      setHitsPeca(rows);
      setGlobusOffline(false);
      if (!rows.length) setMsgGlobus("Nenhuma peca encontrada no Globus ao vivo.");
      else setMsgGlobus(`Globus ao vivo: ${rows.length} peca(s).`);
    } catch (e) {
      setHitsPeca([]);
      setGlobusOffline(true);
      setError(e instanceof ApiError ? e.message : "Falha ao buscar pecas no Globus ao vivo.");
    } finally {
      setBuscandoPeca(false);
    }
  }

  useEffect(() => {
    if (!allowed) return;
    if (qVeiculoDebounced.length < 2) {
      setHitsVeiculo([]);
      return;
    }
    void buscarVeiculoLocal(qVeiculoDebounced);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- debounce dispara busca local
  }, [qVeiculoDebounced, allowed]);

  useEffect(() => {
    if (!allowed) return;
    if (qPecaDebounced.length < 2) {
      setHitsPeca([]);
      return;
    }
    void buscarPecaLocal(qPecaDebounced);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [qPecaDebounced, allowed]);

  async function escolherVeiculo(v: GlobusVeiculo) {
    setError("");
    const codigo = (v.codigo_veic_globus || v.codigo || "").trim();
    if (!codigo) {
      setError("Veiculo sem codigo Globus.");
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
      setQVeiculo("");
      setMsgGlobus(`Veiculo ${local.codigo} espelhado no RastroGlobus (somente leitura Globus).`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Falha ao espelhar veiculo.");
    }
  }

  async function escolherPeca(p: GlobusPeca) {
    setError("");
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
      setQPeca("");
      setMsgGlobus(`Peca ${local.codigo_interno} espelhada no RastroGlobus (somente leitura Globus).`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Falha ao espelhar peca.");
    }
  }

  async function buscarNfCompra() {
    if (!nfCompra.trim()) {
      setError("Informe o numero da NF compra para buscar no Globus.");
      return;
    }
    setError("");
    setMsgGlobus("");
    setBuscandoNf(true);
    try {
      const rows = await buscarNfGlobus(nfCompra.trim());
      if (!rows.length) {
        setMsgGlobus("NF nao encontrada no Globus (somente leitura).");
        return;
      }
      const nf = rows[0];
      setNfCompra(nf.numero || nfCompra);
      if (nf.valor) setValor(String(nf.valor));
      setGlobusOffline(false);

      const nomeForn = nf.fornecedor_nome || "";
      const codForn = nf.codigo_fornecedor != null ? String(nf.codigo_fornecedor) : "";
      if (nomeForn || codForn) {
        try {
          const forn = await api<{ id: number; nome_fantasia: string; razao_social: string }>(
            "/api/fornecedores/ensure/",
            {
              method: "POST",
              body: {
                codigo_externo: codForn,
                nome_fantasia: nomeForn || `Fornecedor ${codForn}`,
                razao_social: nomeForn || `Fornecedor Globus ${codForn}`,
              },
            }
          );
          setFornecedor(String(forn.id));
          setQFornecedor(forn.nome_fantasia || forn.razao_social || "");
          setFornecedores((prev) => {
            if (prev.some((x) => x.id === forn.id)) return prev;
            return [
              ...prev,
              { id: forn.id, label: forn.nome_fantasia || forn.razao_social },
            ];
          });
        } catch {
          /* fornecedor opcional; NF e valor ja preenchidos */
        }
      }

      setMsgGlobus(
        `Globus: NF ${nf.numero}${nf.serie ? ` serie ${nf.serie}` : ""}` +
          (nf.data_emissao ? ` · ${String(nf.data_emissao).slice(0, 10)}` : "") +
          (nomeForn ? ` · ${nomeForn}` : "") +
          " (espelho — sem movimentar estoque)."
      );
    } catch (e) {
      setGlobusOffline(true);
      setError(e instanceof ApiError ? e.message : "Falha ao buscar NF no Globus.");
    } finally {
      setBuscandoNf(false);
    }
  }

  function onSearchKeyDown(
    e: KeyboardEvent<HTMLInputElement>,
    action: () => void | Promise<void>
  ) {
    if (e.key !== "Enter") return;
    e.preventDefault();
    void action();
  }

  if (!allowed) {
    return <Navigate to="/garantias" replace />;
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (!veiculo || !peca || !fornecedor) {
      setError("Selecione veiculo, peca e fornecedor.");
      return;
    }
    if (!nfVenda.trim() || !nfVendaData || !dataAplicacao) {
      setError("Informe NF de venda do fornecedor (numero + data) e data de aplicacao.");
      return;
    }
    setLoading(true);
    try {
      const created = await api<{ id: number }>("/api/garantias/", {
        method: "POST",
        body: {
          veiculo: Number(veiculo),
          peca: Number(peca),
          fornecedor: Number(fornecedor),
          nf_compra_numero: nfCompra,
          nf_venda_fornecedor: nfVenda.trim(),
          nf_venda_data: nfVendaData,
          data_aplicacao: dataAplicacao,
          requisicao_anterior: reqAnt,
          requisicao_atual: reqAtual,
          km_aplicacao: km ? Number(km) : null,
          valor_peca: valor || null,
          observacoes: obs,
          laudo_resumo: obs,
        },
      });
      navigate(`/garantias/${created.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erro ao criar garantia.");
    } finally {
      setLoading(false);
    }
  }

  const field =
    "w-full rounded-lg border border-line bg-bg px-3 py-2 text-sm outline-none focus:border-cyan";

  return (
    <div className="mx-auto max-w-2xl">
      <form onSubmit={onSubmit} className="space-y-4 rounded-xl border border-line bg-panel p-6">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm text-muted">
            Digite para buscar no espelho local (Enter ou aguarde). Oracle so no botao ao vivo. Nao
            movimenta estoque.
          </p>
          <GlobusStatusBadge />
        </div>

        {globusOffline ? (
          <div className="rounded-lg border border-amber/40 bg-amber/10 px-3 py-2 text-xs text-amber">
            Oracle ao vivo indisponivel — continue com o espelho local ou cadastro RG.
          </div>
        ) : null}

        <div>
          <label className="mb-1 block text-sm text-muted">Veiculo (espelho local)</label>
          <div className="flex flex-wrap gap-2">
            <input
              className={`${field} min-w-[12rem] flex-1`}
              placeholder="Prefixo, placa ou codigo…"
              value={qVeiculo}
              onChange={(e) => setQVeiculo(e.target.value)}
              onKeyDown={(e) => onSearchKeyDown(e, () => buscarVeiculoLocal())}
            />
            <button
              type="button"
              onClick={() => void buscarVeiculoLocal()}
              disabled={buscandoVeiculo}
              className="shrink-0 rounded-lg border border-line px-3 text-sm text-cyan disabled:opacity-60"
            >
              {buscandoVeiculo ? "…" : "Buscar local"}
            </button>
            <button
              type="button"
              onClick={() => void buscarVeiculoAoVivo()}
              disabled={buscandoVeiculo}
              className="shrink-0 rounded-lg border border-line px-3 text-sm text-muted disabled:opacity-60"
            >
              Buscar no Globus ao vivo
            </button>
          </div>
          {veiculoLabel ? (
            <p className="mt-1 text-xs text-green">Selecionado: {veiculoLabel}</p>
          ) : null}
          {hitsVeiculo.length ? (
            <ul className="mt-2 max-h-40 overflow-auto rounded-lg border border-line text-sm">
              {hitsVeiculo.map((v) => {
                const key = v.codigo_veic_globus || v.codigo;
                return (
                  <li key={key}>
                    <button
                      type="button"
                      className="w-full px-3 py-2 text-left hover:bg-bg"
                      onClick={() => void escolherVeiculo(v)}
                    >
                      {labelVeiculo(v)}
                    </button>
                  </li>
                );
              })}
            </ul>
          ) : null}
          {globusOffline || !veiculo ? (
            <select
              className={`${field} mt-2`}
              value={veiculo}
              onChange={(e) => {
                setVeiculo(e.target.value);
                const o = veiculosLocais.find((x) => String(x.id) === e.target.value);
                setVeiculoLabel(o?.label || "");
              }}
            >
              <option value="">Cadastro local…</option>
              {veiculosLocais.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.label}
                </option>
              ))}
            </select>
          ) : null}
        </div>

        <div>
          <label className="mb-1 block text-sm text-muted">Peca (espelho local)</label>
          <div className="flex flex-wrap gap-2">
            <input
              className={`${field} min-w-[12rem] flex-1`}
              placeholder="Codigo ou descricao…"
              value={qPeca}
              onChange={(e) => setQPeca(e.target.value)}
              onKeyDown={(e) => onSearchKeyDown(e, () => buscarPecaLocal())}
            />
            <button
              type="button"
              onClick={() => void buscarPecaLocal()}
              disabled={buscandoPeca}
              className="shrink-0 rounded-lg border border-line px-3 text-sm text-cyan disabled:opacity-60"
            >
              {buscandoPeca ? "…" : "Buscar local"}
            </button>
            <button
              type="button"
              onClick={() => void buscarPecaAoVivo()}
              disabled={buscandoPeca}
              className="shrink-0 rounded-lg border border-line px-3 text-sm text-muted disabled:opacity-60"
            >
              Buscar no Globus ao vivo
            </button>
          </div>
          {pecaLabel ? <p className="mt-1 text-xs text-green">Selecionada: {pecaLabel}</p> : null}
          {hitsPeca.length ? (
            <ul className="mt-2 max-h-40 overflow-auto rounded-lg border border-line text-sm">
              {hitsPeca.map((p) => (
                <li key={p.codigo_interno}>
                  <button
                    type="button"
                    className="w-full px-3 py-2 text-left hover:bg-bg"
                    onClick={() => void escolherPeca(p)}
                  >
                    {p.codigo_interno} — {p.descricao || ""}
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
          {globusOffline || !peca ? (
            <select
              className={`${field} mt-2`}
              value={peca}
              onChange={(e) => {
                setPeca(e.target.value);
                const o = pecasLocais.find((x) => String(x.id) === e.target.value);
                setPecaLabel(o?.label || "");
              }}
            >
              <option value="">Cadastro local…</option>
              {pecasLocais.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.label}
                </option>
              ))}
            </select>
          ) : null}
        </div>

        <div>
          <label className="mb-1 block text-sm text-muted">Fornecedor</label>
          <input
            className={`${field} mb-2`}
            placeholder="Filtrar por nome…"
            value={qFornecedor}
            onChange={(e) => setQFornecedor(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") e.preventDefault();
            }}
          />
          <select
            className={field}
            required
            value={fornecedor}
            onChange={(e) => {
              setFornecedor(e.target.value);
              const o = fornecedores.find((x) => String(x.id) === e.target.value);
              if (o) setQFornecedor(o.label);
            }}
          >
            <option value="">Selecione</option>
            {fornecedoresFiltrados.map((o) => (
              <option key={o.id} value={o.id}>
                {o.label}
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-muted">
            Digite para filtrar. Preenchido automaticamente ao buscar a NF compra no Globus.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-sm text-muted">NF venda fornecedor *</label>
            <input
              className={field}
              required
              value={nfVenda}
              onChange={(e) => setNfVenda(e.target.value)}
              placeholder="Numero marcado na peca"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-muted">Data NF venda *</label>
            <input
              type="date"
              className={field}
              required
              value={nfVendaData}
              onChange={(e) => setNfVendaData(e.target.value)}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-muted">Data aplicacao *</label>
            <input
              type="date"
              className={field}
              required
              value={dataAplicacao}
              onChange={(e) => setDataAplicacao(e.target.value)}
            />
            <p className="mt-1 text-xs text-muted">
              Prazo e data fim calculados pelas regras (padrao 180d externo).
            </p>
          </div>
          <div>
            <label className="mb-1 block text-sm text-muted">NF compra (opcional / Globus)</label>
            <div className="flex gap-2">
              <input
                className={field}
                value={nfCompra}
                onChange={(e) => setNfCompra(e.target.value)}
                onKeyDown={(e) => onSearchKeyDown(e, () => buscarNfCompra())}
              />
              <button
                type="button"
                onClick={() => void buscarNfCompra()}
                disabled={buscandoNf}
                className="shrink-0 rounded-lg border border-line px-3 text-sm text-cyan disabled:opacity-60"
              >
                {buscandoNf ? "…" : "Buscar Globus"}
              </button>
            </div>
            {msgGlobus ? <p className="mt-1 text-xs text-muted">{msgGlobus}</p> : null}
          </div>
          <div>
            <label className="mb-1 block text-sm text-muted">Km</label>
            <input
              type="number"
              className={field}
              value={km}
              onChange={(e) => setKm(e.target.value)}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-muted">Requisicao anterior</label>
            <input className={field} value={reqAnt} onChange={(e) => setReqAnt(e.target.value)} />
          </div>
          <div>
            <label className="mb-1 block text-sm text-muted">Requisicao atual</label>
            <input className={field} value={reqAtual} onChange={(e) => setReqAtual(e.target.value)} />
          </div>
          <div>
            <label className="mb-1 block text-sm text-muted">Valor</label>
            <input
              type="number"
              step="0.01"
              className={field}
              value={valor}
              onChange={(e) => setValor(e.target.value)}
            />
          </div>
        </div>

        <div>
          <label className="mb-1 block text-sm text-muted">Observacao / defeito</label>
          <textarea
            className={field}
            rows={4}
            value={obs}
            onChange={(e) => setObs(e.target.value)}
            required
          />
        </div>

        {error ? <p className="text-sm text-red">{error}</p> : null}

        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-cyan px-4 py-2.5 font-semibold text-bg disabled:opacity-60"
        >
          {loading ? "Gerando..." : "Gerar protocolo e laudo"}
        </button>
      </form>
    </div>
  );
}
