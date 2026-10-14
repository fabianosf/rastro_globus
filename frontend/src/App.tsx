import { Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import AppLayout from "./layouts/AppLayout";
import GarantiaDanfe from "./pages/GarantiaDanfe";
import GarantiaFicha from "./pages/GarantiaFicha";
import GarantiaNova from "./pages/GarantiaNova";
import GarantiasList from "./pages/GarantiasList";
import Login from "./pages/Login";
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
  if (pathname === "/" || pathname === "/garantias") return "Notas";
  if (pathname.startsWith("/garantias/nova-danfe")) return "Cadastrar nota";
  if (pathname.startsWith("/garantias/nova")) return "Cadastro avançado";
  if (pathname.match(/^\/garantias\/\d+/)) return "Detalhe da nota";
  if (pathname.startsWith("/relatorios")) return "Relatórios";
  return "SGGI";
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
            <Route path="/" element={<GarantiasList />} />
            <Route path="/garantias" element={<Navigate to="/" replace />} />
            <Route path="/garantias/nova-danfe" element={<GarantiaDanfe />} />
            <Route path="/garantias/nova" element={<GarantiaNova />} />
            <Route path="/garantias/:id" element={<GarantiaFicha />} />
            <Route path="/relatorios" element={<Relatorios />} />
            <Route
              path="/relatorios/erro-interno"
              element={<Navigate to="/relatorios" replace />}
            />
            <Route path="/alertas-reincidencia" element={<Navigate to="/relatorios" replace />} />
            {/* Fora do MVP / Dashboard antigo: redirect */}
            <Route path="/dashboard" element={<Navigate to="/" replace />} />
            <Route path="/regras-prazo" element={<Navigate to="/" replace />} />
            <Route path="/movimentos-globus" element={<Navigate to="/" replace />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}
