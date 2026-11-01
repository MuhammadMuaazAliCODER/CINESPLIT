from datetime import datetime, timezone
import logging

from bson import ObjectId
from bson.errors import InvalidId
from cloudinary import uploader
from pymongo import ReturnDocument

from config.cloudinary_client import configure_cloudinary, is_cloudinary_configured, missing_cloudinary_variables
from config.mongo import get_database
from .mongo import get_media_collection, get_orphan_collection

MAX_VIDEO_SIZE = 500 * 1024 * 1024
MAX_IMAGE_SIZE = 10 * 1024 * 1024
VIDEO_TYPES = {"video/mp4", "video/webm", "video/quicktime", "video/x-m4v"}
IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
CONTENT_COLLECTIONS = {"movie": "movies", "chapter": "movie_chapters", "episode": "episodes"}
logger = logging.getLogger(__name__)


class MediaError(Exception):
    pass


class MediaConfigurationError(MediaError):
    pass


def _destroy_or_queue(public_id, resource_type, content_type, content_id, role, secure_url="", reason="replacement"):
    if not public_id:
        return False
    try:
        result = uploader.destroy(public_id, resource_type=resource_type)
        if result and result.get("result") in {"ok", "not found"}:
            return True
    except Exception:
        pass
    try:
        now = datetime.now(timezone.utc)
        get_orphan_collection().update_one(
            {"public_id": public_id},
            {"$setOnInsert": {"public_id": public_id, "resource_type": resource_type,
                              "content_type": content_type, "content_id": str(content_id), "role": role,
                              "secure_url": secure_url, "queued_at": now, "reason": reason}},
            upsert=True,
        )
    except Exception:
        pass
    return False


def remove_content_media(content_type, content_id):
    try:
        oid = content_id if isinstance(content_id, ObjectId) else ObjectId(content_id)
    except (InvalidId, TypeError):
        return
    try:
        collection = get_media_collection()
        query = {"content_type": content_type, "content_id": oid}
        items = list(collection.find(query))
        collection.delete_many(query)
    except Exception:
        logger.exception("Could not detach media metadata for deleted content %s/%s", content_type, oid)
        return
    for item in items:
        _destroy_or_queue(item.get("public_id"), item.get("resource_type", "image"), content_type,
                          oid, item.get("role", "media"), item.get("secure_url", ""), "content_deleted")


def validate_upload(upload, role):
    if role not in {"video", "poster"}:
        raise MediaError("Media role must be video or poster.")
    allowed = VIDEO_TYPES if role == "video" else IMAGE_TYPES
    limit = MAX_VIDEO_SIZE if role == "video" else MAX_IMAGE_SIZE
    if getattr(upload, "size", 0) <= 0 or upload.size > limit:
        raise MediaError(f"File must be between 1 byte and {limit // (1024 * 1024)} MB.")
    if getattr(upload, "content_type", "") not in allowed:
        raise MediaError("This file type is not supported.")
    position = upload.tell() if hasattr(upload, "tell") else 0
    header = upload.read(16)
    if hasattr(upload, "seek"):
        upload.seek(position)
    if role == "poster":
        valid = header.startswith(b"\xff\xd8\xff") or header.startswith(b"\x89PNG\r\n\x1a\n") or (header.startswith(b"RIFF") and header[8:12] == b"WEBP")
    else:
        valid = (len(header) >= 8 and header[4:8] == b"ftyp") or header.startswith(b"\x1aE\xdf\xa3")
    if not valid:
        raise MediaError("File contents do not match a supported media format.")


def _content_ref(content_type, content_id):
    if content_type not in CONTENT_COLLECTIONS:
        raise MediaError("Unsupported content type.")
    try:
        oid = ObjectId(content_id)
    except (InvalidId, TypeError):
        raise MediaError("Content id is invalid.") from None
    db = get_database()
    collection = getattr(db, CONTENT_COLLECTIONS[content_type])
    item = collection.find_one({"_id": oid})
    if not item:
        raise MediaError("Content was not found.")
    if content_type == "chapter" and not db.movies.find_one({"_id": item.get("movie_id")}):
        raise MediaError("Chapter parent movie was not found.")
    if content_type == "episode" and not db.series.find_one({"_id": item.get("series_id")}):
        raise MediaError("Episode parent series was not found.")
    return collection, oid, item


def get_associations(content_type, content_id):
    collection, oid, _ = _content_ref(content_type, content_id)
    item = collection.find_one({"_id": oid}) or {}
    return {"video": item.get("video"), "poster": item.get("poster_media")}


def list_media(page=1, page_size=20):
    collection = get_media_collection()
    orphans_collection = get_orphan_collection()
    total = collection.count_documents({}) + orphans_collection.count_documents({})
    candidate_limit = page * page_size
    cursor = collection.find({}, {"uploaded_by": 0}).sort("uploaded_at", -1).limit(candidate_limit)
    results = []
    for item in cursor:
        item["id"] = str(item.pop("_id"))
        item["content_id"] = str(item["content_id"])
        results.append(item)
    orphans = list(orphans_collection.find({}).sort("queued_at", -1).limit(candidate_limit))
    orphan_items = [{"id": f"orphan:{item['public_id']}", "public_id": item["public_id"],
                     "resource_type": item["resource_type"], "secure_url": item.get("secure_url", ""),
                     "format": None, "duration": None, "content_type": item["content_type"],
                     "content_id": item["content_id"], "role": item["role"], "uploaded_at": item["queued_at"],
                     "cleanup_pending": True, "reason": item.get("reason", "replacement")} for item in orphans]
    all_items = results + orphan_items
    all_items.sort(key=lambda item: item["uploaded_at"], reverse=True)
    results = all_items[(page - 1) * page_size:(page - 1) * page_size + page_size]
    return {"results": results, "page": page, "page_size": page_size, "total": total,
            "pages": (total + page_size - 1) // page_size}


def upload_and_associate(content_type, content_id, role, upload, actor_id):
    validate_upload(upload, role)
    if not is_cloudinary_configured():
        missing = ", ".join(missing_cloudinary_variables())
        raise MediaConfigurationError(f"Media uploads are not configured. Set these backend environment variables: {missing}.")
    configure_cloudinary()
    collection, oid, old_content = _content_ref(content_type, content_id)
    resource_type = "video" if role == "video" else "image"
    try:
        result = uploader.upload(
            upload,
            resource_type=resource_type,
            folder=f"cinesplit/{content_type}/{oid}",
            use_filename=False,
            unique_filename=True,
            overwrite=False,
            allowed_formats=["mp4", "webm", "mov", "m4v"] if role == "video" else ["jpg", "jpeg", "png", "webp"],
        )
    except Exception as exc:
        raise MediaError("Cloudinary could not upload this file.") from exc
    metadata = {
        "public_id": result.get("public_id"),
        "resource_type": resource_type,
        "secure_url": result.get("secure_url"),
        "format": result.get("format"),
        "duration": result.get("duration"),
        "content_type": content_type,
        "content_id": oid,
        "role": role,
        "uploaded_at": datetime.now(timezone.utc),
        "uploaded_by": str(actor_id),
    }
    if not metadata["public_id"] or not metadata["secure_url"]:
        _destroy_or_queue(result.get("public_id"), resource_type, content_type, oid, role,
                          result.get("secure_url", ""), "invalid_upload_response")
        raise MediaError("Cloudinary returned incomplete media details.")
    field = "video" if role == "video" else "poster_media"
    previous = old_content.get(field) or {}
    try:
        get_media_collection().find_one_and_update(
            {"content_type": content_type, "content_id": oid, "role": role},
            {"$set": metadata}, upsert=True, return_document=ReturnDocument.AFTER,
        )
        changes = {field: metadata, "updated_at": datetime.now(timezone.utc)}
        if content_type == "movie" and role == "poster":
            changes["poster_url"] = metadata["secure_url"]
        result = collection.update_one({"_id": oid}, {"$set": changes})
        if result.matched_count != 1:
            raise MediaError("Content was removed before the media association completed.")
    except Exception as exc:
        try:
            if previous:
                rollback = {field: previous}
                if content_type == "movie" and role == "poster":
                    rollback["poster_url"] = old_content.get("poster_url", "")
                collection.update_one({"_id": oid}, {"$set": rollback})
                get_media_collection().update_one(
                    {"content_type": content_type, "content_id": oid, "role": role}, {"$set": previous}
                )
            else:
                collection.update_one({"_id": oid}, {"$unset": {field: ""}})
                if content_type == "movie" and role == "poster":
                    collection.update_one({"_id": oid}, {"$set": {"poster_url": old_content.get("poster_url", "")}})
                get_media_collection().delete_one({"content_type": content_type, "content_id": oid, "role": role})
        except Exception:
            pass
        _destroy_or_queue(metadata["public_id"], resource_type, content_type, oid, role,
                          metadata["secure_url"], "association_failed")
        raise MediaError("Media was uploaded but could not be associated with content.") from exc
    if previous.get("public_id") and previous.get("public_id") != metadata["public_id"]:
        _destroy_or_queue(previous["public_id"], previous.get("resource_type", resource_type), content_type,
                          oid, role, previous.get("secure_url", ""), "replaced")
    metadata["content_id"] = str(oid)
    metadata["uploaded_by"] = str(actor_id)
    return metadata
