from bson import ObjectId
from bson.errors import InvalidId

from config.mongo import get_database


CONTENT_TYPES = {"movie", "series", "episode", "chapter"}


class ContentIdError(ValueError):
    pass


def parse_content_id(value):
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        raise ContentIdError("Content id is invalid.") from None


def public_content(content_type, content_id):
    if content_type not in CONTENT_TYPES:
        raise ContentIdError("Content type is not supported.")
    oid = parse_content_id(content_id)
    db = get_database()
    if content_type == "movie":
        item = db.movies.find_one({"_id": oid, "status": "published"})
        if not item:
            return None
        return {"content_type": "movie", "content_id": str(oid), "title": item["title"], "slug": item["slug"],
                "url": f"/movies/{item['slug']}", "poster_url": item.get("poster_url", ""),
                "release_year": item.get("release_year"), "status": item["status"]}
    if content_type == "series":
        item = db.series.find_one({"_id": oid, "status": "published"})
        if not item:
            return None
        return {"content_type": "series", "content_id": str(oid), "title": item["title"], "slug": item["slug"],
                "url": f"/series/{item['slug']}", "poster_url": item.get("poster_url", ""),
                "release_year": item.get("release_year"), "status": item["status"]}
    if content_type == "chapter":
        item = db.movie_chapters.find_one({"_id": oid, "status": "published"})
        if not item:
            return None
        movie = db.movies.find_one({"_id": item["movie_id"], "status": "published"})
        if not movie:
            return None
        return {"content_type": "chapter", "content_id": str(oid), "title": item["title"], "slug": item["slug"],
                "url": f"/movies/{movie['slug']}/chapters/{item['slug']}", "poster_url": (item.get("poster_media") or {}).get("secure_url", movie.get("poster_url", "")),
                "release_year": movie.get("release_year"), "status": item["status"]}
    item = db.episodes.find_one({"_id": oid, "status": "published"})
    if not item:
        return None
    series = db.series.find_one({"_id": item["series_id"], "status": "published"})
    if not series:
        return None
    if item.get("type") == "regular" and not db.seasons.find_one({"_id": item.get("season_id"), "series_id": series["_id"], "status": "published"}):
        return None
    return {"content_type": "episode", "content_id": str(oid), "title": item["title"], "slug": item["slug"],
            "url": f"/series/{series['slug']}/episodes/{item['slug']}", "poster_url": (item.get("poster_media") or {}).get("secure_url", series.get("poster_url", "")),
            "release_year": series.get("release_year"), "status": item["status"], "series_title": series["title"]}
