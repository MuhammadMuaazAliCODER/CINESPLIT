import re
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from django.utils.text import slugify
from pymongo import DESCENDING
from pymongo.errors import DuplicateKeyError

from config.mongo import get_database
from .mongo import get_chapter_collection, get_movie_collection


class MovieConflict(Exception):
    """A movie slug or record conflicts with an existing movie."""


class MovieNotFound(Exception):
    """The requested movie does not exist."""


class MovieHasChapters(MovieConflict):
    """Movies with chapters cannot be deleted while chapter records remain."""


class InvalidMovieId(Exception):
    """A supplied movie id is not a valid MongoDB ObjectId."""


def parse_movie_id(value):
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        raise InvalidMovieId from None


def _available_slug(collection, base, exclude_id=None):
    base = slugify(base)[:190].strip("-") or "movie"
    candidate = base
    suffix = 2
    while True:
        query = {"slug": candidate}
        if exclude_id is not None:
            query["_id"] = {"$ne": exclude_id}
        if not collection.find_one(query, {"_id": 1}):
            return candidate
        tail = f"-{suffix}"
        candidate = f"{base[:200 - len(tail)]}{tail}"
        suffix += 1


def _document_data(document):
    if not document:
        return None
    result = dict(document)
    movie_id = result.pop("_id", None)
    result["id"] = str(movie_id or result.get("id", ""))
    if "created_by" in result:
        result["created_by"] = str(result["created_by"])
    return result


def create_movie(values, administrator_id):
    collection = get_movie_collection()
    now = datetime.now(timezone.utc)
    movie = dict(values)
    requested_slug = movie.pop("slug", "")
    movie["slug"] = _available_slug(collection, requested_slug or movie["title"])
    movie.update({
        "created_at": now,
        "updated_at": now,
        "created_by": administrator_id,
    })
    try:
        result = collection.insert_one(movie)
    except DuplicateKeyError as exc:
        raise MovieConflict("That movie slug is already in use.") from exc
    movie["_id"] = result.inserted_id
    return _document_data(movie)


def get_movie_by_slug(slug, published_only=True):
    query = {"slug": slug}
    if published_only:
        query["status"] = "published"
    return _document_data(get_movie_collection().find_one(query))


def get_movie_by_id(movie_id):
    object_id = parse_movie_id(movie_id)
    return _document_data(get_movie_collection().find_one({"_id": object_id}))


def update_movie(movie_id, changes):
    object_id = parse_movie_id(movie_id)
    collection = get_movie_collection()
    existing = collection.find_one({"_id": object_id})
    if not existing:
        raise MovieNotFound
    updates = dict(changes)
    requested_slug = updates.get("slug")
    if requested_slug == "":
        updates["slug"] = _available_slug(collection, updates.get("title", existing["title"]), object_id)
    elif requested_slug:
        updates["slug"] = slugify(requested_slug)[:200]
        duplicate = collection.find_one({"slug": updates["slug"], "_id": {"$ne": object_id}}, {"_id": 1})
        if duplicate:
            raise MovieConflict("That movie slug is already in use.")
    if not updates:
        return _document_data(existing)
    updates["updated_at"] = datetime.now(timezone.utc)
    try:
        updated = collection.find_one_and_update({"_id": object_id}, {"$set": updates}, return_document=True)
    except DuplicateKeyError as exc:
        raise MovieConflict("That movie slug is already in use.") from exc
    if not updated:
        raise MovieNotFound
    return _document_data(updated)


def delete_movie(movie_id, confirmation):
    object_id = parse_movie_id(movie_id)
    collection = get_movie_collection()
    chapters = get_chapter_collection()
    client = get_database().client
    with client.start_session() as session:
        def operation(active_session):
            movie = collection.find_one({"_id": object_id}, {"slug": 1}, session=active_session)
            if not movie:
                raise MovieNotFound
            if confirmation != movie["slug"]:
                return False
            # This parent write coordinates with chapter mutations, which use the same lock.
            locked = collection.update_one({"_id": object_id}, {"$inc": {"chapter_order_revision": 1}}, session=active_session)
            if locked.matched_count != 1:
                raise MovieNotFound
            if chapters.count_documents({"movie_id": object_id}, session=active_session):
                raise MovieHasChapters
            result = collection.delete_one({"_id": object_id, "slug": movie["slug"]}, session=active_session)
            return result.deleted_count == 1
        deleted = session.with_transaction(operation)
    if deleted:
        from media.services import remove_content_media
        remove_content_media("movie", object_id)
    return deleted


def _movie_query(filters, published_only=False, featured_only=False):
    query = {}
    if published_only:
        query["status"] = "published"
    elif filters.get("status"):
        query["status"] = filters["status"]
    if featured_only:
        query["is_featured"] = True
    if filters.get("genre"):
        query["genres"] = filters["genre"].strip().casefold()
    if filters.get("release_year"):
        query["release_year"] = filters["release_year"]
    if filters.get("language"):
        query["original_language"] = filters["language"].strip().casefold()
    if filters.get("content_rating"):
        query["content_rating"] = filters["content_rating"]
    if filters.get("search"):
        query["$text"] = {"$search": filters["search"].strip()}
    return query


def list_movies(filters, *, published_only=False, featured_only=False):
    collection = get_movie_collection()
    query = _movie_query(filters, published_only=published_only, featured_only=featured_only)
    page = filters.get("page", 1)
    page_size = filters.get("page_size", 20)
    sort = filters.get("sort", "-release_year")
    sort_fields = {
        "-release_year": [("release_year", DESCENDING), ("title", 1)],
        "release_year": [("release_year", 1), ("title", 1)],
        "title": [("title", 1)],
        "-title": [("title", DESCENDING)],
        "-created_at": [("created_at", DESCENDING)],
        "created_at": [("created_at", 1)],
    }
    total = collection.count_documents(query)
    documents = collection.find(query).sort(sort_fields[sort]).skip((page - 1) * page_size).limit(page_size)
    return {
        "results": [_document_data(item) for item in documents],
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": (total + page_size - 1) // page_size,
    }


def list_public_genres():
    genres = get_movie_collection().distinct("genres", {"status": "published"})
    return sorted((genre for genre in genres if isinstance(genre, str)), key=str.casefold)
