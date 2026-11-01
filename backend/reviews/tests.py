from datetime import datetime, timezone
from unittest.mock import patch

from bson import ObjectId
from django.test import SimpleTestCase

from .services import create_review, review_summary


class ReviewServiceTests(SimpleTestCase):
    @patch("reviews.services.get_collection")
    @patch("reviews.services.public_content")
    def test_review_summary_aggregates_and_paginates_published_content(self, public_content, get_collection):
        public_content.return_value = {"content_type": "movie", "content_id": "65f000000000000000000001"}
        item = {"_id": ObjectId(), "user_id": "user-a", "username": "viewer", "rating": 5, "body": "Excellent", "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc)}
        get_collection.return_value.aggregate.return_value = [{"average": 4.5, "count": 2}]
        get_collection.return_value.find.return_value.sort.return_value.skip.return_value.limit.return_value = [item]
        result = review_summary("movie", "65f000000000000000000001", page_size=1)
        self.assertEqual(result["average_rating"], 4.5)
        self.assertEqual(result["rating_count"], 2)
        self.assertEqual(result["pages"], 2)

    @patch("reviews.services.get_collection")
    @patch("reviews.services.public_content", return_value=None)
    def test_unpublished_content_cannot_receive_a_review(self, public_content, get_collection):
        self.assertIsNone(create_review("user-a", "viewer", "movie", "65f000000000000000000001", 5, ""))
        get_collection.assert_not_called()
