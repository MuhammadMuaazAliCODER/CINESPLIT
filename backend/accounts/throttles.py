import hashlib
import time
from datetime import datetime, timedelta, timezone

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError
from rest_framework.throttling import SimpleRateThrottle

from .mongo import get_auth_database


class MongoRateThrottle(SimpleRateThrottle):
    """Fixed-window authentication throttling shared across backend workers."""

    def __init__(self):
        # The view supplies its scope later, in allow_request().
        self.rate = None

    def allow_request(self, request, view):
        self.scope = getattr(view, "throttle_scope", None)
        if not self.scope:
            return True
        self.rate = self.get_rate()
        self.num_requests, self.duration = self.parse_rate(self.rate)
        identity = self.get_ident(request)
        now_seconds = int(time.time())
        window_start = now_seconds - (now_seconds % self.duration)
        digest = hashlib.sha256(f"{self.scope}:{identity}:{window_start}".encode("utf-8")).hexdigest()
        expires_at = datetime.fromtimestamp(window_start + self.duration * 2, tz=timezone.utc)
        collection = get_auth_database().auth_rate_limits
        query = {"_id": digest}
        update = {"$inc": {"count": 1}, "$setOnInsert": {
            "scope": self.scope,
            "window_started_at": datetime.fromtimestamp(window_start, tz=timezone.utc),
            "expires_at": expires_at,
        }}
        try:
            record = collection.find_one_and_update(query, update, upsert=True, return_document=ReturnDocument.AFTER)
        except DuplicateKeyError:
            record = collection.find_one_and_update(query, {"$inc": {"count": 1}}, return_document=ReturnDocument.AFTER)
        self.now = time.time()
        self.wait_seconds = max(0, window_start + self.duration - self.now)
        return record["count"] <= self.num_requests

    def wait(self):
        return self.wait_seconds
