import { useAuth0 } from "@auth0/auth0-react";
import type { MouseEvent } from "react";
import { Link, NavLink } from "react-router-dom";

const APP_NAV = [
  { to: "/explore", label: "Explore" },
  { to: "/leaderboard", label: "Leaderboard" },
  { to: "/plinko", label: "Plinko" },
] as const;

export function Splash() {
  const { isAuthenticated, isLoading, loginWithRedirect } = useAuth0();

  const start = () => {
    if (isAuthenticated) return;
    loginWithRedirect({
      appState: { returnTo: "/explore" },
    });
  };

  const handleProtectedNav = (
    path: string,
    e: MouseEvent<HTMLAnchorElement>
  ) => {
    if (isLoading) {
      e.preventDefault();
      return;
    }
    if (!isAuthenticated) {
      e.preventDefault();
      loginWithRedirect({ appState: { returnTo: path } });
    }
  };

  return (
    <div className="landing">
      <header className="landing-nav">
        <Link to="/" className="landing-nav-brand">
          DumpsterFire
        </Link>
        <nav className="landing-nav-links" aria-label="Main">
          {APP_NAV.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              onClick={(e) => handleProtectedNav(to, e)}
            >
              {label}
            </NavLink>
          ))}
        </nav>
      </header>

      <main>
        <section className="landing-hero" aria-label="Introduction">
          <h1>Recycling. Made Social.</h1>
          <p className="landing-hero-sub">
            Sort smarter, see your impact, and compete with friends—all in one
            place.
          </p>
          <div className="landing-hero-cta">
            {isLoading ? (
              <p className="muted" style={{ margin: 0 }}>
                Loading…
              </p>
            ) : isAuthenticated ? (
              <Link to="/explore">
                <button type="button" className="landing-cta-liquid">
                  Get started
                </button>
              </Link>
            ) : (
              <button
                type="button"
                className="landing-cta-liquid"
                onClick={start}
              >
                Get started
              </button>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
