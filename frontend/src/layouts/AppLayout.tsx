import { useState } from "react";
import { MenuIcon } from "lucide-react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { canCreateGarantia } from "../auth/permissions";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";

export default function AppLayout({ title }: { title?: string }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const canNova = canCreateGarantia(user?.perfil);
  const [menuOpen, setMenuOpen] = useState(false);

  const navClass = ({ isActive }: { isActive: boolean }) =>
    `rounded-lg px-3 py-2 text-sm transition ${
      isActive ? "bg-cyan/15 text-cyan" : "text-muted hover:bg-line/40 hover:text-text"
    }`;

  function NavItems({ onNavigate }: { onNavigate?: () => void }) {
    return (
      <>
        <NavLink to="/" end className={navClass} onClick={onNavigate}>
          Notas
        </NavLink>
        {canNova ? (
          <NavLink to="/garantias/nova-danfe" className={navClass} onClick={onNavigate}>
            Cadastrar
          </NavLink>
        ) : null}
        <NavLink to="/relatorios" className={navClass} onClick={onNavigate}>
          Relatórios
        </NavLink>
      </>
    );
  }

  function doLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div className="flex min-h-screen bg-bg">
      <aside className="no-print hidden w-56 shrink-0 flex-col border-r border-line bg-panel md:flex">
        <div className="flex items-center gap-3 border-b border-line px-4 py-5">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-[10px] font-bold text-primary-foreground">
            SGGI
          </div>
          <div>
            <p className="font-semibold text-text">SGGI</p>
            <p className="text-xs text-muted">Notas e custos</p>
          </div>
        </div>
        <nav className="flex flex-1 flex-col gap-1 p-3">
          <NavItems />
        </nav>
        <div className="border-t border-line p-4 text-xs text-muted">
          Cadastre a nota com foto e acompanhe quantidade e valor.
        </div>
      </aside>

      <Sheet open={menuOpen} onOpenChange={setMenuOpen}>
        <SheetContent side="left" className="bg-panel p-0 md:hidden">
          <SheetHeader className="border-b border-line">
            <SheetTitle>SGGI</SheetTitle>
          </SheetHeader>
          <nav className="flex flex-col gap-1 p-3">
            <NavItems onNavigate={() => setMenuOpen(false)} />
          </nav>
        </SheetContent>
      </Sheet>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="no-print flex items-center justify-between border-b border-line bg-panel/80 px-4 py-3 md:px-6 md:py-4">
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="icon-sm"
              className="md:hidden"
              onClick={() => setMenuOpen(true)}
              aria-label="Abrir menu"
            >
              <MenuIcon />
            </Button>
            <h1 className="text-lg font-semibold text-text">{title || "SGGI"}</h1>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <span className="hidden text-muted sm:inline">
              {user?.first_name || user?.username}
            </span>
            <Button type="button" variant="outline" size="sm" onClick={doLogout}>
              Sair
            </Button>
          </div>
        </header>
        <main className="flex-1 overflow-auto p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
