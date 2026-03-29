from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from app.auth import get_current_user
from app.deps import DbSession
from app.models import Drop, PointLedger
from app.schemas import PlinkoAwardBody
from app.timeutil import utc_now, week_id_for

router = APIRouter(prefix="/api/plinko", tags=["plinko"])


@router.post("/award")
async def plinko_award(
    session: DbSession,
    body: PlinkoAwardBody,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    sub = user["sub"]
    drop = await session.get(Drop, body.drop_id)
    gem = body.gemini_value
    if gem is None and drop is not None:
        gem = float(drop.gemini_value)
    if gem is None:
        gem = 0.0

    value_usd = float(gem)
    existing = (
        await session.execute(
            select(PointLedger.id).where(
                PointLedger.user_sub == sub,
                PointLedger.drop_id == body.drop_id,
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        session.add(
            PointLedger(
                user_sub=sub,
                points=value_usd,
                source="plinko",
                drop_id=body.drop_id,
                week_id=week_id_for(),
                gemini_value=value_usd,
                created_at=utc_now(),
            )
        )
        await session.flush()
        awarded = True
    else:
        awarded = False

    total_q = select(func.coalesce(func.sum(PointLedger.gemini_value), 0.0)).where(
        PointLedger.user_sub == sub
    )
    total = float((await session.execute(total_q)).scalar_one() or 0.0)

    return {
        "awarded": awarded,
        "drop_id": body.drop_id,
        "lifetime_points": total,
    }
