import BadgeStatus from "./BadgeStatus";

export type Evento = {
  id: number;
  data: string;
  status_anterior: string;
  status_novo: string;
  descricao: string;
  usuario_nome?: string;
};

export default function Timeline({ eventos }: { eventos: Evento[] }) {
  if (!eventos?.length) {
    return <p className="text-sm text-muted">Nenhum evento na timeline.</p>;
  }

  return (
    <ol className="relative space-y-4 border-l border-line pl-4">
      {eventos.map((ev) => (
        <li key={ev.id} className="relative">
          <span className="absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full bg-cyan" />
          <div className="rounded-lg border border-line bg-bg/40 p-3">
            <div className="mb-1 flex flex-wrap items-center gap-2">
              <BadgeStatus status={ev.status_novo} />
              <span className="text-xs text-muted">
                {new Date(ev.data).toLocaleString("pt-BR")}
                {ev.usuario_nome ? ` · ${ev.usuario_nome}` : ""}
              </span>
            </div>
            <p className="text-sm text-text">{ev.descricao}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}
