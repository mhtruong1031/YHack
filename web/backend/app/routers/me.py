from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError

from app.auth import get_current_user
from app.deps import DbSession
from app.models import PointLedger, User
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
    session: DbSession,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    cp = _claims_profile(user)
    sub = cp["sub"]
    now = utc_now()
    stmt = (
        pg_insert(User)
        .values(
            sub=sub,
            email=cp["email"],
            name=cp["name"],
            picture=cp["picture"],
            updated_at=now,
        )
        .on_conflict_do_update(
            index_elements=["sub"],
            set_={
                "email": cp["email"],
                "name": cp["name"],
                "picture": cp["picture"],
                "updated_at": now,
            },
        )
    )
    await session.execute(stmt)
    await session.flush()
    row = await session.get(User, sub)
    total_points = await _sum_user_points(session, sub, scope="lifetime")
    return {
        "sub": row.sub if row else sub,
        "email": row.email if row else None,
        "name": row.name if row else None,
        "picture": row.picture if row else None,
        "handle": row.handle if row else None,
        "updated_at": row.updated_at if row else None,
        "totals": {"lifetime_points": total_points},
    }


async def _sum_user_points(session, user_sub: str, scope: str) -> float:
    q = select(func.coalesce(func.sum(PointLedger.gemini_value), 0.0)).where(
        PointLedger.user_sub == user_sub
    )
    if scope == "weekly":
        from app.timeutil import week_id_for

        q = q.where(PointLedger.week_id == week_id_for())
    total = (await session.execute(q)).scalar_one()
    return float(total or 0.0)


@router.patch("/me")
async def patch_me(
    session: DbSession,
    body: MePatchBody,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    sub = user["sub"]
    if body.handle is not None:
        handle = body.handle.strip().lower()
        if not handle:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="handle cannot be empty",
            )
        try:
            stmt = (
                pg_insert(User)
                .values(sub=sub, handle=handle, updated_at=utc_now())
                .on_conflict_do_update(
                    index_elements=["sub"],
                    set_={"handle": handle, "updated_at": utc_now()},
                )
            )
            await session.execute(stmt)
            await session.flush()
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="handle already taken",
            ) from None
    row = await session.get(User, sub)
    if not row:
        raise HTTPException(status_code=404, detail="user not found")
    return {
        "sub": row.sub,
        "email": row.email,
        "name": row.name,
        "picture": row.picture,
        "handle": row.handle,
        "updated_at": row.updated_at,
    }
