from pydantic import BaseModel


class MePatchBody(BaseModel):
    handle: str | None = None


class FriendRequestBody(BaseModel):
    to_sub: str


class FriendFromBody(BaseModel):
    from_sub: str


class PlinkoAwardBody(BaseModel):
    drop_id: str
    gemini_value: float | None = None
