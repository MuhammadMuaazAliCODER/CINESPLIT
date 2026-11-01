from threading import Lock

from pymongo import ASCENDING, DESCENDING

from config.mongo import get_database

_indexes_ready = False
_indexes_lock = Lock()
_chapter_indexes_ready = False


def get_movie_collection():
    global _indexes_ready
    collection = get_database().movies
    if not _indexes_ready:
        with _indexes_lock:
            if not _indexes_ready:
                ensure_indexes(collection)
                _indexes_ready = True
    return collection


def ensure_indexes(collection):
    collection.create_index([("slug", ASCENDING)], unique=True, name="movies_slug_unique")
    collection.create_index([("title", "text")], name="movies_title_text")
    collection.create_index([("genres", ASCENDING)], name="movies_genres")
    collection.create_index([("release_year", DESCENDING)], name="movies_release_year")
    collection.create_index([("original_language", ASCENDING)], name="movies_language")
    collection.create_index([("content_rating", ASCENDING)], name="movies_content_rating")
    collection.create_index([("status", ASCENDING)], name="movies_status")
    collection.create_index([("is_featured", ASCENDING)], name="movies_featured")
    collection.create_index([("created_at", DESCENDING)], name="movies_created_at")


def get_chapter_collection():
    global _chapter_indexes_ready
    collection = get_database().movie_chapters
    if not _chapter_indexes_ready:
        with _indexes_lock:
            if not _chapter_indexes_ready:
                ensure_chapter_indexes(collection)
                _chapter_indexes_ready = True
    return collection


def ensure_chapter_indexes(collection):
    collection.create_index(
        [("movie_id", ASCENDING), ("chapter_number", ASCENDING)],
        unique=True, name="movie_chapters_movie_number_unique",
    )
    collection.create_index(
        [("movie_id", ASCENDING), ("slug", ASCENDING)],
        unique=True, name="movie_chapters_movie_slug_unique",
    )
    collection.create_index(
        [("movie_id", ASCENDING), ("status", ASCENDING), ("chapter_number", ASCENDING)],
        name="movie_chapters_movie_status_order",
    )
