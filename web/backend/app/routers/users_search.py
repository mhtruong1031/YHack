from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select

from app.auth import get_current_user
from app.deps import DbSession
from app.models import User

router = APIRouter(prefix="/api/users", tags=["users"])


def _like_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _like_contains(s: str) -> str:
    """SQL ILIKE pattern: substring match anywhere (not only prefix)."""
    return f"%{_like_escape(s)}%"


@router.get("/search")
async def search_users(
    session: DbSession,
    user: dict[str, Any] = Depends(get_current_user),
    q: str = Query("", min_length=1),
) -> dict[str, Any]:
    """
    Search other users by **display name** or **@handle** (case-insensitive substring).

    ``name`` comes from Auth0 ``name`` or ``nickname`` (see ``/api/me`` upsert).
    """
    raw = q.strip()
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="q required",
        )
    me = user["sub"]
    pattern = _like_contains(raw)
    stmt = (
        select(User)
        .where(
            User.sub != me,
            or_(
                User.name.ilike(pattern, escape="\\"),
                User.handle.ilike(pattern, escape="\\"),
            ),
        )
        .limit(50)
    )
    rows = (await session.execute(stmt)).scalars().all()
    results = [
        {
            "sub": doc.sub,
            "name": doc.name,
            "picture": doc.picture,
            "handle": doc.handle,
        }
        for doc in rows
    ]
    return {"results": results}
