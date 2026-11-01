from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from .services import list_favorites, set_favorite


class FavoriteServiceTests(SimpleTestCase):
    @patch("favorites.services.get_collection")
    @patch("favorites.services.public_content")
    def test_add_is_user_scoped_and_idempotent_upsert(self, public_content, get_collection):
        public_content.return_value = {"content_type": "movie", "content_id": "65f000000000000000000001"}
        set_favorite("user-a", "movie", "65f000000000000000000001")
        query, update = get_collection.return_value.update_one.call_args.args[:2]
        self.assertEqual(query["user_id"], "user-a")
        self.assertIn("$setOnInsert", update)
        self.assertTrue(get_collection.return_value.update_one.call_args.kwargs["upsert"])

    @patch("favorites.services.get_collection")
    @patch("favorites.services.public_content")
    def test_unpublished_content_is_not_added(self, public_content, get_collection):
        public_content.return_value = None
        self.assertIsNone(set_favorite("user-a", "movie", "65f000000000000000000001"))
        get_collection.assert_not_called()

    @patch("favorites.services.public_content")
    @patch("favorites.services.get_collection")
    def test_list_hydrates_only_current_users_records(self, get_collection, public_content):
        get_collection.return_value.count_documents.return_value = 1
        get_collection.return_value.find.return_value.sort.return_value.skip.return_value.limit.return_value = [
            {"user_id": "user-a", "content_type": "series", "content_id": "65f000000000000000000002", "created_at": datetime.now(timezone.utc)}
        ]
        public_content.return_value = {"content_type": "series", "content_id": "65f000000000000000000002", "title": "North"}
        result = list_favorites("user-a")
        self.assertEqual(get_collection.return_value.find.call_args.args[0], {"user_id": "user-a"})
        self.assertEqual(result["results"][0]["title"], "North")
