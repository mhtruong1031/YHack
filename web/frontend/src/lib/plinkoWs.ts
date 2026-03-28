/** WebSocket URL for Plinko: ws(s)://host/ws/plinko?token= */
export function getPlinkoWebSocketUrl(accessToken: string): string {
  const base = import.meta.env.VITE_API_BASE_URL?.trim();
  if (base) {
    const u = new URL(base);
    u.protocol = u.protocol === "https:" ? "wss:" : "ws:";
    u.pathname = "/ws/plinko";
    u.search = "";
    u.hash = "";
    const q = new URLSearchParams({ token: accessToken });
    return `${u.toString().replace(/\/$/, "")}?${q.toString()}`;
  }
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  const q = new URLSearchParams({ token: accessToken });
  return `${proto}//${window.location.host}/ws/plinko?${q.toString()}`;
}
