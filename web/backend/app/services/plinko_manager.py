import logging
from collections import defaultdict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class PlinkoConnectionManager:
    """Maps Auth0 sub -> active WebSocket connections for Plinko drop push."""

    def __init__(self) -> None:
        self._by_sub: dict[str, list[WebSocket]] = defaultdict(list)

    def register(self, sub: str, ws: WebSocket) -> None:
        self._by_sub[sub].append(ws)

    def unregister(self, sub: str, ws: WebSocket) -> None:
        conns = self._by_sub.get(sub)
        if not conns:
            return
        try:
            conns.remove(ws)
        except ValueError:
            pass
        if not conns:
            del self._by_sub[sub]

    def distinct_connected_subs(self) -> set[str]:
        return {s for s, wss in self._by_sub.items() if wss}

    async def broadcast_to_sub(self, sub: str, message: dict) -> None:
        for ws in list(self._by_sub.get(sub, [])):
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.debug("ws send failed for %s: %s", sub, e)


plinko_manager = PlinkoConnectionManager()
