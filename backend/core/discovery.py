import re

from pymongo import ASCENDING, DESCENDING

from config.mongo import get_database


SORTS = {"-release_year": ("release_year", DESCENDING), "release_year": ("release_year", ASCENDING),
         "title": ("title", ASCENDING), "-title": ("title", DESCENDING), "-created_at": ("created_at", DESCENDING)}


def _query(filters, kind):
    query = {"status": "published"}
    search = filters.get("search", "").strip()
    if search:
        pattern = re.compile(re.escape(search), re.IGNORECASE)
        fields = ["title", "description", "short_description"] if kind in {"movie", "series"} else ["title"]
        query["$or"] = [{field: pattern} for field in fields]
    if filters.get("genre"):
        query["genres"] = filters["genre"].strip().casefold()
    if filters.get("release_year"):
        query["release_year"] = filters["release_year"]
    return query


def discover(filters=None, *, featured=False, latest=False):
    filters = filters or {}
    db = get_database()
    page = filters.get("page", 1)
    page_size = filters.get("page_size", 20)
    kinds = [filters["content_type"]] if filters.get("content_type") else ["movie", "series"]
    results = []
    total = 0
    limit = min(page * page_size, 2500)
    for kind in kinds:
        collection = db.movies if kind == "movie" else db.series
        query = _query(filters, kind)
        if featured:
            query["is_featured"] = True
        total += collection.count_documents(query)
        order = SORTS["-release_year"] if latest else SORTS[filters.get("sort", "-release_year")]
        cursor = collection.find(query).sort([order, ("title", ASCENDING)]).limit(limit)
        for item in cursor:
            results.append({"id": str(item["_id"]), "content_type": kind, "title": item["title"], "slug": item["slug"],
                            "short_description": item.get("short_description", ""), "release_year": item.get("release_year"),
                            "genres": item.get("genres", []), "poster_url": item.get("poster_url", ""),
                            "is_featured": item.get("is_featured", False), "url": f"/{'movies' if kind == 'movie' else 'series'}/{item['slug']}",
                            "_created_at": item.get("created_at", "")})
    if latest:
        results.sort(key=lambda item: (item.get("release_year") or 0, item["title"].casefold()), reverse=True)
    elif filters.get("sort") == "-created_at":
        results.sort(key=lambda item: item["_created_at"], reverse=True)
    elif filters.get("sort") in {"title", "-title"}:
        results.sort(key=lambda item: (item["title"].casefold(), item["content_type"]), reverse=filters.get("sort") == "-title")
    elif filters.get("sort") == "release_year":
        results.sort(key=lambda item: (item.get("release_year") or 0, item["title"].casefold()))
    else:
        results.sort(key=lambda item: (item.get("release_year") or 0, item["title"].casefold()), reverse=True)
    for item in results:
        item.pop("_created_at", None)
    return {"results": results[(page - 1) * page_size:(page - 1) * page_size + page_size], "page": page,
            "page_size": page_size, "total": total, "pages": (total + page_size - 1) // page_size}
