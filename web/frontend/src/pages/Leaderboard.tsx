import { useAuth0 } from "@auth0/auth0-react";
import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { AppLayout } from "../components/AppLayout";
import { getLeaderboard, type LeaderboardEntry } from "../lib/api";
import { formatUsd } from "../lib/formatUsd";

export function Leaderboard() {
  const { getAccessTokenSilently } = useAuth0();
  const audience = import.meta.env.VITE_AUTH0_AUDIENCE;
  const [searchParams, setSearchParams] = useSearchParams();
  const scopeParam = searchParams.get("scope");
  const scope: "lifetime" | "weekly" =
    scopeParam === "weekly" ? "weekly" : "lifetime";

  const [rows, setRows] = useState<LeaderboardEntry[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async (quiet?: boolean) => {
    if (!quiet) {
      setLoading(true);
      setErr(null);
    }
    try {
      const token = await getAccessTokenSilently({
        authorizationParams: audience ? { audience } : undefined,
      });
      const data = await getLeaderboard(token, scope);
      setRows(data);
    } catch (e) {
      if (!quiet) {
        setErr(e instanceof Error ? e.message : "Failed to load leaderboard");
      }
    } finally {
      if (!quiet) setLoading(false);
    }
  }, [getAccessTokenSilently, scope, audience]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    const id = window.setInterval(() => void load(true), 5000);
    return () => clearInterval(id);
  }, [load]);

  const setScope = (next: "lifetime" | "weekly") => {
    setSearchParams(next === "lifetime" ? {} : { scope: next });
  };

  return (
    <AppLayout>
      <div className="row fade-in-up" style={{ marginBottom: "1.5rem" }}>
          <div className="segment-control">
            <button
              type="button"
              className={scope === "lifetime" ? "primary" : undefined}
              onClick={() => setScope("lifetime")}
            >
              Lifetime
            </button>
            <button
              type="button"
              className={scope === "weekly" ? "primary" : undefined}
              onClick={() => setScope("weekly")}
            >
              Weekly
            </button>
          </div>
          <Link to="/" className="muted" style={{ marginLeft: "auto" }}>
            Home
          </Link>
        </div>
        {loading && <p className="muted fade-in-up-delay-1">Loading…</p>}
        {err && <p className="status-line error fade-in-up-delay-1">{err}</p>}
        {!loading && !err && (
          <div className="table-wrap fade-in-up-delay-1">
            <table>
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Friend</th>
                  <th>Recycled Value</th>
                </tr>
              </thead>
              <tbody>
                {rows.length === 0 ? (
                  <tr>
                    <td colSpan={3} className="muted" style={{ textAlign: "center" }}>
                      No entries yet.
                    </td>
                  </tr>
                ) : (
                  rows.map((r, i) => {
                    const rank = r.rank ?? i + 1;
                    const rankClass = rank <= 3 ? `rank-text-${rank}` : "";
                    
                    return (
                      <tr key={r.sub}>
                        <td>
                          <span className={rankClass}>{rank}</span>
                        </td>
                        <td style={{ fontWeight: 500 }}>{r.name ?? r.sub}</td>
                        <td style={{ color: "var(--success)", fontWeight: 600 }}>{formatUsd(r.points)}</td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        )}
    </AppLayout>
  );
}
