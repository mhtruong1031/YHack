import logging
from typing import Annotated, Any

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwk, jwt

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)

_jwks_cache: dict[str, Any] | None = None


async def fetch_jwks(domain: str) -> dict[str, Any]:
    global _jwks_cache
    url = f"https://{domain.rstrip('/')}/.well-known/jwks.json"
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(url)
        r.raise_for_status()
        _jwks_cache = r.json()
    return _jwks_cache


def _rsa_key_from_jwks(token_header: dict[str, Any], jwks: dict[str, Any]) -> dict[str, Any]:
    kid = token_header.get("kid")
    if not kid:
        raise JWTError("missing kid")
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    raise JWTError("unknown kid")


async def decode_auth0_token(
    token: str,
    settings: Settings,
) -> dict[str, Any]:
    jwks = _jwks_cache or await fetch_jwks(settings.auth0_domain)
    try:
        unverified = jwt.get_unverified_header(token)
        key_dict = _rsa_key_from_jwks(unverified, jwks)
    except JWTError:
        jwks = await fetch_jwks(settings.auth0_domain)
        unverified = jwt.get_unverified_header(token)
        key_dict = _rsa_key_from_jwks(unverified, jwks)

    signing_key = jwk.construct(key_dict)
    issuer = settings.auth0_issuer
    try:
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=settings.auth0_audience,
            issuer=issuer,
            options={"verify_at_hash": False},
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
        ) from e
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing sub",
        )
    return payload


async def fetch_auth0_userinfo(domain: str, access_token: str) -> dict[str, Any] | None:
    """
    Access tokens for a custom API audience often omit name/email/picture.
    Auth0's /userinfo returns those when the token includes openid (and profile/email scopes).
    """
    url = f"https://{domain.rstrip('/')}/userinfo"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if r.status_code != 200:
                logger.debug(
                    "Auth0 userinfo HTTP %s: %s",
                    r.status_code,
                    (r.text or "")[:200],
                )
                return None
            data = r.json()
            return data if isinstance(data, dict) else None
    except Exception as e:
        logger.warning("Auth0 userinfo request failed: %s", e)
        return None


def merge_claims_and_userinfo(
    claims: dict[str, Any],
    userinfo: dict[str, Any] | None,
) -> dict[str, Any]:
    """Prefer userinfo for standard OIDC profile keys when present."""
    if not userinfo:
        return dict(claims)
    out = dict(claims)
    for key in (
        "email",
        "email_verified",
        "name",
        "nickname",
        "picture",
        "given_name",
        "family_name",
    ):
        val = userinfo.get(key)
        if val is not None and val != "":
            out[key] = val
    return out


async def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required",
        )
    return await decode_auth0_token(creds.credentials, settings)


async def decode_auth0_token_ws(token: str, settings: Settings) -> dict[str, Any]:
    return await decode_auth0_token(token, settings)
