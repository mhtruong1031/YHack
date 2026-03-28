from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pymongo.errors import DuplicateKeyError

from app.auth import get_current_user
from app.db import get_database
from app.schemas import PlinkoAwardBody
from app.timeutil import utc_now, week_id_for

router = APIRouter(prefix="/api/plinko", tags=["plinko"])


@router.post("/award")
async def plinko_award(
    body: PlinkoAwardBody,
    user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> dict[str, Any]:
    db = get_database()
    sub = user["sub"]
    drop = await db.drops.find_one({"drop_id": body.drop_id})
    gem = body.gemini_value
    if gem is None and drop is not None:
        gem = float(drop.get("gemini_value", 0.0))
    if gem is None:
        gem = 0.0

    value_usd = float(gem)
    doc = {
        "user_sub": sub,
        "points": value_usd,
        "source": "plinko",
        "drop_id": body.drop_id,
        "week_id": week_id_for(),
        "gemini_value": value_usd,
        "created_at": utc_now(),
    }
    try:
        await db.point_ledger.insert_one(doc)
        awarded = True
    except DuplicateKeyError:
        awarded = False

    pipeline = [
        {"$match": {"user_sub": sub}},
        {
            "$group": {
                "_id": None,
                "t": {"$sum": {"$ifNull": ["$gemini_value", 0]}},
            }
        },
    ]
    total = 0.0
    async for row in db.point_ledger.aggregate(pipeline):
        total = float(row.get("t", 0.0))

    return {
        "awarded": awarded,
        "drop_id": body.drop_id,
        "lifetime_points": total,
    }
