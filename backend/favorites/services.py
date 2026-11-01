from datetime import datetime, timezone
from threading import Lock

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError

from config.mongo import get_database
from core.content import CONTENT_TYPES, ContentIdError, parse_content_id, public_content

_ready = False
_lock = Lock()


def get_collection():
    global _ready
    collection = get_database().favorites
    if not _ready:
        with _lock:
            if not _ready:
                collection.create_index([("user_id", ASCENDING), ("content_type", ASCENDING), ("content_id", ASCENDING)], unique=True, name="favorites_user_content_unique")
                collection.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)], name="favorites_user_created")
                _ready = True
    return collection


class FavoriteConflict(Exception):
    pass


def set_favorite(user_id, content_type, content_id, favorite=True):
    if content_type not in CONTENT_TYPES:
        raise ContentIdError("Content type is not supported.")
    if not favorite:
        oid = parse_content_id(content_id)
        get_collection().delete_one({"user_id": user_id, "content_type": content_type, "content_id": str(oid)})
        return False
    content = public_content(content_type, content_id)
    if not content:
        return None
    collection = get_collection()
    query = {"user_id": user_id, "content_type": content_type, "content_id": content["content_id"]}
    try:
        collection.update_one(query, {"$setOnInsert": {**query, "created_at": datetime.now(timezone.utc)}}, upsert=True)
    except DuplicateKeyError:
        pass
    return True


def is_favorite(user_id, content_type, content_id):
    if content_type not in CONTENT_TYPES:
        raise ContentIdError("Content type is not supported.")
    oid = parse_content_id(content_id)
    return bool(get_collection().find_one({"user_id": user_id, "content_type": content_type, "content_id": str(oid)}))


def list_favorites(user_id, page=1, page_size=20):
    collection = get_collection()
    query = {"user_id": user_id}
    total = collection.count_documents(query)
    records = collection.find(query).sort("created_at", DESCENDING).skip((page - 1) * page_size).limit(page_size)
    results = []
    for record in records:
        content = public_content(record["content_type"], record["content_id"])
        if content:
            content["favorited_at"] = record["created_at"]
            results.append(content)
    return {"results": results, "page": page, "page_size": page_size, "total": total, "pages": (total + page_size - 1) // page_size}
