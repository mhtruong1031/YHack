import { NavLink, Link } from "react-router-dom";
import { useAuth0 } from "@auth0/auth0-react";

type AppNavProps = {
  minimal?: boolean;
};

export function AppNav({ minimal = false }: AppNavProps) {
  const { logout, user } = useAuth0();

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    isActive ? "active" : undefined;

  return (
    <header className="landing-nav app-header-nav">
      <Link to="/" className="landing-nav-brand">
        DumpsterFire
      </Link>
      {minimal ? (
        <nav className="landing-nav-links" aria-label="Main">
          <Link to="/">Home</Link>
        </nav>
      ) : (
        <div className="landing-nav-app-end">
          <nav className="landing-nav-links" aria-label="App">
            <NavLink to="/explore" className={linkClass}>
              Explore
            </NavLink>
            <NavLink to="/leaderboard" className={linkClass}>
              Leaderboard
            </NavLink>
            <NavLink to="/plinko" className={linkClass}>
              Plinko
            </NavLink>
          </nav>
          <div className="landing-nav-user-actions">
            {user?.name && (
              <span className="landing-nav-user muted">{user.name}</span>
            )}
            <button
              type="button"
              className="landing-nav-logout"
              onClick={() =>
                logout({ logoutParams: { returnTo: window.location.origin } })
              }
            >
              Log out
            </button>
          </div>
        </div>
      )}
    </header>
  );
}
