from datetime import datetime, timezone
from unittest.mock import patch

from bson import ObjectId
from django.test import SimpleTestCase

from .services import save_progress


class WatchProgressTests(SimpleTestCase):
    @patch("watch_progress.services.get_collection")
    @patch("watch_progress.services.public_content")
    def test_progress_is_scoped_and_updated_by_content_key(self, public_content, get_collection):
        oid = ObjectId()
        public_content.return_value = {"content_type": "episode", "content_id": str(oid), "title": "Pilot"}
        get_collection.return_value.find_one_and_update.return_value = {
            "_id": ObjectId(), "user_id": "user-a", "content_type": "episode", "content_id": oid,
            "position": 37.0, "duration": 100.0, "completed": False, "last_watched_at": datetime.now(timezone.utc),
        }
        result = save_progress("user-a", "episode", str(oid), 37, 100)
        query = get_collection.return_value.find_one_and_update.call_args.args[0]
        self.assertEqual(query["user_id"], "user-a")
        self.assertEqual(query["content_id"], oid)
        self.assertTrue(get_collection.return_value.find_one_and_update.call_args.kwargs["upsert"])
        self.assertEqual(result["position"], 37)
        self.assertEqual(result["content"]["title"], "Pilot")

    @patch("watch_progress.services.get_collection")
    @patch("watch_progress.services.public_content", return_value=None)
    def test_unpublished_content_cannot_create_progress(self, public_content, get_collection):
        self.assertIsNone(save_progress("user-a", "movie", "65f000000000000000000001", 4))
        get_collection.assert_not_called()
