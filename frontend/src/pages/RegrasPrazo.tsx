import { FormEvent, useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { canManageRegrasPrazo } from "../auth/permissions";

type Regra = {
  id: number;
  escopo: string;
  valor_escopo: string;
  prazo_dias: number;
  tipo_servico: string;
  ativo: boolean;
};

const ESCOPOS = [
  { v: "peca", l: "Peca" },
  { v: "grupo_peca", l: "Grupo de peca" },
  { v: "fornecedor", l: "Fornecedor" },
  { v: "tipo_servico", l: "Tipo de servico" },
];

export default function RegrasPrazo() {
  const { user } = useAuth();
  const allowed = canManageRegrasPrazo(user?.perfil);
  const [rows, setRows] = useState<Regra[]>([]);
  const [error, setError] = useState("");
  const [escopo, setEscopo] = useState("tipo_servico");
  const [valor, setValor] = useState("externo");
  const [prazo, setPrazo] = useState("180");
  const [tipoServico, setTipoServico] = useState("externo");

  function load() {
    api<Regra[]>("/api/regras-prazo/")
      .then(setRows)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Erro ao carregar regras."));
  }

  useEffect(() => {
    if (allowed) load();
  }, [allowed]);

  if (!allowed) return <Navigate to="/" replace />;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await api("/api/regras-prazo/", {
        method: "POST",
        body: {
          escopo,
          valor_escopo: valor.trim(),
          prazo_dias: Number(prazo),
          tipo_servico: tipoServico,
          ativo: true,
        },
      });
      setValor("");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao salvar regra.");
    }
  }

  const field =
    "w-full rounded-lg border border-line bg-bg px-3 py-2 text-sm outline-none focus:border-cyan";

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <p className="text-sm text-muted">
        Especificidade: peca &gt; grupo &gt; fornecedor &gt; tipo_servico. Padrao externo = 180 dias.
      </p>

      <form onSubmit={onSubmit} className="space-y-3 rounded-xl border border-line bg-panel p-4">
        <h2 className="font-semibold">Nova regra</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="text-sm">
            <span className="mb-1 block text-muted">Escopo</span>
            <select className={field} value={escopo} onChange={(e) => setEscopo(e.target.value)}>
              {ESCOPOS.map((o) => (
                <option key={o.v} value={o.v}>
                  {o.l}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-muted">Valor do escopo</span>
            <input className={field} value={valor} onChange={(e) => setValor(e.target.value)} required />
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-muted">Prazo (dias)</span>
            <input
              className={field}
              type="number"
              min={1}
              value={prazo}
              onChange={(e) => setPrazo(e.target.value)}
              required
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-muted">Tipo servico</span>
            <select
              className={field}
              value={tipoServico}
              onChange={(e) => setTipoServico(e.target.value)}
            >
              <option value="externo">Externo</option>
              <option value="interno">Interno</option>
            </select>
          </label>
        </div>
        {error ? <p className="text-sm text-red">{error}</p> : null}
        <button type="submit" className="rounded-lg bg-cyan px-4 py-2 text-sm font-medium text-bg">
          Salvar
        </button>
      </form>

      <div className="overflow-x-auto rounded-xl border border-line bg-panel">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-line text-muted">
            <tr>
              <th className="px-3 py-2">Escopo</th>
              <th className="px-3 py-2">Valor</th>
              <th className="px-3 py-2">Prazo</th>
              <th className="px-3 py-2">Tipo</th>
              <th className="px-3 py-2">Ativo</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-t border-line">
                <td className="px-3 py-2">{r.escopo}</td>
                <td className="px-3 py-2">{r.valor_escopo}</td>
                <td className="px-3 py-2">{r.prazo_dias} d</td>
                <td className="px-3 py-2">{r.tipo_servico}</td>
                <td className="px-3 py-2">{r.ativo ? "sim" : "nao"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
