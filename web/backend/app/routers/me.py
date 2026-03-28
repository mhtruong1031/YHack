from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.auth import get_current_user
from app.db import get_database
from app.schemas import MePatchBody
from app.timeutil import utc_now
router = APIRouter(prefix="/api", tags=["me"])


def _claims_profile(claims: dict[str, Any]) -> dict[str, Any]:
    return {
        "sub": claims["sub"],
        "email": claims.get("email"),
        "name": claims.get("name") or claims.get("nickname"),
        "picture": claims.get("picture"),
    }


@router.get("/me")
async def get_me(
    user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> dict[str, Any]:
    db = get_database()
    cp = _claims_profile(user)
    sub = cp["sub"]
    now = utc_now()
    await db.users.update_one(
        {"sub": sub},
        {
            "$set": {
                "email": cp["email"],
                "name": cp["name"],
                "picture": cp["picture"],
                "updated_at": now,
            },
            "$setOnInsert": {"sub": sub},
        },
        upsert=True,
    )
    doc = await db.users.find_one({"sub": sub})
    total_points = await _sum_user_points(db, sub, scope="lifetime")
    out = {
        "sub": doc.get("sub"),
        "email": doc.get("email"),
        "name": doc.get("name"),
        "picture": doc.get("picture"),
        "handle": doc.get("handle"),
        "updated_at": doc.get("updated_at"),
        "totals": {"lifetime_points": total_points},
    }
    return out


async def _sum_user_points(db, user_sub: str, scope: str) -> float:
    match: dict[str, Any] = {"user_sub": user_sub}
    if scope == "weekly":
        from app.timeutil import week_id_for

        match["week_id"] = week_id_for()
    cursor = db.point_ledger.aggregate(
        [{"$match": match}, {"$group": {"_id": None, "t": {"$sum": "$points"}}}]
    )
    async for row in cursor:
        return float(row.get("t", 0.0))
    return 0.0


@router.patch("/me")
async def patch_me(
    body: MePatchBody,
    user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> dict[str, Any]:
    db = get_database()
    sub = user["sub"]
    if body.handle is not None:
        handle = body.handle.strip().lower()
        if not handle:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="handle cannot be empty",
            )
        try:
            await db.users.update_one(
                {"sub": sub},
                {
                    "$set": {"handle": handle, "updated_at": utc_now()},
                    "$setOnInsert": {"sub": sub},
                },
                upsert=True,
            )
        except DuplicateKeyError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="handle already taken",
            ) from None
    doc = await db.users.find_one({"sub": sub})
    if not doc:
        raise HTTPException(status_code=404, detail="user not found")
    return {
        "sub": doc["sub"],
        "email": doc.get("email"),
        "name": doc.get("name"),
        "picture": doc.get("picture"),
        "handle": doc.get("handle"),
        "updated_at": doc.get("updated_at"),
    }
