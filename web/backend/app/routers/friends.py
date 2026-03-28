from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.auth import get_current_user
from app.db import get_database
from app.schemas import FriendFromBody, FriendRequestBody
from app.timeutil import utc_now

router = APIRouter(prefix="/api/friends", tags=["friends"])


@router.post("/request")
async def friend_request(
    body: FriendRequestBody,
    user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> dict[str, Any]:
    db = get_database()
    me = user["sub"]
    if body.to_sub == me:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cannot request yourself",
        )
    other = await db.users.find_one({"sub": body.to_sub})
    if not other:
        raise HTTPException(status_code=404, detail="user not found")
    existing = await db.friend_edges.find_one(
        {
            "from_sub": me,
            "to_sub": body.to_sub,
            "status": "pending",
        }
    )
    if existing:
        return {"status": "already_pending"}
    rev = await db.friend_edges.find_one(
        {
            "from_sub": body.to_sub,
            "to_sub": me,
            "status": "pending",
        }
    )
    if rev:
        return {"status": "they_pending_you", "hint": "use /accept"}
    accepted = await db.friend_edges.find_one(
        {
            "status": "accepted",
            "$or": [
                {"from_sub": me, "to_sub": body.to_sub},
                {"from_sub": body.to_sub, "to_sub": me},
            ],
        }
    )
    if accepted:
        return {"status": "already_friends"}
    try:
        await db.friend_edges.insert_one(
            {
                "from_sub": me,
                "to_sub": body.to_sub,
                "status": "pending",
                "created_at": utc_now(),
            }
        )
    except DuplicateKeyError:
        return {"status": "already_pending"}
    return {"status": "sent"}


@router.post("/accept")
async def friend_accept(
    body: FriendFromBody,
    user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> dict[str, Any]:
    db = get_database()
    me = user["sub"]
    res = await db.friend_edges.update_one(
        {
            "from_sub": body.from_sub,
            "to_sub": me,
            "status": "pending",
        },
        {"$set": {"status": "accepted"}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="no pending request")
    return {"status": "accepted"}


@router.post("/reject")
async def friend_reject(
    body: FriendFromBody,
    user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> dict[str, Any]:
    db = get_database()
    me = user["sub"]
    res = await db.friend_edges.delete_one(
        {
            "from_sub": body.from_sub,
            "to_sub": me,
            "status": "pending",
        }
    )
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="no pending request")
    return {"status": "rejected"}


@router.get("/pending")
async def friends_pending(
    user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> dict[str, Any]:
    db = get_database()
    me = user["sub"]
    cursor = db.friend_edges.find(
        {"to_sub": me, "status": "pending"},
        {"from_sub": 1, "created_at": 1},
    )
    from_subs = []
    async for e in cursor:
        from_subs.append(e["from_sub"])
    users = []
    if from_subs:
        ucursor = db.users.find(
            {"sub": {"$in": from_subs}},
            {"sub": 1, "name": 1, "picture": 1, "handle": 1},
        )
        by = {d["sub"]: d async for d in ucursor}
        for fs in from_subs:
            u = by.get(fs, {"sub": fs})
            users.append(
                {
                    "sub": u["sub"],
                    "name": u.get("name"),
                    "picture": u.get("picture"),
                    "handle": u.get("handle"),
                }
            )
    return {"incoming": users}
