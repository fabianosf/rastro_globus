import { Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import AppLayout from "./layouts/AppLayout";
import AlertasReincidencia from "./pages/AlertasReincidencia";
import Dashboard from "./pages/Dashboard";
import GarantiaFicha from "./pages/GarantiaFicha";
import GarantiaNova from "./pages/GarantiaNova";
import GarantiasList from "./pages/GarantiasList";
import Login from "./pages/Login";
import RegrasPrazo from "./pages/RegrasPrazo";

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
  if (pathname.startsWith("/alertas-reincidencia")) return "Alertas de reincidencia";
  if (pathname.startsWith("/regras-prazo")) return "Regras de prazo";
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
            {/* Mantidas por URL (fora do menu MVP) */}
            <Route path="/alertas-reincidencia" element={<AlertasReincidencia />} />
            <Route path="/regras-prazo" element={<RegrasPrazo />} />
            {/* Removidas do MVP: redirect */}
            <Route path="/movimentos-globus" element={<Navigate to="/" replace />} />
            <Route path="/relatorios" element={<Navigate to="/" replace />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}
