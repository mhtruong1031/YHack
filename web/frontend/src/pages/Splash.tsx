import { useAuth0 } from "@auth0/auth0-react";
import { Link } from "react-router-dom";
import { MacWindow } from "../components/MacWindow";

export function Splash() {
  const { isAuthenticated, isLoading, loginWithRedirect } = useAuth0();

  return (
    <div className="page-wrap">
      <MacWindow title="Recycle Social">
        <div className="stack" style={{ alignItems: "center", textAlign: "center" }}>
          <h1 style={{ margin: 0, fontSize: "1.65rem", fontWeight: 700 }}>
            Sort smarter. Compete with friends.
          </h1>
          <p className="muted" style={{ maxWidth: "28rem", margin: 0 }}>
            Track recycling impact, climb the leaderboard, and drop Plinko rewards
            from your sorted items.
          </p>
          {isLoading ? (
            <p className="muted">Loading…</p>
          ) : isAuthenticated ? (
            <div className="row" style={{ justifyContent: "center" }}>
              <Link to="/explore">
                <button type="button" className="primary">
                  Go to app
                </button>
              </Link>
            </div>
          ) : (
            <div className="row" style={{ justifyContent: "center" }}>
              <button
                type="button"
                className="primary"
                onClick={() =>
                  loginWithRedirect({
                    appState: { returnTo: "/explore" },
                  })
                }
              >
                Log in
              </button>
              <Link to="/login">
                <button type="button">Auth page</button>
              </Link>
            </div>
          )}
        </div>
      </MacWindow>
    </div>
  );
}
