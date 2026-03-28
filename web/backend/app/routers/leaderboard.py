from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query

from app.auth import get_current_user
from app.db import get_database
from app.timeutil import week_id_for

router = APIRouter(prefix="/api", tags=["leaderboard"])


async def _friend_subs(db, me: str) -> list[str]:
    cursor = db.friend_edges.find(
        {
            "status": "accepted",
            "$or": [{"from_sub": me}, {"to_sub": me}],
        },
        {"from_sub": 1, "to_sub": 1},
    )
    out: set[str] = set()
    async for e in cursor:
        a, b = e["from_sub"], e["to_sub"]
        other = b if a == me else a
        out.add(other)
    return list(out)


@router.get("/leaderboard")
async def leaderboard(
    user: Annotated[dict[str, Any], Depends(get_current_user)],
    scope: Literal["lifetime", "weekly"] = Query("lifetime"),
) -> dict[str, Any]:
    db = get_database()
    me = user["sub"]
    friends = await _friend_subs(db, me)
    if not friends:
        return {"scope": scope, "entries": []}

    match: dict[str, Any] = {"user_sub": {"$in": friends}}
    if scope == "weekly":
        match["week_id"] = week_id_for()

    pipeline = [
        {"$match": match},
        {
            "$group": {
                "_id": "$user_sub",
                "points": {"$sum": {"$ifNull": ["$gemini_value", 0]}},
            }
        },
    ]
    agg: dict[str, float] = {}
    async for row in db.point_ledger.aggregate(pipeline):
        agg[row["_id"]] = float(row["points"])

    users = await db.users.find({"sub": {"$in": friends}}).to_list(length=None)
    by_sub = {u["sub"]: u for u in users}

    entries = []
    for sub in friends:
        u = by_sub.get(sub, {})
        entries.append(
            {
                "sub": sub,
                "name": u.get("name"),
                "picture": u.get("picture"),
                "points": agg.get(sub, 0.0),
            }
        )
    entries.sort(key=lambda x: x["points"], reverse=True)
    return {"scope": scope, "entries": entries}
