import bcrypt
import secrets
from datetime import datetime, timezone


def utc_now():
    return datetime.now(timezone.utc)


def generate_email_code():
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_password(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")


def verify_password(password, password_hash):
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except (ValueError, TypeError, UnicodeEncodeError):
        return False


def hash_email_code(code):
    return bcrypt.hashpw(code.encode("ascii"), bcrypt.gensalt(rounds=12)).decode("ascii")


def verify_email_code(code, code_hash):
    try:
        return bcrypt.checkpw(code.encode("ascii"), code_hash.encode("ascii"))
    except (ValueError, TypeError, UnicodeEncodeError):
        return False
