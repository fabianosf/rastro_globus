import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { canCreateGarantia } from "../auth/permissions";

export default function AppLayout({ title }: { title?: string }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const canNova = canCreateGarantia(user?.perfil);

  return (
    <div className="flex min-h-screen bg-bg">
      <aside className="no-print flex w-60 shrink-0 flex-col border-r border-line bg-panel">
        <div className="flex items-center gap-3 border-b border-line px-4 py-5">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-cyan text-[10px] font-bold text-bg">
            SGGI
          </div>
          <div>
            <p className="font-semibold text-text">SGGI</p>
            <p className="text-xs text-muted">Garantias Improcedentes</p>
          </div>
        </div>
        <nav className="flex flex-1 flex-col gap-1 p-3">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              `rounded-lg px-3 py-2 text-sm transition ${
                isActive
                  ? "bg-cyan/15 text-cyan"
                  : "text-muted hover:bg-line/40 hover:text-text"
              }`
            }
          >
            Minhas NFs
          </NavLink>
          {canNova ? (
            <NavLink
              to="/garantias/nova-danfe"
              className={({ isActive }) =>
                `rounded-lg px-3 py-2 text-sm transition ${
                  isActive
                    ? "bg-cyan/15 text-cyan"
                    : "text-muted hover:bg-line/40 hover:text-text"
                }`
              }
            >
              Registrar DANFE
            </NavLink>
          ) : null}
          <NavLink
            to="/relatorios"
            className={({ isActive }) =>
              `rounded-lg px-3 py-2 text-sm transition ${
                isActive
                  ? "bg-cyan/15 text-cyan"
                  : "text-muted hover:bg-line/40 hover:text-text"
              }`
            }
          >
            Relatórios
          </NavLink>
        </nav>
        <div className="border-t border-line p-4 text-xs text-muted">
          Cadastre a DANFE, edite ou exclua.
          <br />
          Sem histórico da planilha.
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="no-print flex items-center justify-between border-b border-line bg-panel/80 px-6 py-4">
          <h1 className="text-lg font-semibold text-text">{title || "SGGI"}</h1>
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
