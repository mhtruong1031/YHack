from urllib.parse import urlparse

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import get_settings

_client: AsyncIOMotorClient | None = None
_DEFAULT_DB = "recycling"


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(get_settings().mongodb_uri)
    return _client


def get_database() -> AsyncIOMotorDatabase:
    client = get_client()
    path = urlparse(get_settings().mongodb_uri).path.strip("/")
    if path:
        name = path.split("/")[0]
        return client[name]
    return client[_DEFAULT_DB]


async def init_indexes() -> None:
    db = get_database()
    await db.users.create_index("handle", unique=True, sparse=True)
    await db.friend_edges.create_index(
        [("from_sub", 1), ("to_sub", 1)],
        unique=True,
        partialFilterExpression={"status": "pending"},
        name="unique_pending_direction",
    )
    await db.friend_edges.create_index([("to_sub", 1), ("status", 1)])
    await db.friend_edges.create_index([("from_sub", 1), ("status", 1)])
    await db.point_ledger.create_index(
        [("user_sub", 1), ("drop_id", 1)],
        unique=True,
        name="unique_award_per_drop",
    )
    await db.point_ledger.create_index([("user_sub", 1), ("week_id", 1)])
    await db.drops.create_index("drop_id", unique=True)
    await db.users.create_index("name")
