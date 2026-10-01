type Props = {
  title: string;
  value: string | number;
  hint?: string;
  accent?: "cyan" | "green" | "amber" | "red" | "violet";
};

const accentMap = {
  cyan: "border-cyan/40 text-cyan",
  green: "border-green/40 text-green",
  amber: "border-amber/40 text-amber",
  red: "border-red/40 text-red",
  violet: "border-violet/40 text-violet",
};

export default function KpiCard({ title, value, hint, accent = "cyan" }: Props) {
  return (
    <div className={`rounded-xl border bg-panel p-4 ${accentMap[accent]}`}>
      <p className="text-sm text-muted">{title}</p>
      <p className="mt-2 text-2xl font-semibold text-text">{value}</p>
      {hint ? <p className="mt-1 text-xs text-muted">{hint}</p> : null}
    </div>
  );
}
