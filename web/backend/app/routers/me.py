from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError

from app.auth import (
    decode_auth0_token,
    fetch_auth0_userinfo,
    merge_claims_and_userinfo,
)
from app.config import Settings, get_settings
from app.deps import DbSession
from app.models import PointLedger, User
from app.schemas import MePatchBody
from app.timeutil import utc_now

router = APIRouter(prefix="/api", tags=["me"])
_bearer = HTTPBearer()


def _display_name_from_claims(claims: dict[str, Any]) -> str | None:
    if claims.get("name"):
        return str(claims["name"]).strip() or None
    if claims.get("nickname"):
        return str(claims["nickname"]).strip() or None
    g = (claims.get("given_name") or "").strip()
    f = (claims.get("family_name") or "").strip()
    if g and f:
        return f"{g} {f}"
    return g or f or None


def _claims_profile(claims: dict[str, Any]) -> dict[str, Any]:
    return {
        "sub": claims["sub"],
        "email": claims.get("email"),
        "name": _display_name_from_claims(claims),
        "picture": claims.get("picture"),
    }


async def upsert_user_from_bearer(
    session: DbSession,
    creds: HTTPAuthorizationCredentials,
    settings: Settings,
) -> User:
    """Decode JWT, merge Auth0 /userinfo (profile lives there for API access tokens), upsert users row."""
    token = creds.credentials
    claims = await decode_auth0_token(token, settings)
    userinfo = await fetch_auth0_userinfo(settings.auth0_domain, token)
    merged = merge_claims_and_userinfo(claims, userinfo)
    cp = _claims_profile(merged)
    sub = cp["sub"]
    now = utc_now()
    ins = pg_insert(User).values(
        sub=sub,
        email=cp["email"],
        name=cp["name"],
        picture=cp["picture"],
        updated_at=now,
    )
    stmt = ins.on_conflict_do_update(
        index_elements=["sub"],
        set_={
            # Keep existing row values if Auth0 returns null this request (e.g. userinfo failed).
            "email": func.coalesce(ins.excluded.email, User.email),
            "name": func.coalesce(ins.excluded.name, User.name),
            "picture": func.coalesce(ins.excluded.picture, User.picture),
            "updated_at": ins.excluded.updated_at,
        },
    )
    await session.execute(stmt)
    await session.flush()
    row = await session.get(User, sub)
    if not row:
        raise HTTPException(status_code=500, detail="user upsert failed")
    return row


@router.get("/me")
async def get_me(
    session: DbSession,
    creds: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    row = await upsert_user_from_bearer(session, creds, settings)
    sub = row.sub
    total_points = await _sum_user_points(session, sub, scope="lifetime")
    return {
        "sub": row.sub,
        "email": row.email,
        "name": row.name,
        "picture": row.picture,
        "handle": row.handle,
        "updated_at": row.updated_at,
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
    creds: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    row = await upsert_user_from_bearer(session, creds, settings)
    sub = row.sub
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
