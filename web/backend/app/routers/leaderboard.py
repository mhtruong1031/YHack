from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select

from app.auth import get_current_user
from app.deps import DbSession
from app.models import FriendEdge, PointLedger, User
from app.timeutil import week_id_for

router = APIRouter(prefix="/api", tags=["leaderboard"])


async def _friend_subs(session, me: str) -> list[str]:
    rows = (
        await session.execute(
            select(FriendEdge).where(
                FriendEdge.status == "accepted",
                or_(FriendEdge.from_sub == me, FriendEdge.to_sub == me),
            )
        )
    ).scalars().all()
    out: set[str] = set()
    for e in rows:
        a, b = e.from_sub, e.to_sub
        other = b if a == me else a
        out.add(other)
    return list(out)


@router.get("/leaderboard")
async def leaderboard(
    session: DbSession,
    user: dict[str, Any] = Depends(get_current_user),
    scope: Literal["lifetime", "weekly"] = Query("lifetime"),
) -> dict[str, Any]:
    me = user["sub"]
    friends = await _friend_subs(session, me)
    if not friends:
        return {"scope": scope, "entries": []}

    q = (
        select(PointLedger.user_sub, func.coalesce(func.sum(PointLedger.gemini_value), 0.0))
        .where(PointLedger.user_sub.in_(friends))
        .group_by(PointLedger.user_sub)
    )
    if scope == "weekly":
        q = q.where(PointLedger.week_id == week_id_for())

    agg: dict[str, float] = {}
    for user_sub, points in (await session.execute(q)).all():
        agg[user_sub] = float(points or 0.0)

    users = (await session.execute(select(User).where(User.sub.in_(friends)))).scalars().all()
    by_sub = {u.sub: u for u in users}

    entries = []
    for sub in friends:
        u = by_sub.get(sub)
        entries.append(
            {
                "sub": sub,
                "name": u.name if u else None,
                "picture": u.picture if u else None,
                "points": agg.get(sub, 0.0),
            }
        )
    entries.sort(key=lambda x: x["points"], reverse=True)
    return {"scope": scope, "entries": entries}
