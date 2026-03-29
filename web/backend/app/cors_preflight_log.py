"""Log browser CORS preflight details (helps fix HTTP 400 on OPTIONS)."""

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger(__name__)


class CorsPreflightLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            logger.info(
                "CORS preflight: path=%s origin=%r access-control-request-method=%r "
                "access-control-request-headers=%r",
                request.url.path,
                request.headers.get("origin"),
                request.headers.get("access-control-request-method"),
                request.headers.get("access-control-request-headers"),
            )
        return await call_next(request)
