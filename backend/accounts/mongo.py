from threading import Lock

from pymongo import ASCENDING, DESCENDING

from config.mongo import get_database

_indexes_ready = False
_indexes_lock = Lock()


def get_auth_database():
    global _indexes_ready
    db = get_database()
    if not _indexes_ready:
        with _indexes_lock:
            if not _indexes_ready:
                ensure_indexes(db)
                _indexes_ready = True
    return db


def ensure_indexes(db):
    db.users.create_index([("email", ASCENDING)], unique=True, name="users_email_unique")
    db.users.create_index([("username", ASCENDING)], unique=True, name="users_username_unique")
    db.email_verifications.create_index(
        [("user_id", ASCENDING)], unique=True,
        partialFilterExpression={"invalidated_at": None, "verified_at": None},
        name="email_verifications_active_user_unique",
    )
    db.email_verifications.create_index([("expires_at", ASCENDING)], expireAfterSeconds=0, name="email_verifications_ttl")
    db.email_verifications.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)], name="email_verifications_user_created")
    db.refresh_sessions.create_index([("current_jti", ASCENDING)], unique=True, name="refresh_sessions_current_jti_unique")
    db.refresh_sessions.create_index([("user_id", ASCENDING), ("revoked_at", ASCENDING)], name="refresh_sessions_user_active")
    db.refresh_sessions.create_index([("family_id", ASCENDING)], name="refresh_sessions_family")
    db.refresh_sessions.create_index([("expires_at", ASCENDING)], expireAfterSeconds=0, name="refresh_sessions_ttl")
    db.auth_rate_limits.create_index([("expires_at", ASCENDING)], expireAfterSeconds=0, name="auth_rate_limits_ttl")


def safe_user(user):
    if not user:
        return None
    return {
        "id": str(user["_id"]),
        "username": user["username"],
        "email": user["email"],
        "role": user["role"],
        "is_active": user["is_active"],
        "is_verified": user["is_verified"],
        "full_name": user.get("full_name", ""),
        "avatar": user.get("avatar", ""),
        "bio": user.get("bio", ""),
        "created_at": user["created_at"].isoformat(),
        "updated_at": user["updated_at"].isoformat(),
        "last_login": user["last_login"].isoformat() if user.get("last_login") else None,
    }


