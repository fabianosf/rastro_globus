import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { canCreateGarantia } from "../auth/permissions";

export default function AppLayout({ title }: { title?: string }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const links = [
    { to: "/", label: "Dashboard", end: true },
    { to: "/garantias", label: "Garantias" },
    ...(canCreateGarantia(user?.perfil)
      ? [{ to: "/garantias/nova", label: "Nova garantia" }]
      : []),
  ];

  return (
    <div className="flex min-h-screen bg-bg">
      <aside className="flex w-60 shrink-0 flex-col border-r border-line bg-panel">
        <div className="flex items-center gap-3 border-b border-line px-4 py-5">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-cyan text-sm font-bold text-bg">
            RG
          </div>
          <div>
            <p className="font-semibold text-text">RastroGlobus</p>
            <p className="text-xs text-muted">Rastro da garantia</p>
          </div>
        </div>
        <nav className="flex flex-1 flex-col gap-1 p-3">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={"end" in l ? l.end : undefined}
              className={({ isActive }) =>
                `flex items-center justify-between rounded-lg px-3 py-2 text-sm transition ${
                  isActive
                    ? "bg-cyan/15 text-cyan"
                    : "text-muted hover:bg-line/40 hover:text-text"
                }`
              }
            >
              <span>{l.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-line p-4 text-xs text-muted">
          Globo controla estoque.
          <br />
          RG controla o rastro.
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-line bg-panel/80 px-6 py-4">
          <h1 className="text-lg font-semibold text-text">{title || "RastroGlobus"}</h1>
          <div className="flex items-center gap-3 text-sm">
            <span className="text-muted">
              {user?.first_name || user?.username}
              <span className="ml-2 rounded border border-line px-2 py-0.5 text-xs">
                {user?.perfil}
              </span>
            </span>
            <button
              type="button"
              className="rounded-lg border border-line px-3 py-1.5 text-muted hover:text-text"
              onClick={() => {
                logout();
                navigate("/login");
              }}
            >
              Sair
            </button>
          </div>
        </header>
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
