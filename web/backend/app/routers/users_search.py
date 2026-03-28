import re
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import get_current_user
from app.db import get_database

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/search")
async def search_users(
    user: Annotated[dict[str, Any], Depends(get_current_user)],
    q: str = Query("", min_length=1),
) -> dict[str, Any]:
    db = get_database()
    prefix = re.escape(q.strip())
    if not prefix:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="q required",
        )
    rx = {"$regex": f"^{prefix}", "$options": "i"}
    me = user["sub"]
    cursor = db.users.find(
        {
            "sub": {"$ne": me},
            "$or": [{"name": rx}, {"handle": rx}],
        },
        {"sub": 1, "name": 1, "picture": 1, "handle": 1},
    ).limit(50)
    results = []
    async for doc in cursor:
        results.append(
            {
                "sub": doc["sub"],
                "name": doc.get("name"),
                "picture": doc.get("picture"),
                "handle": doc.get("handle"),
            }
        )
    return {"results": results}
