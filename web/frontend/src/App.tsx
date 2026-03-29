import { Auth0Provider } from "@auth0/auth0-react";
import { BrowserRouter, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { Explore } from "./pages/Explore";
import { Leaderboard } from "./pages/Leaderboard";
import { Login } from "./pages/Login";
import { Plinko } from "./pages/Plinko";
import { Splash } from "./pages/Splash";

function AppWithAuth() {
  const navigate = useNavigate();
  const domain = import.meta.env.VITE_AUTH0_DOMAIN?.trim();
  const clientId = import.meta.env.VITE_AUTH0_CLIENT_ID?.trim();
  const audience = import.meta.env.VITE_AUTH0_AUDIENCE?.trim();

  if (!domain || !clientId) {
    return (
      <div className="page-wrap">
        <p>
          Set <code>VITE_AUTH0_DOMAIN</code> and <code>VITE_AUTH0_CLIENT_ID</code> in{" "}
          <code>.env</code> (see <code>.env.example</code>).
        </p>
      </div>
    );
  }

  return (
    <Auth0Provider
      domain={domain}
      clientId={clientId}
      authorizationParams={{
        redirect_uri: window.location.origin,
        ...(audience ? { audience } : {}),
      }}
      onRedirectCallback={(appState) => {
        navigate(appState?.returnTo ?? "/explore", { replace: true });
      }}
    >
      <Routes>
        <Route path="/" element={<Splash />} />
        <Route path="/login" element={<Login />} />
        <Route
          path="/leaderboard"
          element={
            <ProtectedRoute>
              <Leaderboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/plinko"
          element={
            <ProtectedRoute>
              <Plinko />
            </ProtectedRoute>
          }
        />
        <Route
          path="/explore"
          element={
            <ProtectedRoute>
              <Explore />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Auth0Provider>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppWithAuth />
    </BrowserRouter>
  );
}
