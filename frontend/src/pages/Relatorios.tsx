import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import RelatorioErroInterno from "./RelatorioErroInterno";
import RelatorioRankings from "./RelatorioRankings";

type Aba = "erro-interno" | "rankings";

export default function Relatorios() {
  const [params, setParams] = useSearchParams();
  const aba = useMemo<Aba>(() => {
    const raw = (params.get("aba") || "erro-interno").toLowerCase();
    return raw === "rankings" ? "rankings" : "erro-interno";
  }, [params]);

  function setAba(next: Aba) {
    const p = new URLSearchParams(params);
    p.set("aba", next);
    setParams(p, { replace: true });
  }

  const tabClass = (active: boolean) =>
    `rounded-lg px-3 py-1.5 text-sm transition ${
      active ? "bg-cyan/15 text-cyan" : "text-muted hover:bg-line/40 hover:text-text"
    }`;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted">
          Acompanhe o custo do erro interno e os rankings. Não altera estoque Globus.
        </p>
        <div className="flex flex-wrap gap-1 rounded-xl border border-line bg-panel p-1">
          <button
            type="button"
            className={tabClass(aba === "erro-interno")}
            onClick={() => setAba("erro-interno")}
          >
            Custo do erro interno
          </button>
          <button
            type="button"
            className={tabClass(aba === "rankings")}
            onClick={() => setAba("rankings")}
          >
            Rankings
          </button>
        </div>
      </div>

      {aba === "erro-interno" ? <RelatorioErroInterno /> : <RelatorioRankings />}
    </div>
  );
}
