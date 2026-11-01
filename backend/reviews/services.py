from datetime import datetime, timezone
from threading import Lock

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError

from config.mongo import get_database
from core.content import public_content

_ready = False
_lock = Lock()


def get_collection():
    global _ready
    collection = get_database().reviews
    if not _ready:
        with _lock:
            if not _ready:
                collection.create_index([("content_type", ASCENDING), ("content_id", ASCENDING), ("user_id", ASCENDING)], unique=True, name="reviews_content_user_unique")
                collection.create_index([("content_type", ASCENDING), ("content_id", ASCENDING), ("created_at", DESCENDING)], name="reviews_content_recent")
                collection.create_index([("user_id", ASCENDING), ("updated_at", DESCENDING)], name="reviews_user_updated")
                _ready = True
    return collection


class ReviewError(Exception):
    pass


def review_summary(content_type, content_id, page=1, page_size=20, user_id=None):
    content = public_content(content_type, content_id)
    if not content:
        return None
    collection = get_collection()
    query = {"content_type": content_type, "content_id": content["content_id"]}
    aggregate = list(collection.aggregate([{"$match": query}, {"$group": {"_id": None, "average": {"$avg": "$rating"}, "count": {"$sum": 1}}}]))
    summary = aggregate[0] if aggregate else {"average": None, "count": 0}
    docs = list(collection.find(query, {"content_type": 0, "content_id": 0}).sort("created_at", DESCENDING).skip((page - 1) * page_size).limit(page_size))
    for doc in docs:
        doc["id"] = str(doc.pop("_id")); doc["user_id"] = str(doc["user_id"])
    mine = collection.find_one({**query, "user_id": user_id}) if user_id else None
    if mine:
        mine["id"] = str(mine.pop("_id")); mine["user_id"] = str(mine["user_id"])
    count = summary.get("count", 0)
    return {"results": docs, "average_rating": round(summary["average"], 2) if summary.get("average") is not None else None,
            "rating_count": count, "current_review": mine, "page": page, "page_size": page_size, "pages": (count + page_size - 1) // page_size}


def create_review(user_id, username, content_type, content_id, rating, body):
    content = public_content(content_type, content_id)
    if not content:
        return None
    now = datetime.now(timezone.utc)
    record = {"user_id": user_id, "username": username, "content_type": content_type, "content_id": content["content_id"],
              "rating": rating, "body": body, "created_at": now, "updated_at": now}
    try:
        result = get_collection().insert_one(record)
    except DuplicateKeyError:
        raise ReviewError("You have already reviewed this content; edit your existing review.") from None
    record["id"] = str(result.inserted_id); record["user_id"] = str(user_id)
    return record


def update_review(user_id, content_type, content_id, review_id, changes):
    from bson import ObjectId
    from bson.errors import InvalidId
    try:
        oid = ObjectId(review_id)
    except (InvalidId, TypeError):
        raise ReviewError("Review id is invalid.") from None
    content = public_content(content_type, content_id)
    if not content:
        return None
    collection = get_collection()
    old = collection.find_one({"_id": oid, "user_id": user_id, "content_type": content_type, "content_id": content["content_id"]})
    if not old:
        raise ReviewError("Review was not found.")
    changes = dict(changes); changes["updated_at"] = datetime.now(timezone.utc)
    if collection.update_one({"_id": oid, "user_id": user_id}, {"$set": changes}).matched_count != 1:
        raise ReviewError("Review was not found.")
    result = collection.find_one({"_id": oid, "user_id": user_id})
    result["id"] = str(result.pop("_id")); result["user_id"] = str(result["user_id"])
    return result


def delete_review(user_id, content_type, content_id, review_id):
    from bson import ObjectId
    from bson.errors import InvalidId
    try:
        oid = ObjectId(review_id)
    except (InvalidId, TypeError):
        raise ReviewError("Review id is invalid.") from None
    from core.content import CONTENT_TYPES, parse_content_id
    if content_type not in CONTENT_TYPES:
        raise ReviewError("Content type is not supported.")
    normalized_id = str(parse_content_id(content_id))
    return get_collection().delete_one({"_id": oid, "user_id": user_id, "content_type": content_type, "content_id": normalized_id}).deleted_count == 1
