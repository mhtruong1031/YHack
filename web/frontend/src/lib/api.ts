const apiBase = () => import.meta.env.VITE_API_BASE_URL || "";

export async function apiFetch(
  path: string,
  init: RequestInit & { token?: string | null } = {}
): Promise<Response> {
  const { token, headers: h, ...rest } = init;
  const headers = new Headers(h);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (!headers.has("Content-Type") && rest.body && !(rest.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  return fetch(`${apiBase()}${path}`, { ...rest, headers });
}

export type Me = {
  sub: string;
  name?: string;
  nickname?: string;
  picture?: string;
  email?: string;
  /** Sum of estimated recyclable deposit value (USD) from device + completed drops */
  totals?: { lifetime_points: number };
};

export async function getMe(token: string): Promise<Me> {
  const r = await apiFetch("/api/me", { token });
  if (!r.ok) throw new Error(await r.text());
  return r.json() as Promise<Me>;
}

export async function patchMe(token: string, body: Record<string, unknown>): Promise<Me> {
  const r = await apiFetch("/api/me", {
    method: "PATCH",
    token,
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json() as Promise<Me>;
}

export type LeaderboardEntry = {
  sub: string;
  name?: string;
  points: number;
  rank?: number;
};

export async function getLeaderboard(
  token: string,
  scope: "lifetime" | "weekly"
): Promise<LeaderboardEntry[]> {
  const r = await apiFetch(`/api/leaderboard?scope=${encodeURIComponent(scope)}`, {
    token,
  });
  if (!r.ok) throw new Error(await r.text());
  const data = (await r.json()) as { entries?: LeaderboardEntry[] } | LeaderboardEntry[];
  return Array.isArray(data) ? data : data.entries ?? [];
}

export type UserSearchHit = {
  sub: string;
  name?: string;
  picture?: string;
};

export async function searchUsers(token: string, q: string): Promise<UserSearchHit[]> {
  const r = await apiFetch(`/api/users/search?q=${encodeURIComponent(q)}`, { token });
  if (!r.ok) throw new Error(await r.text());
  const data = (await r.json()) as {
    results?: UserSearchHit[];
    users?: UserSearchHit[];
  };
  if (Array.isArray(data)) return data as UserSearchHit[];
  return data.results ?? data.users ?? [];
}

export type PendingFriend = {
  from_sub: string;
  name?: string;
  picture?: string;
};

export async function getPendingFriends(token: string): Promise<PendingFriend[]> {
  const r = await apiFetch("/api/friends/pending", { token });
  if (!r.ok) throw new Error(await r.text());
  const data = (await r.json()) as {
    incoming?: Array<{ sub: string; name?: string; picture?: string }>;
    pending?: PendingFriend[];
  };
  if (Array.isArray(data)) return data as PendingFriend[];
  if (data.pending?.length) return data.pending;
  const inc = data.incoming ?? [];
  return inc.map((u) => ({
    from_sub: u.sub,
    name: u.name,
    picture: u.picture,
  }));
}

export async function requestFriend(token: string, to_sub: string): Promise<void> {
  const r = await apiFetch("/api/friends/request", {
    method: "POST",
    token,
    body: JSON.stringify({ to_sub }),
  });
  if (!r.ok) throw new Error(await r.text());
}

export async function acceptFriend(token: string, from_sub: string): Promise<void> {
  const r = await apiFetch("/api/friends/accept", {
    method: "POST",
    token,
    body: JSON.stringify({ from_sub }),
  });
  if (!r.ok) throw new Error(await r.text());
}

export async function rejectFriend(token: string, from_sub: string): Promise<void> {
  const r = await apiFetch("/api/friends/reject", {
    method: "POST",
    token,
    body: JSON.stringify({ from_sub }),
  });
  if (!r.ok) throw new Error(await r.text());
}

export async function postPlinkoAward(
  token: string,
  body: { drop_id: string; gemini_value?: number | null }
): Promise<{ awarded: boolean; lifetime_points: number }> {
  const r = await apiFetch("/api/plinko/award", {
    method: "POST",
    token,
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json() as Promise<{ awarded: boolean; lifetime_points: number }>;
}
