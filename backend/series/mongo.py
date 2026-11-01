from threading import Lock

from pymongo import ASCENDING, DESCENDING

from config.mongo import get_database

_ready = False
_lock = Lock()


def _collection(name):
    global _ready
    collection = getattr(get_database(), name)
    if not _ready:
        with _lock:
            if not _ready:
                ensure_indexes()
                _ready = True
    return collection


def ensure_indexes():
    db = get_database()
    series = db.series
    seasons = db.seasons
    episodes = db.episodes
    series.create_index([("slug", ASCENDING)], unique=True, name="series_slug_unique")
    series.create_index([("title", "text")], name="series_title_text")
    series.create_index([("status", ASCENDING), ("is_featured", ASCENDING)], name="series_status_featured")
    series.create_index([("genres", ASCENDING)], name="series_genres")
    series.create_index([("release_year", DESCENDING)], name="series_release_year")
    series.create_index([("created_at", DESCENDING)], name="series_created_at")
    seasons.create_index([("series_id", ASCENDING), ("season_number", ASCENDING)], unique=True, name="seasons_series_number_unique")
    seasons.create_index([("series_id", ASCENDING), ("slug", ASCENDING)], unique=True, name="seasons_series_slug_unique")
    seasons.create_index([("series_id", ASCENDING), ("status", ASCENDING), ("season_number", ASCENDING)], name="seasons_series_status_order")
    episodes.create_index([("season_id", ASCENDING), ("episode_number", ASCENDING)], unique=True, name="episodes_season_number_unique", partialFilterExpression={"type": "regular"})
    episodes.create_index([("series_id", ASCENDING), ("special_number", ASCENDING)], unique=True, name="episodes_special_number_unique", partialFilterExpression={"type": "special"})
    episodes.create_index([("season_id", ASCENDING), ("slug", ASCENDING)], unique=True, name="episodes_season_slug_unique", partialFilterExpression={"type": "regular"})
    episodes.create_index([("series_id", ASCENDING), ("slug", ASCENDING)], unique=True, name="episodes_special_slug_unique", partialFilterExpression={"type": "special"})
    episodes.create_index([("series_id", ASCENDING), ("status", ASCENDING), ("type", ASCENDING), ("release_date", ASCENDING)], name="episodes_series_publishing")
    episodes.create_index([("season_id", ASCENDING), ("status", ASCENDING), ("episode_number", ASCENDING)], name="episodes_season_publishing_order")


def get_series_collection(): return _collection("series")
def get_season_collection(): return _collection("seasons")
def get_episode_collection(): return _collection("episodes")
