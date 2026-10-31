import secrets
import uuid
from datetime import timedelta

import bcrypt
from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError
from django.conf import settings

from .email_service import EmailDeliveryError, send_verification_email
from .mongo import get_auth_database
from .security import generate_email_code, hash_email_code, hash_password, utc_now, verify_email_code, verify_password
from .tokens import TokenError, create_access_token, create_refresh_token, decode_token

_DUMMY_PASSWORD_HASH = bcrypt.hashpw(b"cinesplit-nonexistent-account", bcrypt.gensalt(rounds=12)).decode("ascii")


class AccountConflict(Exception):
    pass


class VerificationFailure(Exception):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


class AuthenticationFailure(Exception):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


class RefreshFailure(Exception):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def _verification_document(user_id, code, now):
    return {
        "user_id": user_id,
        "code_hash": hash_email_code(code),
        "created_at": now,
        "expires_at": now + timedelta(minutes=settings.EMAIL_VERIFICATION_EXPIRY_MINUTES),
        "attempts": 0,
        "verified_at": None,
        "invalidated_at": None,
    }


def register_user(username, email, password):
    db = get_auth_database()
    now = utc_now()
    code = generate_email_code()
    user = {
        "username": username,
        "email": email,
        "password_hash": hash_password(password),
        "role": "user",
        "is_active": True,
        "is_verified": False,
        "created_at": now,
        "updated_at": now,
        "last_login": None,
        "full_name": "",
        "avatar": "",
        "bio": "",
    }

    def create_records(session):
        result = db.users.insert_one(user, session=session)
        db.email_verifications.insert_one(_verification_document(result.inserted_id, code, now), session=session)

    try:
        with db.client.start_session() as session:
            session.with_transaction(create_records)
    except DuplicateKeyError as exc:
        raise AccountConflict("An account already uses that username or email.") from exc
    try:
        send_verification_email(email, code)
    except EmailDeliveryError:
        return user, False
    return user, True


def resend_verification(email):
    db = get_auth_database()
    user = db.users.find_one({"email": email}, {"_id": 1, "is_verified": 1, "is_active": 1})
    if not user or user.get("is_verified") or not user.get("is_active"):
        return "not_eligible"

    now = utc_now()
    code = generate_email_code()
    verification = _verification_document(user["_id"], code, now)
    state = {"eligible": False}

    def rotate_code(session):
        state["eligible"] = False
        latest = db.email_verifications.find_one(
            {"user_id": user["_id"]}, sort=[("created_at", -1)], session=session
        )
        if latest and (now - latest["created_at"]).total_seconds() < settings.EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS:
            return
        db.email_verifications.update_many(
            {"user_id": user["_id"], "invalidated_at": None, "verified_at": None},
            {"$set": {"invalidated_at": now}}, session=session,
        )
        db.email_verifications.insert_one(verification, session=session)
        state["eligible"] = True

    with db.client.start_session() as session:
        session.with_transaction(rotate_code)
    if not state["eligible"]:
        return "not_eligible"
    try:
        send_verification_email(email, code)
    except EmailDeliveryError:
        return "delivery_failed"
    return "sent"


def verify_email(email, code):
    db = get_auth_database()
    now = utc_now()
    user = db.users.find_one({"email": email, "is_active": True}, {"_id": 1, "is_verified": 1})
    if not user or user.get("is_verified"):
        raise VerificationFailure("invalid_code", "The code is invalid or no longer active.")
    for _ in range(3):
        record = db.email_verifications.find_one(
            {"user_id": user["_id"], "invalidated_at": None, "verified_at": None},
            sort=[("created_at", -1)],
        )
        if not record:
            raise VerificationFailure("invalid_code", "The code is invalid or no longer active.")
        if record["expires_at"] <= now:
            raise VerificationFailure("expired_code", "This code has expired. Request a new one.")
        if record["attempts"] >= settings.EMAIL_VERIFICATION_MAX_ATTEMPTS:
            raise VerificationFailure("attempt_limit", "Too many attempts. Request a new code.")
        if not verify_email_code(code, record["code_hash"]):
            updated = db.email_verifications.find_one_and_update(
                {"_id": record["_id"], "attempts": record["attempts"],
                 "invalidated_at": None, "verified_at": None, "expires_at": {"$gt": now},
                 },
                {"$inc": {"attempts": 1}}, return_document=ReturnDocument.AFTER,
            )
            if updated:
                raise VerificationFailure("invalid_code", "The code is incorrect.")
            continue

        consumed = {"done": False}
        def consume(session):
            consumed["done"] = False
            result = db.email_verifications.find_one_and_update(
                {"_id": record["_id"], "attempts": record["attempts"],
                 "invalidated_at": None, "verified_at": None, "expires_at": {"$gt": now},
                 },
                {"$set": {"verified_at": now}}, return_document=ReturnDocument.AFTER, session=session,
            )
            if not result:
                return
            user_result = db.users.update_one(
                {"_id": record["user_id"], "is_verified": False, "is_active": True},
                {"$set": {"is_verified": True, "updated_at": now}}, session=session,
            )
            consumed["done"] = user_result.modified_count == 1

        with db.client.start_session() as session:
            session.with_transaction(consume)
        if consumed["done"]:
            return
    raise VerificationFailure("invalid_code", "The code is invalid or no longer active.")


def login(email, password):
    db = get_auth_database()
    user = db.users.find_one({"email": email})
    stored_hash = user.get("password_hash", _DUMMY_PASSWORD_HASH) if user else _DUMMY_PASSWORD_HASH
    password_matches = verify_password(password, stored_hash)
    if not user or not password_matches:
        raise AuthenticationFailure("invalid_credentials", "Email or password is incorrect.")
    if not user.get("is_active"):
        raise AuthenticationFailure("invalid_credentials", "Email or password is incorrect.")
    if not user.get("is_verified"):
        raise AuthenticationFailure("email_not_verified", "Verify your email before signing in.")

    now = utc_now()
    session_id = str(uuid.uuid4())
    family_id = str(uuid.uuid4())
    refresh_jti = secrets.token_urlsafe(24)
    refresh_expiry = now + timedelta(days=settings.JWT_REFRESH_TOKEN_LIFETIME)
    session_document = {
        "_id": session_id,
        "user_id": user["_id"],
        "current_jti": refresh_jti,
        "used_jtis": [],
        "created_at": now,
        "expires_at": refresh_expiry,
        "revoked_at": None,
        "rotation_count": 0,
        "last_rotated_at": None,
        "family_id": family_id,
    }
    db.refresh_sessions.insert_one(session_document)
    db.users.update_one({"_id": user["_id"]}, {"$set": {"last_login": now, "updated_at": now}})
    user["last_login"] = now
    user["updated_at"] = now
    return create_access_token(user), create_refresh_token(user["_id"], session_id, family_id, refresh_jti), user


def _revoke_family(db, session_id, family_id, now, session):
    db.refresh_sessions.update_one(
        {"_id": session_id, "family_id": family_id, "revoked_at": None},
        {"$set": {"revoked_at": now}}, session=session,
    )


def rotate_refresh_token(token):
    db = get_auth_database()
    try:
        claims = decode_token(token, "refresh")
        user_id = ObjectId(claims["sub"])
        session_id = claims["sid"]
        family_id = claims["fam"]
        token_jti = claims["jti"]
    except (TokenError, ValueError, KeyError, TypeError) as exc:
        raise RefreshFailure("invalid_refresh", "Refresh token is invalid or expired.") from exc

    now = utc_now()
    new_jti = secrets.token_urlsafe(24)
    new_expiry = now + timedelta(days=settings.JWT_REFRESH_TOKEN_LIFETIME)
    outcome = {"status": "invalid", "user": None}

    def rotate(session):
        outcome["status"] = "invalid"
        outcome["user"] = None
        document = db.refresh_sessions.find_one({"_id": session_id, "family_id": family_id, "user_id": user_id}, session=session)
        if not document or document.get("revoked_at") or document["expires_at"] <= now:
            return
        if token_jti in document.get("used_jtis", []):
            _revoke_family(db, session_id, family_id, now, session)
            outcome["status"] = "replay"
            return
        if token_jti != document.get("current_jti"):
            return
        user = db.users.find_one({"_id": user_id, "is_active": True, "is_verified": True}, session=session)
        if not user:
            _revoke_family(db, session_id, family_id, now, session)
            return
        changed = db.refresh_sessions.update_one(
            {"_id": session_id, "current_jti": token_jti, "revoked_at": None, "expires_at": {"$gt": now}},
            {"$set": {"current_jti": new_jti, "expires_at": new_expiry, "last_rotated_at": now},
             "$inc": {"rotation_count": 1}, "$addToSet": {"used_jtis": token_jti}}, session=session,
        )
        if changed.modified_count == 1:
            outcome["status"] = "rotated"
            outcome["user"] = user

    with db.client.start_session() as session:
        session.with_transaction(rotate)
    if outcome["status"] == "replay":
        raise RefreshFailure("refresh_replay", "This refresh token has already been used. The session was revoked.")
    if outcome["status"] != "rotated":
        raise RefreshFailure("invalid_refresh", "Refresh token is invalid, expired, or revoked.")
    access = create_access_token(outcome["user"])
    refresh = create_refresh_token(user_id, session_id, family_id, new_jti)
    return access, refresh


def revoke_refresh_token(token):
    db = get_auth_database()
    try:
        claims = decode_token(token, "refresh")
        user_id = ObjectId(claims["sub"])
    except (TokenError, ValueError, KeyError, TypeError):
        return False
    now = utc_now()
    result = db.refresh_sessions.update_one(
        {"_id": claims.get("sid"), "user_id": user_id, "family_id": claims.get("fam"),
         "current_jti": claims["jti"], "revoked_at": None},
        {"$set": {"revoked_at": now}},
    )
    return result.modified_count == 1


def update_profile(user_id, changes):
    db = get_auth_database()
    try:
        object_id = ObjectId(user_id)
    except (ValueError, TypeError):
        return None
    if "username" in changes:
        duplicate = db.users.find_one({"username": changes["username"], "_id": {"$ne": object_id}}, {"_id": 1})
        if duplicate:
            raise AccountConflict("That username is already taken.")
    changes["updated_at"] = utc_now()
    try:
        db.users.update_one({"_id": object_id}, {"$set": changes})
    except DuplicateKeyError as exc:
        raise AccountConflict("That username is already taken.") from exc
    return db.users.find_one({"_id": object_id})


def change_password(user_id, current_password, new_password):
    db = get_auth_database()
    object_id = ObjectId(user_id)
    user = db.users.find_one({"_id": object_id})
    if not user or not verify_password(current_password, user.get("password_hash", "")):
        raise AuthenticationFailure("incorrect_password", "Current password is incorrect.")
    now = utc_now()
    password_hash = hash_password(new_password)
    with db.client.start_session() as session:
        def update_all(transaction):
            updated = db.users.update_one(
                {"_id": object_id, "password_hash": user["password_hash"]},
                {"$set": {"password_hash": password_hash, "updated_at": now}}, session=transaction,
            )
            if updated.modified_count != 1:
                raise AuthenticationFailure("incorrect_password", "Current password is incorrect.")
            db.refresh_sessions.update_many(
                {"user_id": object_id, "revoked_at": None},
                {"$set": {"revoked_at": now}}, session=transaction,
            )
        session.with_transaction(update_all)
