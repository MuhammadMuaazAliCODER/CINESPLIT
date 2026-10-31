import secrets
from datetime import timedelta

import jwt
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .security import utc_now


class TokenError(Exception):
    pass


def _secret():
    if not settings.JWT_SECRET_KEY or settings.JWT_SECRET_KEY == settings.SECRET_KEY:
        raise ImproperlyConfigured("Configure a dedicated JWT_SECRET_KEY distinct from DJANGO_SECRET_KEY.")
    if settings.JWT_ALGORITHM not in {"HS256", "HS384", "HS512"}:
        raise ImproperlyConfigured("JWT_ALGORITHM must be a supported HMAC algorithm.")
    return settings.JWT_SECRET_KEY


def _encode(claims):
    if settings.JWT_ISSUER:
        claims["iss"] = settings.JWT_ISSUER
    if settings.JWT_AUDIENCE:
        claims["aud"] = settings.JWT_AUDIENCE
    return jwt.encode(claims, _secret(), algorithm=settings.JWT_ALGORITHM)


def create_access_token(user):
    now = utc_now()
    claims = {
        "sub": str(user["_id"]),
        "jti": secrets.token_urlsafe(24),
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_LIFETIME),
        "type": "access",
    }
    return _encode(claims)


def create_refresh_token(user_id, session_id, family_id, jti):
    now = utc_now()
    claims = {
        "sub": str(user_id),
        "sid": session_id,
        "fam": family_id,
        "jti": jti,
        "iat": now,
        "exp": now + timedelta(days=settings.JWT_REFRESH_TOKEN_LIFETIME),
        "type": "refresh",
    }
    return _encode(claims)


def decode_token(token, expected_type):
    try:
        options = {"require": ["sub", "jti", "iat", "exp", "type"]}
        kwargs = {"algorithms": [settings.JWT_ALGORITHM], "options": options}
        if settings.JWT_ISSUER:
            kwargs["issuer"] = settings.JWT_ISSUER
        if settings.JWT_AUDIENCE:
            kwargs["audience"] = settings.JWT_AUDIENCE
        claims = jwt.decode(token, _secret(), **kwargs)
        if claims.get("type") != expected_type:
            raise TokenError("Incorrect token type.")
        return claims
    except (jwt.PyJWTError, ImproperlyConfigured, TypeError, ValueError) as exc:
        if isinstance(exc, ImproperlyConfigured):
            raise
        raise TokenError("Token is invalid or expired.") from exc
