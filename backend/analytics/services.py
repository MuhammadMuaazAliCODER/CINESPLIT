from datetime import datetime, timezone

from config.mongo import get_database


def dashboard_data():
    db = get_database()
    counts = {
        "users": db.users.count_documents({}),
        "movies": db.movies.count_documents({}),
        "series": db.series.count_documents({}),
        "seasons": db.seasons.count_documents({}),
        "episodes": db.episodes.count_documents({}),
        "media_assets": db.media.count_documents({}),
        "media_cleanup_pending": db.media_orphans.count_documents({}),
        "reviews": db.reviews.count_documents({}),
        "published": sum(collection.count_documents({"status": "published"}) for collection in (db.movies, db.series, db.seasons, db.episodes, db.movie_chapters)),
        "drafts": sum(collection.count_documents({"status": "draft"}) for collection in (db.movies, db.series, db.seasons, db.episodes, db.movie_chapters)),
    }
    registrations = list(db.users.find({}, {"username": 1, "created_at": 1}).sort("created_at", -1).limit(8))
    for item in registrations:
        item["id"] = str(item.pop("_id")); item["created_at"] = item["created_at"].isoformat()
    recent = []
    for kind, collection in (("movie", db.movies), ("series", db.series), ("season", db.seasons), ("episode", db.episodes)):
        recent.extend({"type": kind, "title": d.get("title", ""), "created_at": d["created_at"].isoformat()}
                      for d in collection.find({}, {"title": 1, "created_at": 1}).sort("created_at", -1).limit(5) if d.get("created_at"))
    recent.sort(key=lambda item: item["created_at"], reverse=True)
    return {"counts": counts, "recent_users": registrations, "recent_content": recent[:8]}
