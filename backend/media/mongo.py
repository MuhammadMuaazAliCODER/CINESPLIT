from threading import Lock

from pymongo import ASCENDING

from config.mongo import get_database

_lock = Lock()
_ready = False
_orphan_ready = False


def get_media_collection():
    global _ready
    collection = get_database().media
    if not _ready:
        with _lock:
            if not _ready:
                collection.create_index(
                    [("content_type", ASCENDING), ("content_id", ASCENDING), ("role", ASCENDING)],
                    unique=True,
                    name="media_content_role_unique",
                )
                collection.create_index([("public_id", ASCENDING)], name="media_public_id")
                collection.create_index([("uploaded_at", -1)], name="media_uploaded_at")
                _ready = True
    return collection


def get_orphan_collection():
    global _orphan_ready
    collection = get_database().media_orphans
    if not _orphan_ready:
        with _lock:
            if not _orphan_ready:
                collection.create_index([("public_id", ASCENDING)], unique=True, name="media_orphan_public_id_unique")
                collection.create_index([("queued_at", -1)], name="media_orphan_queued_at")
                _orphan_ready = True
    return collection
