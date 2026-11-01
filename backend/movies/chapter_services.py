from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from django.utils.text import slugify
from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError

from config.mongo import get_database
from .mongo import get_chapter_collection, get_movie_collection
from .services import InvalidMovieId, MovieNotFound, parse_movie_id


class ChapterNotFound(Exception):
    pass


class ChapterConflict(Exception):
    pass


class InvalidChapterId(Exception):
    pass


def parse_chapter_id(value):
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        raise InvalidChapterId from None


def _data(document):
    if not document:
        return None
    result = dict(document)
    result["id"] = str(result.pop("_id"))
    result["movie_id"] = str(result["movie_id"])
    if result.get("created_by") is not None:
        result["created_by"] = str(result["created_by"])
    return result


def _transaction(movie_oid, callback):
    movies = get_movie_collection()
    chapters = get_chapter_collection()
    if not movies.find_one({"_id": movie_oid}, {"_id": 1}):
        raise MovieNotFound
    client = get_database().client
    with client.start_session() as session:
        def operation(active_session):
            # Writing the parent serializes chapter mutations for this movie.
            locked = movies.update_one(
                {"_id": movie_oid}, {"$inc": {"chapter_order_revision": 1}}, session=active_session
            )
            if locked.matched_count != 1:
                raise MovieNotFound
            return callback(chapters, active_session)
        return session.with_transaction(operation)


def _slug_for(chapters, movie_oid, title, requested="", exclude_id=None, session=None):
    base = slugify(requested or title)[:180].strip("-") or "chapter"
    candidate, suffix = base, 2
    while True:
        query = {"movie_id": movie_oid, "slug": candidate}
        if exclude_id:
            query["_id"] = {"$ne": exclude_id}
        if not chapters.find_one(query, {"_id": 1}, session=session):
            return candidate
        if requested:
            raise ChapterConflict("A chapter with that slug already exists for this movie.")
        tail = f"-{suffix}"
        candidate = f"{base[:190-len(tail)]}{tail}"
        suffix += 1


def list_chapters(movie_id, *, published_only=False):
    movie_oid = parse_movie_id(movie_id)
    query = {"movie_id": movie_oid}
    if published_only:
        query["status"] = "published"
    docs = get_chapter_collection().find(query).sort("chapter_number", ASCENDING)
    return [_data(doc) for doc in docs]


def list_public_chapters(movie_slug):
    movie = get_movie_collection().find_one({"slug": movie_slug, "status": "published"}, {"_id": 1})
    if not movie:
        return []
    docs = get_chapter_collection().find({"movie_id": movie["_id"], "status": "published"}).sort("chapter_number", ASCENDING)
    return [_data(doc) for doc in docs]


def get_chapter(movie_id, chapter_id, *, published_only=False):
    movie_oid = parse_movie_id(movie_id)
    chapter_oid = parse_chapter_id(chapter_id)
    query = {"_id": chapter_oid, "movie_id": movie_oid}
    if published_only:
        query["status"] = "published"
    return _data(get_chapter_collection().find_one(query))


def get_public_chapter(movie_slug, chapter_slug):
    movie = get_movie_collection().find_one({"slug": movie_slug, "status": "published"}, {"_id": 1})
    if not movie:
        return None
    return _data(get_chapter_collection().find_one({
        "movie_id": movie["_id"], "slug": chapter_slug, "status": "published"
    }))


def create_chapter(movie_id, values, administrator_id):
    movie_oid = parse_movie_id(movie_id)
    now = datetime.now(timezone.utc)
    def operation(chapters, session):
        existing = list(chapters.find({"movie_id": movie_oid}, {"chapter_number": 1}, session=session).sort("chapter_number", ASCENDING))
        expected = len(existing) + 1
        requested_number = values.get("chapter_number")
        if requested_number is not None and requested_number != expected:
            raise ChapterConflict(f"New chapters are appended at chapter {expected}; use reorder to change numbering.")
        slug = _slug_for(chapters, movie_oid, values["title"], values.get("slug", ""), session=session)
        document = {**values, "movie_id": movie_oid, "chapter_number": expected, "slug": slug,
                    "created_at": now, "updated_at": now, "created_by": administrator_id}
        result = chapters.insert_one(document, session=session)
        document["_id"] = result.inserted_id
        return _data(document)
    try:
        return _transaction(movie_oid, operation)
    except DuplicateKeyError as exc:
        raise ChapterConflict("Chapter number or slug already exists for this movie.") from exc


def update_chapter(movie_id, chapter_id, values):
    movie_oid, chapter_oid = parse_movie_id(movie_id), parse_chapter_id(chapter_id)
    now = datetime.now(timezone.utc)
    def operation(chapters, session):
        existing = chapters.find_one({"_id": chapter_oid, "movie_id": movie_oid}, session=session)
        if not existing:
            raise ChapterNotFound
        changes = dict(values)
        changes.pop("chapter_number", None)  # Number changes are only allowed via complete reorder.
        if "slug" in changes or "title" in changes:
            changes["slug"] = _slug_for(chapters, movie_oid, changes.get("title", existing["title"]),
                                         changes.get("slug", ""), chapter_oid, session)
        changes["updated_at"] = now
        chapters.update_one({"_id": chapter_oid, "movie_id": movie_oid}, {"$set": changes}, session=session)
        return _data(chapters.find_one({"_id": chapter_oid, "movie_id": movie_oid}, session=session))
    try:
        return _transaction(movie_oid, operation)
    except DuplicateKeyError as exc:
        raise ChapterConflict("Chapter number or slug already exists for this movie.") from exc


def delete_chapter(movie_id, chapter_id):
    movie_oid, chapter_oid = parse_movie_id(movie_id), parse_chapter_id(chapter_id)
    def operation(chapters, session):
        existing = chapters.find_one({"_id": chapter_oid, "movie_id": movie_oid}, session=session)
        if not existing:
            raise ChapterNotFound
        chapters.delete_one({"_id": chapter_oid, "movie_id": movie_oid}, session=session)
        remaining = list(chapters.find({"movie_id": movie_oid}, {"_id": 1, "chapter_number": 1}, session=session).sort("chapter_number", ASCENDING))
        # Deletion explicitly compacts the sequence; the API response states this behavior.
        _assign_order(chapters, remaining, session)
        return {"deleted": True, "renumbered": True}
    result = _transaction(movie_oid, operation)
    from media.services import remove_content_media
    remove_content_media("chapter", chapter_oid)
    return result


def reorder_chapters(movie_id, chapter_ids):
    movie_oid = parse_movie_id(movie_id)
    try:
        requested = [parse_chapter_id(chapter_id) for chapter_id in chapter_ids]
    except InvalidChapterId:
        raise
    if len(set(requested)) != len(requested):
        raise ChapterConflict("Chapter IDs must not be repeated.")
    def operation(chapters, session):
        existing = list(chapters.find({"movie_id": movie_oid}, {"_id": 1, "chapter_number": 1}, session=session).sort("chapter_number", ASCENDING))
        if {doc["_id"] for doc in existing} != set(requested):
            raise ChapterConflict("Reorder must include every chapter belonging to this movie exactly once.")
        by_id = {doc["_id"]: doc for doc in existing}
        ordered = [by_id[item] for item in requested]
        _assign_order(chapters, ordered, session)
        return [_data(chapters.find_one({"_id": item, "movie_id": movie_oid}, session=session)) for item in requested]
    try:
        return _transaction(movie_oid, operation)
    except DuplicateKeyError as exc:
        raise ChapterConflict("Chapter order conflicted with another update; reload and try again.") from exc


def _assign_order(chapters, ordered, session):
    if not ordered:
        return
    highest = max(item["chapter_number"] for item in ordered)
    offset = highest + len(ordered) + 1
    chapters.update_many({"_id": {"$in": [item["_id"] for item in ordered]}},
                         {"$inc": {"chapter_number": offset}}, session=session)
    now = datetime.now(timezone.utc)
    for position, item in enumerate(ordered, 1):
        chapters.update_one({"_id": item["_id"]}, {"$set": {"chapter_number": position, "updated_at": now}}, session=session)
