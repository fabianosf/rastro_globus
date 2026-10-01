import { useEffect, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";

type GlobusStatus = {
  ok: boolean;
  detail: string;
  configured?: boolean;
  oracle_ok?: boolean;
  oracle_detail?: string;
  atualizado_em?: string | null;
  stale?: boolean;
  falhou?: boolean;
  em_andamento?: boolean;
  source?: string;
};

function formatAtualizado(iso?: string | null) {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const mi = String(d.getMinutes()).padStart(2, "0");
  return `${dd}/${mm} ${hh}:${mi}`;
}

export default function GlobusStatusBadge() {
  const { token } = useAuth();
  const [status, setStatus] = useState<GlobusStatus | null>(null);

  useEffect(() => {
    if (!token) {
      setStatus(null);
      return;
    }
    api<GlobusStatus>("/api/globus/status/")
      .then(setStatus)
      .catch(() =>
        setStatus({
          ok: false,
          detail: "Espelho Globus indisponivel.",
          falhou: true,
          stale: true,
        })
      );
  }, [token]);

  if (!status) {
    return <span className="text-xs text-muted">Globus: verificando…</span>;
  }

  const quando = formatAtualizado(status.atualizado_em);
  const oracleOk = Boolean(status.oracle_ok);
  const confMissing = status.configured === false;
  const alerta = Boolean(
    status.falhou ||
      confMissing ||
      status.oracle_ok === false ||
      (Boolean(quando) && status.stale && !status.em_andamento)
  );
  const aviso = Boolean(!alerta && (status.em_andamento || (!quando && oracleOk)));

  let label: string;
  if (quando && !status.em_andamento) {
    label = `Dados do Globus atualizados em ${quando}`;
  } else if (status.em_andamento) {
    label = quando
      ? `Sync em andamento (último espelho ${quando})`
      : "Sync Globus em andamento…";
  } else if (oracleOk) {
    label = "Oracle OK (conf/) — espelho ainda sem sync";
  } else if (confMissing) {
    label = "conf/ Oracle não configurado";
  } else {
    label = status.oracle_detail || status.detail || "Falha na conexão Oracle";
  }

  const tone = alerta
    ? "border-red/40 bg-red/10 text-red"
    : aviso
      ? "border-amber-500/40 bg-amber-500/10 text-amber-700"
      : "border-green/40 bg-green/10 text-green";
  const dot = alerta ? "bg-red" : aviso ? "bg-amber-500" : "bg-green";
  const title = [status.detail, status.oracle_detail].filter(Boolean).join(" | ");

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded border px-2 py-1 text-xs ${tone}`}
      title={title}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${dot}`} />
      {label}
    </span>
  );
}

export type GlobusNf = {
  numero: string;
  serie?: string;
  data_emissao?: string;
  data_entrada?: string;
  valor?: string;
  codigo_fornecedor?: string | number;
  fornecedor_nome?: string;
  tipo_doc?: string;
  peca_codigo?: string;
  peca_descricao?: string;
  cod_int_nf?: string | number;
};

export type GlobusPeca = {
  codigo_interno: string;
  descricao?: string;
};

export type GlobusVeiculo = {
  codigo: string;
  prefixo?: string;
  placa?: string;
  descricao?: string;
  codigo_veic_globus?: string;
};

export async function buscarNfGlobus(numero: string): Promise<GlobusNf[]> {
  const data = await api<{ results: GlobusNf[] }>(
    `/api/globus/nf/?numero=${encodeURIComponent(numero)}`
  );
  return data.results || [];
}

export async function buscarNfsGarantiaGlobus(opts: {
  numero?: string;
  peca?: string;
  limite?: number;
}): Promise<{ results: GlobusNf[]; aviso?: string; detail?: string }> {
  const q = new URLSearchParams();
  if (opts.numero) q.set("numero", opts.numero);
  if (opts.peca) q.set("peca", opts.peca);
  if (opts.limite) q.set("limite", String(opts.limite));
  return api(`/api/globus/nfs-garantia/?${q}`);
}

export async function buscarPecasLocal(q: string): Promise<GlobusPeca[]> {
  const data = await api<{ results: GlobusPeca[] }>(
    `/api/globus/local/pecas/?q=${encodeURIComponent(q)}`
  );
  return data.results || [];
}

export async function buscarVeiculosLocal(q: string): Promise<GlobusVeiculo[]> {
  const data = await api<{ results: GlobusVeiculo[] }>(
    `/api/globus/local/veiculos/?q=${encodeURIComponent(q)}`
  );
  return data.results || [];
}

/** Busca ao vivo no Oracle (alternativa). */
export async function buscarPecasGlobus(q: string): Promise<GlobusPeca[]> {
  const data = await api<{ results: GlobusPeca[] }>(
    `/api/globus/pecas/?q=${encodeURIComponent(q)}`
  );
  return data.results || [];
}

export async function buscarVeiculosGlobus(q: string): Promise<GlobusVeiculo[]> {
  const data = await api<{ results: GlobusVeiculo[] }>(
    `/api/globus/veiculos/?q=${encodeURIComponent(q)}`
  );
  return data.results || [];
}
