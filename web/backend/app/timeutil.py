from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def week_id_for(dt: datetime | None = None) -> str:
    d = (dt or utc_now()).date()
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"
