import { useAuth0 } from "@auth0/auth0-react";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AppLayout } from "../components/AppLayout";
import {
  acceptFriend,
  getMe,
  getPendingFriends,
  rejectFriend,
  requestFriend,
  searchUsers,
  type PendingFriend,
  type UserSearchHit,
} from "../lib/api";
import { formatUsd } from "../lib/formatUsd";

export function Explore() {
  const { getAccessTokenSilently } = useAuth0();
  const audience = import.meta.env.VITE_AUTH0_AUDIENCE;
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<UserSearchHit[]>([]);
  const [pending, setPending] = useState<PendingFriend[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [myRecycledUsd, setMyRecycledUsd] = useState<number | null>(null);

  const tokenOpts = audience ? { authorizationParams: { audience } } : undefined;

  const refreshMeTotal = useCallback(async () => {
    try {
      const token = await getAccessTokenSilently(tokenOpts);
      const me = await getMe(token);
      const t = me.totals?.lifetime_points;
      setMyRecycledUsd(typeof t === "number" ? t : 0);
    } catch {
      /* ignore */
    }
  }, [getAccessTokenSilently, audience]);

  useEffect(() => {
    void refreshMeTotal();
    const id = window.setInterval(() => void refreshMeTotal(), 4000);
    return () => clearInterval(id);
  }, [refreshMeTotal]);

  const refreshPending = useCallback(async () => {
    try {
      const token = await getAccessTokenSilently(tokenOpts);
      const p = await getPendingFriends(token);
      setPending(p);
    } catch {
      /* ignore */
    }
  }, [getAccessTokenSilently, audience]);

  useEffect(() => {
    void refreshPending();
  }, [refreshPending]);

  useEffect(() => {
    if (q.trim().length < 2) {
      setHits([]);
      return;
    }
    const t = window.setTimeout(() => {
      void (async () => {
        setErr(null);
        try {
          const token = await getAccessTokenSilently(tokenOpts);
          const u = await searchUsers(token, q.trim());
          setHits(u);
        } catch (e) {
          setErr(e instanceof Error ? e.message : "Search failed");
        }
      })();
    }, 300);
    return () => window.clearTimeout(t);
  }, [q, getAccessTokenSilently, audience]);

  async function onRequest(to_sub: string) {
    setBusy(to_sub);
    setMsg(null);
    setErr(null);
    try {
      const token = await getAccessTokenSilently(tokenOpts);
      await requestFriend(token, to_sub);
      setMsg("Friend request sent.");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Request failed");
    } finally {
      setBusy(null);
    }
  }

  async function onAccept(from_sub: string) {
    setBusy(from_sub);
    setErr(null);
    try {
      const token = await getAccessTokenSilently(tokenOpts);
      await acceptFriend(token, from_sub);
      setMsg("Friend accepted.");
      await refreshPending();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Accept failed");
    } finally {
      setBusy(null);
    }
  }

  async function onReject(from_sub: string) {
    setBusy(from_sub);
    setErr(null);
    try {
      const token = await getAccessTokenSilently(tokenOpts);
      await rejectFriend(token, from_sub);
      setMsg("Request dismissed.");
      await refreshPending();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Reject failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <AppLayout>
      <div className="row" style={{ marginBottom: "0.5rem" }}>
          <span className="badge" title="Updates when your hardware sends a new sort">
            Your recycled value:{" "}
            {myRecycledUsd === null ? "…" : formatUsd(myRecycledUsd)}
          </span>
          <Link to="/" className="muted" style={{ marginLeft: "auto" }}>
            Home
          </Link>
        </div>
        {msg && <p className="status-line ok">{msg}</p>}
        {err && <p className="status-line error">{err}</p>}

        <h2 style={{ fontSize: "1rem", margin: "1rem 0 0.5rem" }}>Find people</h2>
        <input
          type="search"
          placeholder="Search by name…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          style={{ maxWidth: "100%" }}
        />
        <ul style={{ listStyle: "none", padding: 0, margin: "0.75rem 0 0" }}>
          {hits.map((u) => (
            <li
              key={u.sub}
              className="row"
              style={{
                justifyContent: "space-between",
                padding: "0.5rem 0",
                borderBottom: "1px solid rgba(255,255,255,0.06)",
              }}
            >
              <span>{u.name ?? u.sub}</span>
              <button
                type="button"
                disabled={busy === u.sub}
                onClick={() => void onRequest(u.sub)}
              >
                Add friend
              </button>
            </li>
          ))}
        </ul>

        <h2 style={{ fontSize: "1rem", margin: "1.25rem 0 0.5rem" }}>
          Pending requests
        </h2>
        {pending.length === 0 ? (
          <p className="muted">No pending invites.</p>
        ) : (
          <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
            {pending.map((p) => (
              <li
                key={p.from_sub}
                className="row"
                style={{
                  justifyContent: "space-between",
                  padding: "0.5rem 0",
                  borderBottom: "1px solid rgba(255,255,255,0.06)",
                }}
              >
                <span>{p.name ?? p.from_sub}</span>
                <div className="row">
                  <button
                    type="button"
                    className="primary"
                    disabled={busy === p.from_sub}
                    onClick={() => void onAccept(p.from_sub)}
                  >
                    Accept
                  </button>
                  <button
                    type="button"
                    disabled={busy === p.from_sub}
                    onClick={() => void onReject(p.from_sub)}
                  >
                    Reject
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
    </AppLayout>
  );
}
