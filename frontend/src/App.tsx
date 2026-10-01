import { Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import AppLayout from "./layouts/AppLayout";
import Dashboard from "./pages/Dashboard";
import GarantiaFicha from "./pages/GarantiaFicha";
import GarantiaNova from "./pages/GarantiaNova";
import GarantiasList from "./pages/GarantiasList";
import Login from "./pages/Login";
import MovimentosGlobus from "./pages/MovimentosGlobus";
import Relatorios from "./pages/Relatorios";

function Protected() {
  const { isAuthenticated } = useAuth();
  const location = useLocation();
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  return <Outlet />;
}

function titleFor(pathname: string) {
  if (pathname === "/") return "Dashboard";
  if (pathname.startsWith("/garantias/nova")) return "Nova garantia";
  if (pathname.match(/^\/garantias\/\d+/)) return "Ficha da garantia";
  if (pathname.startsWith("/garantias")) return "Garantias";
  if (pathname.startsWith("/movimentos-globus")) return "Movimentos Globus";
  if (pathname.startsWith("/relatorios")) return "Relatórios";
  return "RastroGlobus";
}

function LayoutShell() {
  const location = useLocation();
  return <AppLayout title={titleFor(location.pathname)} />;
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<Protected />}>
          <Route element={<LayoutShell />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/garantias" element={<GarantiasList />} />
            <Route path="/garantias/nova" element={<GarantiaNova />} />
            <Route path="/garantias/:id" element={<GarantiaFicha />} />
            <Route path="/movimentos-globus" element={<MovimentosGlobus />} />
            <Route path="/relatorios" element={<Relatorios />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}
