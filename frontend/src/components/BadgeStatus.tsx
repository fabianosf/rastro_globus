/** Rótulos amigáveis para quem não mexe com TI. */
const LABELS: Record<string, string> = {
  aberta: "Em andamento",
  enviada: "Em andamento",
  em_analise: "Em andamento",
  procedente: "Procedente",
  improcedente: "Improcedente",
  cortesia: "Cortesia",
  cancelada: "Cancelada",
};

const COLORS: Record<string, string> = {
  aberta: "bg-amber/15 text-amber border-amber/40",
  enviada: "bg-amber/15 text-amber border-amber/40",
  em_analise: "bg-amber/15 text-amber border-amber/40",
  procedente: "bg-green/15 text-green border-green/40",
  improcedente: "bg-red/15 text-red border-red/40",
  cortesia: "bg-violet/15 text-violet border-violet/40",
  cancelada: "bg-muted/15 text-muted border-muted/40",
};

export function statusLabel(status: string) {
  return LABELS[status] || status;
}

export default function BadgeStatus({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex items-center rounded border px-2 py-0.5 text-xs font-medium ${
        COLORS[status] || "bg-muted/15 text-muted border-muted/40"
      }`}
    >
      {statusLabel(status)}
    </span>
  );
}
