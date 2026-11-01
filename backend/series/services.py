from datetime import date, datetime, time, timezone

from bson import ObjectId
from bson.errors import InvalidId
from django.utils.text import slugify
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError

from config.mongo import get_database
from .mongo import get_episode_collection, get_season_collection, get_series_collection


class InvalidIdValue(Exception): pass
class SeriesNotFound(Exception): pass
class ContentConflict(Exception): pass


def parse_id(value):
    try: return ObjectId(value)
    except (InvalidId, TypeError): raise InvalidIdValue from None


def _data(doc):
    if not doc: return None
    result = dict(doc); result["id"] = str(result.pop("_id"))
    for key in ("series_id", "season_id", "created_by"):
        if result.get(key) is not None: result[key] = str(result[key])
    if isinstance(result.get("release_date"), datetime):
        result["release_date"] = result["release_date"].date()
    return result


def _bson_date(value):
    if value is None or isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time.min, tzinfo=timezone.utc)
    return value


def _episode_write_values(values):
    result=dict(values)
    if "release_date" in result:
        result["release_date"]=_bson_date(result["release_date"])
    return result


def _slug(collection, title, requested="", scope=None, exclude=None, session=None):
    base = slugify(requested or title)[:180].strip("-") or "title"
    candidate, n = base, 2
    while True:
        query = {"slug": candidate, **(scope or {})}
        if exclude: query["_id"] = {"$ne": exclude}
        if not collection.find_one(query, {"_id": 1}, **({"session": session} if session is not None else {})): return candidate
        if requested: raise ContentConflict("That slug is already in use in this collection.")
        suffix = f"-{n}"; candidate = f"{base[:190-len(suffix)]}{suffix}"; n += 1


def create_series(values, creator):
    c = get_series_collection(); now = datetime.now(timezone.utc); doc = dict(values)
    doc["slug"] = _slug(c, doc["title"], doc.pop("slug", "")); doc.update(created_at=now, updated_at=now, created_by=creator)
    try: doc["_id"] = c.insert_one(doc).inserted_id
    except DuplicateKeyError as exc: raise ContentConflict("That series slug is already in use.") from exc
    return _data(doc)


def get_series(identifier, published=False, by_id=False):
    query = {"_id": parse_id(identifier)} if by_id else {"slug": identifier}
    if published: query["status"] = "published"
    return _data(get_series_collection().find_one(query))


def list_series(filters=None, *, published=False, featured=False):
    filters = filters or {}; query = {}
    if published: query["status"] = "published"
    elif filters.get("status"): query["status"] = filters["status"]
    if featured: query["is_featured"] = True
    if filters.get("genre"): query["genres"] = filters["genre"].casefold()
    if filters.get("release_year"): query["release_year"] = filters["release_year"]
    if filters.get("search"): query["$text"] = {"$search": filters["search"]}
    page, size = filters.get("page", 1), filters.get("page_size", 20)
    c = get_series_collection(); total = c.count_documents(query)
    sort = {"title": [("title", ASCENDING)], "-created_at": [("created_at", DESCENDING)], "release_year": [("release_year", ASCENDING)], "-release_year": [("release_year", DESCENDING)]}.get(filters.get("sort", "-release_year"), [("release_year", DESCENDING)])
    docs = c.find(query).sort(sort).skip((page-1)*size).limit(size)
    return {"results": [_data(x) for x in docs], "page": page, "page_size": size, "total": total, "pages": (total+size-1)//size}


def update_series(series_id, changes):
    oid = parse_id(series_id); c = get_series_collection(); old = c.find_one({"_id": oid})
    if not old: raise SeriesNotFound
    values = dict(changes)
    if "slug" in values or "title" in values:
        values["slug"] = _slug(c, values.get("title", old["title"]), values.get("slug", ""), exclude=oid)
    values["updated_at"] = datetime.now(timezone.utc)
    try: return _data(c.find_one_and_update({"_id": oid}, {"$set": values}, return_document=True))
    except DuplicateKeyError as exc: raise ContentConflict("That series slug is already in use.") from exc


def delete_series(series_id):
    oid = parse_id(series_id); db = get_database(); series=db.series; seasons=db.seasons; episodes=db.episodes
    if not series.find_one({"_id": oid}): raise SeriesNotFound
    client=db.client
    with client.start_session() as session:
        def op(s):
            if not series.find_one({"_id":oid},session=s): raise SeriesNotFound
            series.update_one({"_id":oid},{"$inc":{"integrity_revision":1}},session=s)
            season_ids=[d["_id"] for d in seasons.find({"series_id":oid},{"_id":1},session=s)]
            episode_ids=[d["_id"] for d in episodes.find({"series_id":oid},{"_id":1},session=s)]
            episodes.delete_many({"series_id":oid},session=s); seasons.delete_many({"series_id":oid},session=s)
            series.delete_one({"_id":oid},session=s)
            return len(season_ids), episode_ids
        season_count, episode_ids = session.with_transaction(op)
    from media.services import remove_content_media
    for episode_id in episode_ids:
        remove_content_media("episode", episode_id)
    return season_count


def delete_series_confirmed(series_id, confirmation):
    oid=parse_id(series_id); series=get_series_collection(); existing=series.find_one({"_id":oid},{"slug":1})
    if not existing: raise SeriesNotFound
    if confirmation != existing["slug"]: return False
    delete_series(series_id)
    return True


def _parent_transaction(series_oid, callback):
    db=get_database(); series=db.series
    if not series.find_one({"_id":series_oid},{"_id":1}): raise SeriesNotFound
    with db.client.start_session() as session:
        def op(s):
            if series.update_one({"_id":series_oid},{"$inc":{"content_revision":1}},session=s).matched_count != 1: raise SeriesNotFound
            return callback(s)
        return session.with_transaction(op)


def seasons_for(series_slug, published=True):
    parent=get_series(series_slug,published=True)
    if not parent: return None
    q={"series_id":ObjectId(parent["id"])}
    if published: q["status"]="published"
    return [_data(d) for d in get_season_collection().find(q).sort("season_number",ASCENDING)]


def season_detail(series_slug, season_slug):
    parent=get_series(series_slug,published=True)
    if not parent:return None
    return _data(get_season_collection().find_one({"series_id":ObjectId(parent["id"]),"slug":season_slug,"status":"published"}))


def create_season(series_id, values, creator):
    soid=parse_id(series_id); c=get_season_collection(); now=datetime.now(timezone.utc)
    def op(s):
        existing=list(c.find({"series_id":soid},{"season_number":1},session=s).sort("season_number",ASCENDING))
        number=values.get("season_number",len(existing)+1)
        if number != len(existing)+1: raise ContentConflict(f"New seasons append at season {len(existing)+1}; use reorder to change numbering.")
        doc=dict(values); doc["season_number"]=number; doc["series_id"]=soid; doc["slug"]=_slug(c,doc["title"],doc.pop("slug",""),{"series_id":soid},session=s)
        doc.update(created_at=now,updated_at=now,created_by=creator); doc["_id"]=c.insert_one(doc,session=s).inserted_id; return _data(doc)
    try:return _parent_transaction(soid,op)
    except DuplicateKeyError as exc:raise ContentConflict("Season number or slug already exists in this series.") from exc


def admin_seasons(series_id):
    oid=parse_id(series_id)
    if not get_series_collection().find_one({"_id":oid}): raise SeriesNotFound
    return [_data(d) for d in get_season_collection().find({"series_id":oid}).sort("season_number",ASCENDING)]


def _season_admin(series_oid, season_id, session=None):
    season_oid=parse_id(season_id); season=get_season_collection().find_one({"_id":season_oid,"series_id":series_oid},**({"session":session} if session is not None else {}))
    if not season: raise SeriesNotFound
    return season_oid,season


def get_admin_season(series_id, season_id):
    soid=parse_id(series_id); oid,_=_season_admin(soid,season_id)
    return _data(get_season_collection().find_one({"_id":oid,"series_id":soid}))


def update_season(series_id, season_id, values):
    soid=parse_id(series_id); c=get_season_collection(); now=datetime.now(timezone.utc)
    def op(s):
        oid,old=_season_admin(soid,season_id,s); changes=dict(values)
        if "season_number" in changes: raise ContentConflict("Use the season reorder endpoint to change numbering.")
        if "slug" in changes or "title" in changes: changes["slug"]=_slug(c,changes.get("title",old["title"]),changes.get("slug",""),{"series_id":soid},oid,session=s)
        changes["updated_at"]=now; c.update_one({"_id":oid},{"$set":changes},session=s); return _data(c.find_one({"_id":oid},session=s))
    try:return _parent_transaction(soid,op)
    except DuplicateKeyError as exc:raise ContentConflict("Season slug already exists in this series.") from exc


def _assign_order(collection, docs, field, session):
    if not docs:return
    ids=[d["_id"] for d in docs]; offset=max(d[field] for d in docs)+len(docs)+1
    collection.update_many({"_id":{"$in":ids}},{"$inc":{field:offset}},session=session)
    now=datetime.now(timezone.utc)
    for n,d in enumerate(docs,1): collection.update_one({"_id":d["_id"]},{"$set":{field:n,"updated_at":now}},session=session)


def reorder_seasons(series_id, ids):
    soid=parse_id(series_id); requested=[parse_id(x) for x in ids]; c=get_season_collection()
    if len(set(requested))!=len(requested):raise ContentConflict("Season IDs must not repeat.")
    def op(s):
        docs=list(c.find({"series_id":soid},session=s).sort("season_number",ASCENDING))
        if {d["_id"] for d in docs}!=set(requested):raise ContentConflict("Include every season in this series exactly once.")
        byid={d["_id"]:d for d in docs}; ordered=[byid[x] for x in requested]; _assign_order(c,ordered,"season_number",s)
        return [_data(c.find_one({"_id":x},session=s)) for x in requested]
    try:return _parent_transaction(soid,op)
    except DuplicateKeyError as exc:raise ContentConflict("Season ordering conflicted with another update.") from exc


def delete_season(series_id, season_id):
    soid=parse_id(series_id); c=get_season_collection(); ep=get_episode_collection()
    deleted_episode_ids=[]
    def op(s):
        oid,_=_season_admin(soid,season_id,s)
        deleted_episode_ids.extend(d["_id"] for d in ep.find({"season_id":oid},{"_id":1},session=s))
        c.delete_one({"_id":oid},session=s); ep.delete_many({"season_id":oid},session=s)
        docs=list(c.find({"series_id":soid},session=s).sort("season_number",ASCENDING)); _assign_order(c,docs,"season_number",s)
        return {"deleted":True,"renumbered":True}
    result = _parent_transaction(soid,op)
    from media.services import remove_content_media
    for episode_id in deleted_episode_ids:
        remove_content_media("episode", episode_id)
    return result


def admin_episodes(series_id, season_id=None, special=None):
    soid=parse_id(series_id)
    if not get_series_collection().find_one({"_id":soid}):raise SeriesNotFound
    q={"series_id":soid}
    if season_id is not None:q["season_id"]=parse_id(season_id)
    if special is not None:q["type"]="special" if special else "regular"
    key="special_number" if special else "episode_number"
    return [_data(d) for d in get_episode_collection().find(q).sort(key,ASCENDING)]


def _create_episode(series_id, values, creator, season_id=None):
    soid=parse_id(series_id); c=get_episode_collection(); seasons=get_season_collection(); now=datetime.now(timezone.utc)
    special=season_id is None; season_oid=parse_id(season_id) if season_id else None
    def op(s):
        if special:
            nums=[d.get("special_number",0) for d in c.find({"series_id":soid,"type":"special"},{"special_number":1},session=s)]
            n=values.get("special_number",max(nums,default=0)+1); field="special_number"; scope={"series_id":soid,"type":"special"}
        else:
            season=seasons.find_one({"_id":season_oid,"series_id":soid},session=s)
            if not season:raise SeriesNotFound
            nums=[d.get("episode_number",0) for d in c.find({"season_id":season_oid,"type":"regular"},{"episode_number":1},session=s)]
            n=values.get("episode_number",max(nums,default=0)+1); field="episode_number"; scope={"season_id":season_oid,"type":"regular"}
        expected=max(nums,default=0)+1
        if n!=expected:raise ContentConflict(f"New content appends at number {expected}; use reorder to change numbering.")
        doc=_episode_write_values(values); doc.pop("episode_number",None); doc.pop("special_number",None); doc.update(series_id=soid,season_id=season_oid,type="special" if special else "regular")
        doc[field]=n; doc["slug"]=_slug(c,doc["title"],doc.pop("slug",""),scope,session=s); doc.update(created_at=now,updated_at=now,created_by=creator)
        doc["_id"]=c.insert_one(doc,session=s).inserted_id; return _data(doc)
    try:return _parent_transaction(soid,op)
    except DuplicateKeyError as exc:raise ContentConflict("Episode number or slug already exists in this parent.") from exc


def create_episode(series_id,values,creator,season_id=None):return _create_episode(series_id,values,creator,season_id)


def public_episodes(series_slug, season_slug=None, specials=False):
    parent=get_series(series_slug,published=True)
    if not parent:return None
    soid=ObjectId(parent["id"]); q={"series_id":soid,"type":"special" if specials else "regular","status":"published"}
    order="special_number" if specials else "episode_number"
    if not specials:
        season=get_season_collection().find_one({"series_id":soid,"slug":season_slug,"status":"published"},{"_id":1})
        if not season:return None
        q["season_id"]=season["_id"]
    return [_data(d) for d in get_episode_collection().find(q).sort(order,ASCENDING)]


def public_episode(series_slug, episode_slug):
    parent=get_series(series_slug,published=True)
    if not parent:return None
    soid=ObjectId(parent["id"]); e=get_episode_collection().find_one({"series_id":soid,"slug":episode_slug,"status":"published"})
    if not e:return None
    if e["type"]=="regular":
        season=get_season_collection().find_one({"_id":e.get("season_id"),"series_id":soid,"status":"published"})
        if not season:return None
    return _data(e)


def update_episode(series_id,episode_id,values):
    soid=parse_id(series_id); c=get_episode_collection(); now=datetime.now(timezone.utc)
    def op(s):
        oid=parse_id(episode_id); old=c.find_one({"_id":oid,"series_id":soid},session=s)
        if not old:raise SeriesNotFound
        changes=_episode_write_values(values)
        if "episode_number" in changes or "special_number" in changes:raise ContentConflict("Use the episode reorder endpoint to change numbering.")
        if "slug" in changes or "title" in changes:
            scope={"series_id":soid,"type":old["type"]}
            if old["type"]=="regular":scope={"season_id":old["season_id"],"type":"regular"}
            changes["slug"]=_slug(c,changes.get("title",old["title"]),changes.get("slug",""),scope,oid,session=s)
        changes["updated_at"]=now;c.update_one({"_id":oid},{"$set":changes},session=s);return _data(c.find_one({"_id":oid},session=s))
    try:return _parent_transaction(soid,op)
    except DuplicateKeyError as exc:raise ContentConflict("Episode slug already exists in this parent.") from exc


def get_admin_episode(series_id, episode_id):
    soid=parse_id(series_id); oid=parse_id(episode_id)
    if not get_series_collection().find_one({"_id":soid}):raise SeriesNotFound
    return _data(get_episode_collection().find_one({"_id":oid,"series_id":soid}))


def delete_episode(series_id,episode_id):
    soid=parse_id(series_id);c=get_episode_collection()
    def op(s):
        oid=parse_id(episode_id);old=c.find_one({"_id":oid,"series_id":soid},session=s)
        if not old:raise SeriesNotFound
        c.delete_one({"_id":oid},session=s);field="special_number" if old["type"]=="special" else "episode_number"
        q={"series_id":soid,"type":old["type"]}
        if old["type"]=="regular":q["season_id"]=old["season_id"]
        docs=list(c.find(q,session=s).sort(field,ASCENDING));_assign_order(c,docs,field,s);return {"deleted":True,"renumbered":True}
    result = _parent_transaction(soid,op)
    from media.services import remove_content_media
    remove_content_media("episode", parse_id(episode_id))
    return result


def reorder_episodes(series_id,ids,season_id=None,special=False):
    soid=parse_id(series_id);requested=[parse_id(x) for x in ids];c=get_episode_collection();field="special_number" if special else "episode_number"
    if len(set(requested))!=len(requested):raise ContentConflict("Episode IDs must not repeat.")
    q={"series_id":soid,"type":"special" if special else "regular"}
    if season_id:q["season_id"]=parse_id(season_id)
    def op(s):
        docs=list(c.find(q,session=s).sort(field,ASCENDING))
        if {d["_id"] for d in docs}!=set(requested):raise ContentConflict("Include every episode in this parent exactly once.")
        byid={d["_id"]:d for d in docs};ordered=[byid[x] for x in requested];_assign_order(c,ordered,field,s)
        return [_data(c.find_one({"_id":x},session=s)) for x in requested]
    try:return _parent_transaction(soid,op)
    except DuplicateKeyError as exc:raise ContentConflict("Episode order conflicted with another update.") from exc
