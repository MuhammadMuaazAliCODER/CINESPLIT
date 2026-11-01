from datetime import datetime, timezone
from threading import Lock

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ASCENDING, DESCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError

from config.mongo import get_database
from core.content import ContentIdError, public_content

_ready = False
_lock = Lock()


def get_collection():
    global _ready
    collection = get_database().watch_history
    if not _ready:
        with _lock:
            if not _ready:
                collection.create_index([("user_id", ASCENDING), ("content_type", ASCENDING), ("content_id", ASCENDING)], unique=True, name="watch_user_content_unique")
                collection.create_index([("user_id", ASCENDING), ("last_watched_at", DESCENDING)], name="watch_user_recent")
                _ready = True
    return collection


class WatchError(Exception):
    pass


def save_progress(user_id, content_type, content_id, position, duration=None, completed=False, watched_at=None):
    content = public_content(content_type, content_id)
    if not content:
        return None
    oid = ObjectId(content["content_id"])
    now = datetime.now(timezone.utc)
    event_at = watched_at or now
    if event_at.tzinfo is None:
        event_at = event_at.replace(tzinfo=timezone.utc)
    values = {"user_id": user_id, "content_type": content_type, "content_id": oid,
              "position": float(position), "duration": float(duration) if duration is not None else None,
              "completed": bool(completed), "last_watched_at": event_at, "updated_at": now}
    collection = get_collection()
    query = {"user_id": user_id, "content_type": content_type, "content_id": oid,
             "$or": [{"last_watched_at": {"$lte": event_at}}, {"last_watched_at": {"$exists": False}}]}
    try:
        result = collection.find_one_and_update(query, {"$set": values, "$setOnInsert": {"created_at": now}},
                                                upsert=True, return_document=ReturnDocument.AFTER)
    except DuplicateKeyError:
        result = collection.find_one({"user_id": user_id, "content_type": content_type, "content_id": oid})
    result["content"] = content
    result["id"] = str(result.pop("_id"))
    result["content_id"] = str(result["content_id"])
    result["last_watched_at"] = result["last_watched_at"].isoformat()
    return result


def list_history(user_id, page=1, page_size=20, continue_watching=False):
    collection = get_collection()
    query = {"user_id": user_id}
    if continue_watching:
        query["completed"] = {"$ne": True}
    total = collection.count_documents(query)
    docs = collection.find(query).sort("last_watched_at", DESCENDING).skip((page - 1) * page_size).limit(page_size)
    results = []
    for doc in docs:
        content = public_content(doc["content_type"], doc["content_id"])
        if content:
            doc["content"] = content
            doc["id"] = str(doc.pop("_id"))
            doc["content_id"] = str(doc["content_id"])
            doc["last_watched_at"] = doc["last_watched_at"].isoformat()
            results.append(doc)
    return {"results": results, "page": page, "page_size": page_size, "total": total, "pages": (total + page_size - 1) // page_size}


def get_progress(user_id, content_type, content_id):
    content = public_content(content_type, content_id)
    if not content:
        return None
    oid = ObjectId(content["content_id"])
    record = get_collection().find_one({"user_id": user_id, "content_type": content_type, "content_id": oid})
    if not record:
        return {"content": content, "content_type": content_type, "content_id": str(oid), "position": 0,
                "duration": None, "completed": False, "last_watched_at": None}
    record["content"] = content
    record["id"] = str(record.pop("_id"))
    record["content_id"] = str(record["content_id"])
    record["last_watched_at"] = record["last_watched_at"].isoformat()
    return record


def remove_history(user_id, content_type, content_id):
    if content_type not in {"movie", "series", "episode", "chapter"}:
        raise WatchError("Content type is not supported.")
    try:
        oid = ObjectId(content_id)
    except (InvalidId, TypeError):
        raise WatchError("Content id is invalid.") from None
    get_collection().delete_one({"user_id": user_id, "content_type": content_type, "content_id": oid})
