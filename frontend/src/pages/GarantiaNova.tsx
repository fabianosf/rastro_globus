import { FormEvent, useEffect, useState } from "react";
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
  const [hitsVeiculo, setHitsVeiculo] = useState<GlobusVeiculo[]>([]);
  const [hitsPeca, setHitsPeca] = useState<GlobusPeca[]>([]);
  const [nfCompra, setNfCompra] = useState("");
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

  async function buscarVeiculoLocal() {
    if (qVeiculo.trim().length < 2) {
      setError("Informe ao menos 2 caracteres para buscar veiculo no espelho local.");
      return;
    }
    setError("");
    setMsgGlobus("");
    setBuscandoVeiculo(true);
    try {
      const rows = await buscarVeiculosLocal(qVeiculo.trim());
      setHitsVeiculo(rows);
      setGlobusOffline(false);
      if (!rows.length) setMsgGlobus("Nenhum veiculo no espelho local. Tente sync_globus ou busca ao vivo.");
      else setMsgGlobus(`Espelho local: ${rows.length} veiculo(s).`);
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

  async function buscarPecaLocal() {
    if (qPeca.trim().length < 2) {
      setError("Informe ao menos 2 caracteres para buscar peca no espelho local.");
      return;
    }
    setError("");
    setMsgGlobus("");
    setBuscandoPeca(true);
    try {
      const rows = await buscarPecasLocal(qPeca.trim());
      setHitsPeca(rows);
      setGlobusOffline(false);
      if (!rows.length) setMsgGlobus("Nenhuma peca no espelho local. Tente sync_globus ou busca ao vivo.");
      else setMsgGlobus(`Espelho local: ${rows.length} peca(s).`);
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

  async function escolherVeiculo(v: GlobusVeiculo) {
    setError("");
    try {
      const local = await api<{ id: number; codigo: string }>("/api/veiculos/ensure/", {
        method: "POST",
        body: {
          codigo: v.codigo,
          placa: v.placa || "",
          descricao: v.descricao || `Veículo ${v.codigo}`,
        },
      });
      setVeiculo(String(local.id));
      setVeiculoLabel(`${local.codigo}${v.placa ? ` · ${v.placa}` : ""}`);
      setHitsVeiculo([]);
      setMsgGlobus(`Veículo ${local.codigo} espelhado no RastroGlobus (somente leitura Globus).`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Falha ao espelhar veículo.");
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
      setMsgGlobus(`Peça ${local.codigo_interno} espelhada no RastroGlobus (somente leitura Globus).`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Falha ao espelhar peça.");
    }
  }

  async function buscarNfCompra() {
    if (!nfCompra.trim()) {
      setError("Informe o número da NF compra para buscar no Globus.");
      return;
    }
    setError("");
    setMsgGlobus("");
    setBuscandoNf(true);
    try {
      const rows = await buscarNfGlobus(nfCompra.trim());
      if (!rows.length) {
        setMsgGlobus("NF não encontrada no Globus (somente leitura).");
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
          setFornecedores((prev) => {
            if (prev.some((x) => x.id === forn.id)) return prev;
            return [
              ...prev,
              { id: forn.id, label: forn.nome_fantasia || forn.razao_social },
            ];
          });
        } catch {
          /* fornecedor opcional; NF e valor já preenchidos */
        }
      }

      setMsgGlobus(
        `Globus: NF ${nf.numero}${nf.serie ? ` série ${nf.serie}` : ""}` +
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

  if (!allowed) {
    return <Navigate to="/garantias" replace />;
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (!veiculo || !peca || !fornecedor) {
      setError("Selecione veículo, peça e fornecedor.");
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
            Busque peca/veiculo no espelho local (sync_globus). Oracle so no job ou no botao ao vivo. Nao movimenta estoque.
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
              placeholder="Prefixo ou placa…"
              value={qVeiculo}
              onChange={(e) => setQVeiculo(e.target.value)}
            />
            <button
              type="button"
              onClick={buscarVeiculoLocal}
              disabled={buscandoVeiculo}
              className="shrink-0 rounded-lg border border-line px-3 text-sm text-cyan disabled:opacity-60"
            >
              {buscandoVeiculo ? "…" : "Buscar local"}
            </button>
            <button
              type="button"
              onClick={buscarVeiculoAoVivo}
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
              {hitsVeiculo.map((v) => (
                <li key={v.codigo}>
                  <button
                    type="button"
                    className="w-full px-3 py-2 text-left hover:bg-bg"
                    onClick={() => escolherVeiculo(v)}
                  >
                    {v.codigo}
                    {v.placa ? ` · ${v.placa}` : ""}
                  </button>
                </li>
              ))}
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
            />
            <button
              type="button"
              onClick={buscarPecaLocal}
              disabled={buscandoPeca}
              className="shrink-0 rounded-lg border border-line px-3 text-sm text-cyan disabled:opacity-60"
            >
              {buscandoPeca ? "…" : "Buscar local"}
            </button>
            <button
              type="button"
              onClick={buscarPecaAoVivo}
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
                    onClick={() => escolherPeca(p)}
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
          <select
            className={field}
            required
            value={fornecedor}
            onChange={(e) => setFornecedor(e.target.value)}
          >
            <option value="">Selecione</option>
            {fornecedores.map((o) => (
              <option key={o.id} value={o.id}>
                {o.label}
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-muted">
            Preenchido automaticamente ao buscar a NF compra no Globus, quando houver.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-sm text-muted">NF compra</label>
            <div className="flex gap-2">
              <input
                className={field}
                value={nfCompra}
                onChange={(e) => setNfCompra(e.target.value)}
              />
              <button
                type="button"
                onClick={buscarNfCompra}
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
            <label className="mb-1 block text-sm text-muted">Requisição anterior</label>
            <input className={field} value={reqAnt} onChange={(e) => setReqAnt(e.target.value)} />
          </div>
          <div>
            <label className="mb-1 block text-sm text-muted">Requisição atual</label>
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
          <label className="mb-1 block text-sm text-muted">Observação / defeito</label>
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
