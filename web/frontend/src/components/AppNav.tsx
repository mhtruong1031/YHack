import { NavLink } from "react-router-dom";
import { useAuth0 } from "@auth0/auth0-react";

export function AppNav() {
  const { logout, user } = useAuth0();
  return (
    <nav className="app-nav">
      <div className="app-nav-links">
        <NavLink to="/explore" className={({ isActive }) => (isActive ? "app-nav-link active" : "app-nav-link")}>
          Explore
        </NavLink>
        <NavLink to="/leaderboard" className={({ isActive }) => (isActive ? "app-nav-link active" : "app-nav-link")}>
          Leaderboard
        </NavLink>
        <NavLink to="/plinko" className={({ isActive }) => (isActive ? "app-nav-link active" : "app-nav-link")}>
          Plinko
        </NavLink>
      </div>
      {user?.name && <span className="muted">{user.name}</span>}
      <button
        type="button"
        onClick={() =>
          logout({ logoutParams: { returnTo: window.location.origin } })
        }
      >
        Log out
      </button>
      <style>{`
        .app-nav {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 0.75rem 1rem;
          margin-bottom: 1rem;
          padding-bottom: 0.85rem;
          border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        .app-nav-links {
          display: flex;
          flex-wrap: wrap;
          gap: 1rem;
          flex: 1;
        }
      `}</style>
    </nav>
  );
}
