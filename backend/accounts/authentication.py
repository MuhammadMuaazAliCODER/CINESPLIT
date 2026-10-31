from dataclasses import dataclass

from bson import ObjectId
from bson.errors import InvalidId
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from .mongo import get_auth_database
from .tokens import TokenError, decode_token


@dataclass(frozen=True)
class AuthenticatedUser:
    id: str
    username: str
    email: str
    role: str
    is_active: bool
    is_verified: bool
    full_name: str = ""
    avatar: str = ""
    bio: str = ""

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False


class MongoJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        header = get_authorization_header(request).split()
        if not header:
            return None
        if len(header) != 2 or header[0].lower() != b"bearer":
            raise AuthenticationFailed("Use a Bearer access token.")
        try:
            token = header[1].decode("ascii")
            claims = decode_token(token, "access")
            user_id = ObjectId(claims["sub"])
        except (UnicodeDecodeError, InvalidId, KeyError, TokenError) as exc:
            raise AuthenticationFailed("Access token is invalid or expired.") from exc

        user = get_auth_database().users.find_one({"_id": user_id})
        if not user or not user.get("is_active"):
            raise AuthenticationFailed("User account is unavailable.")
        if not user.get("is_verified"):
            raise AuthenticationFailed("Email verification is required.")
        principal = AuthenticatedUser(
            id=str(user["_id"]), username=user["username"], email=user["email"],
            role=user["role"], is_active=user["is_active"], is_verified=user["is_verified"],
            full_name=user.get("full_name", ""), avatar=user.get("avatar", ""), bio=user.get("bio", ""),
        )
        return principal, claims

    def authenticate_header(self, request):
        return "Bearer"
