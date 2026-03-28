from pydantic import BaseModel, Field


class MePatchBody(BaseModel):
    handle: str | None = None


class FriendRequestBody(BaseModel):
    to_sub: str


class FriendFromBody(BaseModel):
    from_sub: str


class PlinkoAwardBody(BaseModel):
    drop_id: str
    points: float = Field(..., ge=0)
    gemini_value: float | None = None
