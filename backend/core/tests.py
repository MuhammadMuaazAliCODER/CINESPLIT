from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from .discovery import discover


class DiscoveryTests(SimpleTestCase):
    @patch("core.discovery.get_database")
    def test_search_is_published_only_and_bounded(self, get_db):
        db = MagicMock()
        get_db.return_value = db
        for collection in (db.movies, db.series):
            collection.count_documents.return_value = 1
            collection.find.return_value.sort.return_value.limit.return_value = []
        discover({"search": "a.*b", "page": 2, "page_size": 10})
        query = db.movies.count_documents.call_args.args[0]
        self.assertEqual(query["status"], "published")
        self.assertNotEqual(query["$or"][0]["title"].pattern, "a.*b")
        db.movies.find.return_value.sort.return_value.limit.assert_called_with(20)
