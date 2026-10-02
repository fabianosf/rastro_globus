import { Link } from "react-router-dom";

type Props = {
  title: string;
  value: string | number;
  hint?: string;
  accent?: "cyan" | "green" | "amber" | "red" | "violet";
  to?: string;
};

const accentMap = {
  cyan: "border-cyan/40 text-cyan",
  green: "border-green/40 text-green",
  amber: "border-amber/40 text-amber",
  red: "border-red/40 text-red",
  violet: "border-violet/40 text-violet",
};

export default function KpiCard({ title, value, hint, accent = "cyan", to }: Props) {
  const body = (
    <>
      <p className="text-sm text-muted">{title}</p>
      <p className="mt-2 text-2xl font-semibold text-text">{value}</p>
      {hint ? <p className="mt-1 text-xs text-muted">{hint}</p> : null}
    </>
  );

  const cls = `rounded-xl border bg-panel p-4 ${accentMap[accent]} ${
    to ? "transition hover:border-cyan/60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan" : ""
  }`;

  if (to) {
    return (
      <Link to={to} className={`block ${cls}`}>
        {body}
      </Link>
    );
  }

  return <div className={cls}>{body}</div>;
}
