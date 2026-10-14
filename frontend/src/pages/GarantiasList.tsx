import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { api, ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { canCreateGarantia, canDeleteGarantia } from "../auth/permissions";
import BadgeStatus from "../components/BadgeStatus";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

type GarantiaRow = {
  id: number;
  protocolo: string;
  peca_nome: string;
  peca_codigo?: string;
  veiculo_codigo: string;
  fornecedor_nome: string;
  nf_remessa: string;
  status: string;
  valor_peca: string | null;
};

type ResumoAno = {
  ano: number;
  contagem_status: Record<string, number>;
  valor_improcedente: string;
  valor_aberto: string;
  valor_procedente?: string;
};

const FILTROS = [
  { value: "", label: "Todas" },
  { value: "abertos", label: "Em andamento" },
  { value: "improcedente", label: "Improcedentes" },
] as const;

function money(v: string | number | null | undefined) {
  if (v === undefined || v === null || v === "") return "—";
  const n = Number(v);
  if (Number.isNaN(n)) return String(v);
  return n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function useDebounced(value: string, ms: number) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = window.setTimeout(() => setDebounced(value), ms);
    return () => window.clearTimeout(t);
  }, [value, ms]);
  return debounced;
}

export default function GarantiasList() {
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const anoAtual = new Date().getFullYear();
  const anos = useMemo(
    () => [anoAtual, anoAtual - 1, anoAtual - 2, anoAtual - 3].map(String),
    [anoAtual]
  );

  const status = params.get("status") || "";
  const ano = params.get("ano") || String(anoAtual);
  const qParam = params.get("q") || "";

  const [qInput, setQInput] = useState(qParam);
  const qDebounced = useDebounced(qInput, 350);

  const [rows, setRows] = useState<GarantiaRow[]>([]);
  const [resumo, setResumo] = useState<ResumoAno | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [toDelete, setToDelete] = useState<GarantiaRow | null>(null);
  const fetchGen = useRef(0);

  useEffect(() => {
    if (params.get("ano")) return;
    const next = new URLSearchParams(params);
    next.set("ano", String(anoAtual));
    setParams(next, { replace: true });
  }, [anoAtual, params, setParams]);

  useEffect(() => {
    if (qDebounced.trim() === qParam.trim()) return;
    const next = new URLSearchParams(params);
    if (qDebounced.trim()) next.set("q", qDebounced.trim());
    else next.delete("q");
    setParams(next, { replace: true });
  }, [qDebounced, qParam, params, setParams]);

  useEffect(() => {
    setQInput(qParam);
  }, [qParam]);

  useEffect(() => {
    const qs = new URLSearchParams();
    if (status) qs.set("status", status);
    qs.set("ano", ano || String(anoAtual));
    if (qParam.trim()) qs.set("q", qParam.trim());

    const gen = ++fetchGen.current;
    setLoading(true);
    setError("");
    Promise.all([
      api<GarantiaRow[]>(`/api/garantias/?${qs}`),
      api<ResumoAno>(`/api/relatorios/resumo/?ano=${ano || anoAtual}`),
    ])
      .then(([lista, r]) => {
        if (gen !== fetchGen.current) return;
        setRows(Array.isArray(lista) ? lista : []);
        setResumo(r);
      })
      .catch((e) => {
        if (gen !== fetchGen.current) return;
        setError(e instanceof ApiError ? e.message : "Erro ao carregar notas.");
        setRows([]);
        setResumo(null);
      })
      .finally(() => {
        if (gen !== fetchGen.current) return;
        setLoading(false);
      });
  }, [status, ano, qParam, anoAtual]);

  const contagem = resumo?.contagem_status || {};
  const qtdTotal = Object.values(contagem).reduce((a, b) => a + (b || 0), 0);
  const qtdImp = contagem.improcedente || 0;
  const qtdAndamento =
    (contagem.aberta || 0) + (contagem.enviada || 0) + (contagem.em_analise || 0);

  const valorAno =
    Number(resumo?.valor_improcedente || 0) +
    Number(resumo?.valor_aberto || 0) +
    Number(resumo?.valor_procedente || 0);

  const valorCard =
    status === "improcedente"
      ? Number(resumo?.valor_improcedente || 0)
      : status === "abertos"
        ? Number(resumo?.valor_aberto || 0)
        : valorAno;

  const qtdCard =
    status === "improcedente" ? qtdImp : status === "abertos" ? qtdAndamento : qtdTotal;

  async function confirmarExclusao() {
    const row = toDelete;
    if (!row || !canDeleteGarantia(user?.perfil, row.status)) return;
    setDeletingId(row.id);
    setError("");
    try {
      await api(`/api/garantias/${row.id}/`, { method: "DELETE" });
      setRows((prev) => prev.filter((r) => r.id !== row.id));
      toast.success("Nota excluída.");
      setToDelete(null);
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Erro ao excluir.";
      setError(msg);
      toast.error(msg);
    } finally {
      setDeletingId(null);
    }
  }

  function setFiltro(value: string) {
    const next = new URLSearchParams();
    next.set("ano", ano || String(anoAtual));
    if (value) next.set("status", value);
    if (qParam.trim()) next.set("q", qParam.trim());
    setParams(next, { replace: true });
  }

  const emptyState = (
    <div className="px-3 py-12 text-center">
      <p className="text-base font-medium text-ink">Nenhuma nota ainda</p>
      <p className="mt-1 text-sm text-muted">Cadastre a primeira nota com a foto da NF.</p>
      {canCreateGarantia(user?.perfil) ? (
        <Button
          render={<Link to="/garantias/nova-danfe" />}
          className="mt-4 w-full sm:w-auto"
          size="lg"
        >
          Cadastrar nota
        </Button>
      ) : null}
    </div>
  );

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
        <div className="min-w-0">
          <p className="text-sm text-muted">Notas de {ano}</p>
          <p className="text-xs text-muted">Cadastre a nota, anexe a foto e acompanhe o valor.</p>
        </div>
        {canCreateGarantia(user?.perfil) ? (
          <Button
            render={<Link to="/garantias/nova-danfe" />}
            size="lg"
            className="w-full sm:w-auto"
          >
            Cadastrar nota
          </Button>
        ) : null}
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-xl border border-line bg-panel px-4 py-4">
          <p className="text-xs text-muted">Quantidade de notas</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums">{qtdCard}</p>
        </div>
        <div className="rounded-xl border border-line bg-panel px-4 py-4">
          <p className="text-xs text-muted">Valor total</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-cyan">{money(valorCard)}</p>
        </div>
        <div className="rounded-xl border border-line bg-panel px-4 py-4">
          <p className="text-xs text-muted">Improcedentes ({ano})</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-red">{qtdImp}</p>
          <p className="mt-0.5 text-xs text-muted">{money(resumo?.valor_improcedente)}</p>
        </div>
      </div>

      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
        <div className="flex flex-wrap gap-2">
          {FILTROS.map((f) => (
            <button
              key={f.value || "todas"}
              type="button"
              onClick={() => setFiltro(f.value)}
              className={
                status === f.value
                  ? "rounded-lg bg-cyan/20 px-3 py-1.5 text-sm font-semibold text-cyan"
                  : "rounded-lg border border-line px-3 py-1.5 text-sm text-muted hover:text-ink"
              }
            >
              {f.label}
            </button>
          ))}
        </div>
        <div className="flex w-full flex-col gap-2 sm:ml-auto sm:w-auto sm:flex-row sm:items-center">
          <select
            className="w-full rounded-lg border border-line bg-bg px-2 py-1.5 text-sm sm:w-auto"
            value={anos.includes(ano) ? ano : String(anoAtual)}
            onChange={(e) => {
              const next = new URLSearchParams(params);
              next.set("ano", e.target.value);
              setParams(next, { replace: true });
            }}
            title="Ano"
          >
            {anos.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
          <Input
            className="w-full sm:w-52"
            placeholder="Buscar NF, peça…"
            value={qInput}
            onChange={(e) => setQInput(e.target.value)}
          />
        </div>
      </div>

      {error ? <p className="text-red">{error}</p> : null}
      {loading ? <p className="text-muted">Carregando…</p> : null}

      {/* Cards — mobile */}
      <div className="space-y-3 md:hidden">
        {rows.map((r) => (
          <article
            key={r.id}
            className="rounded-xl border border-line bg-panel p-4 text-sm"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <Link
                  className="font-semibold text-cyan hover:underline"
                  to={`/garantias/${r.id}`}
                >
                  {r.nf_remessa || r.protocolo}
                </Link>
                <p className="truncate text-xs text-muted">{r.fornecedor_nome}</p>
              </div>
              <BadgeStatus status={r.status} />
            </div>
            <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
              <div className="min-w-0">
                <dt className="text-muted">Peça</dt>
                <dd className="truncate font-medium">{r.peca_nome}</dd>
              </div>
              <div className="min-w-0">
                <dt className="text-muted">Carro</dt>
                <dd className="truncate font-medium">{r.veiculo_codigo}</dd>
              </div>
              <div className="col-span-2">
                <dt className="text-muted">Valor</dt>
                <dd className="font-medium tabular-nums">{money(r.valor_peca)}</dd>
              </div>
            </dl>
            <div className="mt-3 flex flex-wrap gap-2 border-t border-line pt-3">
              <Button
                render={<Link to={`/garantias/${r.id}`} />}
                size="sm"
                className="flex-1"
              >
                Ver
              </Button>
              {canDeleteGarantia(user?.perfil, r.status) ? (
                <Button
                  type="button"
                  variant="destructive"
                  size="sm"
                  disabled={deletingId === r.id}
                  onClick={() => setToDelete(r)}
                  className="flex-1"
                >
                  {deletingId === r.id ? "…" : "Excluir"}
                </Button>
              ) : null}
            </div>
          </article>
        ))}
        {!loading && !rows.length ? (
          <div className="rounded-xl border border-line bg-panel">{emptyState}</div>
        ) : null}
      </div>

      {/* Tabela — desktop */}
      <div className="hidden overflow-x-auto rounded-xl border border-line bg-panel md:block">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead className="border-b border-line text-muted">
            <tr>
              <th className="px-3 py-3 font-medium">Nota</th>
              <th className="px-3 py-3 font-medium">Peça</th>
              <th className="px-3 py-3 font-medium">Carro</th>
              <th className="px-3 py-3 font-medium">Valor</th>
              <th className="px-3 py-3 font-medium">Situação</th>
              <th className="px-3 py-3 font-medium" />
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-t border-line hover:bg-bg/40">
                <td className="px-3 py-3">
                  <Link className="font-medium text-cyan hover:underline" to={`/garantias/${r.id}`}>
                    {r.nf_remessa || r.protocolo}
                  </Link>
                  <p className="text-xs text-muted">{r.fornecedor_nome}</p>
                </td>
                <td className="px-3 py-3">{r.peca_nome}</td>
                <td className="px-3 py-3">{r.veiculo_codigo}</td>
                <td className="px-3 py-3 whitespace-nowrap">{money(r.valor_peca)}</td>
                <td className="px-3 py-3">
                  <BadgeStatus status={r.status} />
                </td>
                <td className="px-3 py-3 text-right">
                  <Link to={`/garantias/${r.id}`} className="text-xs text-cyan hover:underline">
                    Ver
                  </Link>
                  {canDeleteGarantia(user?.perfil, r.status) ? (
                    <Button
                      type="button"
                      variant="link"
                      size="sm"
                      disabled={deletingId === r.id}
                      onClick={() => setToDelete(r)}
                      className="ml-2 h-auto p-0 text-xs text-destructive"
                    >
                      {deletingId === r.id ? "…" : "Excluir"}
                    </Button>
                  ) : null}
                </td>
              </tr>
            ))}
            {!loading && !rows.length ? (
              <tr>
                <td colSpan={6}>{emptyState}</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      <Dialog open={!!toDelete} onOpenChange={(open) => !open && setToDelete(null)}>
        <DialogContent showCloseButton>
          <DialogHeader>
            <DialogTitle>Excluir nota?</DialogTitle>
            <DialogDescription>
              Excluir a nota {toDelete?.nf_remessa || toDelete?.protocolo}? Esta ação não tem
              volta.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setToDelete(null)}>
              Cancelar
            </Button>
            <Button
              type="button"
              variant="destructive"
              disabled={deletingId !== null}
              onClick={() => void confirmarExclusao()}
            >
              {deletingId !== null ? "Excluindo…" : "Excluir"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
