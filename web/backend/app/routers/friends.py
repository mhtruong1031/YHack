from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, delete, or_, select, update
from sqlalchemy.exc import IntegrityError

from app.auth import get_current_user
from app.deps import DbSession
from app.models import FriendEdge, User
from app.schemas import FriendFromBody, FriendRequestBody
from app.timeutil import utc_now

router = APIRouter(prefix="/api/friends", tags=["friends"])


@router.post("/request")
async def friend_request(
    session: DbSession,
    body: FriendRequestBody,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    me = user["sub"]
    if body.to_sub == me:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cannot request yourself",
        )
    other = await session.get(User, body.to_sub)
    if not other:
        raise HTTPException(status_code=404, detail="user not found")

    existing = (
        await session.execute(
            select(FriendEdge).where(
                FriendEdge.from_sub == me,
                FriendEdge.to_sub == body.to_sub,
                FriendEdge.status == "pending",
            )
        )
    ).scalar_one_or_none()
    if existing:
        return {"status": "already_pending"}

    rev = (
        await session.execute(
            select(FriendEdge).where(
                FriendEdge.from_sub == body.to_sub,
                FriendEdge.to_sub == me,
                FriendEdge.status == "pending",
            )
        )
    ).scalar_one_or_none()
    if rev:
        return {"status": "they_pending_you", "hint": "use /accept"}

    accepted = (
        await session.execute(
            select(FriendEdge).where(
                FriendEdge.status == "accepted",
                or_(
                    and_(FriendEdge.from_sub == me, FriendEdge.to_sub == body.to_sub),
                    and_(FriendEdge.from_sub == body.to_sub, FriendEdge.to_sub == me),
                ),
            )
        )
    ).scalar_one_or_none()
    if accepted:
        return {"status": "already_friends"}

    session.add(
        FriendEdge(
            from_sub=me,
            to_sub=body.to_sub,
            status="pending",
            created_at=utc_now(),
        )
    )
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        return {"status": "already_pending"}
    return {"status": "sent"}


@router.post("/accept")
async def friend_accept(
    session: DbSession,
    body: FriendFromBody,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    me = user["sub"]
    res = await session.execute(
        update(FriendEdge)
        .where(
            FriendEdge.from_sub == body.from_sub,
            FriendEdge.to_sub == me,
            FriendEdge.status == "pending",
        )
        .values(status="accepted")
    )
    if res.rowcount == 0:
        raise HTTPException(status_code=404, detail="no pending request")
    return {"status": "accepted"}


@router.post("/reject")
async def friend_reject(
    session: DbSession,
    body: FriendFromBody,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    me = user["sub"]
    res = await session.execute(
        delete(FriendEdge).where(
            FriendEdge.from_sub == body.from_sub,
            FriendEdge.to_sub == me,
            FriendEdge.status == "pending",
        )
    )
    if res.rowcount == 0:
        raise HTTPException(status_code=404, detail="no pending request")
    return {"status": "rejected"}


@router.get("/pending")
async def friends_pending(
    session: DbSession,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    me = user["sub"]
    edges = (
        await session.execute(
            select(FriendEdge.from_sub).where(
                FriendEdge.to_sub == me,
                FriendEdge.status == "pending",
            )
        )
    ).scalars().all()
    from_subs = list(edges)
    users_out: list[dict[str, Any]] = []
    if from_subs:
        rows = (
            await session.execute(
                select(User).where(User.sub.in_(from_subs))
            )
        ).scalars().all()
        by = {u.sub: u for u in rows}
        for fs in from_subs:
            u = by.get(fs)
            if u:
                users_out.append(
                    {
                        "sub": u.sub,
                        "name": u.name,
                        "picture": u.picture,
                        "handle": u.handle,
                    }
                )
            else:
                users_out.append({"sub": fs})
    return {"incoming": users_out}
