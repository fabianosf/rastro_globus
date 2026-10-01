import { useEffect, useState } from "react";
import { api } from "../api/client";

type GlobusStatus = {
  ok: boolean;
  detail: string;
  configured?: boolean;
  atualizado_em?: string | null;
  stale?: boolean;
  falhou?: boolean;
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
  const [status, setStatus] = useState<GlobusStatus | null>(null);

  useEffect(() => {
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
  }, []);

  if (!status) {
    return <span className="text-xs text-muted">Globus: verificando…</span>;
  }

  const alerta = Boolean(status.falhou || status.stale || !status.ok);
  const quando = formatAtualizado(status.atualizado_em);
  const label = quando
    ? `Dados do Globus atualizados em ${quando}`
    : "Dados do Globus: sync pendente";

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded border px-2 py-1 text-xs ${
        alerta
          ? "border-red/40 bg-red/10 text-red"
          : "border-green/40 bg-green/10 text-green"
      }`}
      title={status.detail}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${alerta ? "bg-red" : "bg-green"}`} />
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
  placa?: string;
  descricao?: string;
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
