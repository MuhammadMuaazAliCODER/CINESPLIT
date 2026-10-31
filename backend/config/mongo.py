import atexit
import os
from threading import Lock

from pymongo import MongoClient
from pymongo.errors import PyMongoError

_client = None
_client_lock = Lock()


class MongoConfigurationError(RuntimeError):
    """MongoDB settings are missing or invalid."""


class MongoUnavailableError(RuntimeError):
    """MongoDB did not respond to a health check."""


def _get_client():
    global _client
    uri = os.getenv("MONGODB_URI", "").strip()
    if not uri:
        raise MongoConfigurationError("MONGODB_URI is not configured")
    with _client_lock:
        if _client is None:
            _client = MongoClient(uri, serverSelectionTimeoutMS=3000, connectTimeoutMS=3000, socketTimeoutMS=3000, tz_aware=True)
            atexit.register(close_mongo_client)
        return _client


def get_database():
    database_name = os.getenv("MONGODB_DATABASE", "cinesplit").strip()
    if not database_name:
        raise MongoConfigurationError("MONGODB_DATABASE must not be empty")
    return _get_client()[database_name]


def ping_database():
    try:
        get_database().command("ping")
    except MongoConfigurationError:
        raise
    except (PyMongoError, ValueError) as exc:
        raise MongoUnavailableError("MongoDB ping failed") from exc


def close_mongo_client():
    global _client
    with _client_lock:
        if _client is not None:
            _client.close()
            _client = None
