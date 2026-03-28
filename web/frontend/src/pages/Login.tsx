import { useAuth0 } from "@auth0/auth0-react";
import { useEffect } from "react";
import { Navigate } from "react-router-dom";
import { MacWindow } from "../components/MacWindow";

export function Login() {
  const { loginWithRedirect, isAuthenticated, isLoading } = useAuth0();

  useEffect(() => {
    if (isLoading || isAuthenticated) return;
    void loginWithRedirect({ appState: { returnTo: "/explore" } });
  }, [isAuthenticated, isLoading, loginWithRedirect]);

  if (isAuthenticated) {
    return <Navigate to="/explore" replace />;
  }

  return (
    <div className="page-wrap">
      <MacWindow title="Sign in">
        <div className="stack" style={{ alignItems: "center", textAlign: "center" }}>
          <p className="muted">
            {isAuthenticated
              ? "You are signed in."
              : "Redirecting to Auth0…"}
          </p>
          {!isAuthenticated && !isLoading && (
            <button
              type="button"
              className="primary"
              onClick={() =>
                loginWithRedirect({ appState: { returnTo: "/explore" } })
              }
            >
              Continue with login
            </button>
          )}
        </div>
      </MacWindow>
    </div>
  );
}
