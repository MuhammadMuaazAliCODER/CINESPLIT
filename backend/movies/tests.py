from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from bson import ObjectId
from pymongo.errors import DuplicateKeyError
from django.test import SimpleTestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory, force_authenticate

from .mongo import ensure_chapter_indexes, ensure_indexes
from .serializers import ChapterReorderSerializer, ChapterWriteSerializer, MovieListQuerySerializer, MovieWriteSerializer
from .services import (
    InvalidMovieId, MovieConflict, MovieHasChapters, create_movie, delete_movie, get_movie_by_id,
    list_movies, update_movie,
)
from .views import AdminMovieCollectionView, MovieListView, PublicMovieDetailView
from .chapter_views import AdminChapterCollectionView, PublicChapterListView, PublicChapterDetailView
from .chapter_services import list_public_chapters


def valid_movie(**overrides):
    values = {
        "title": "The Long Night", "slug": "", "short_description": "A quiet mystery.",
        "description": "A full story description.", "release_year": 2025, "genres": ["mystery", "drama"],
        "original_language": "english", "duration_minutes": 118, "content_rating": "PG-13",
        "cast": ["Avery Stone"], "director": "Riley North", "production_company": "North House",
        "country": "United States", "status": "draft", "is_featured": False,
        "poster_url": "", "backdrop_url": "",
    }
    values.update(overrides)
    return values


class MovieSerializerTests(SimpleTestCase):
    def test_movie_write_serializer_normalizes_genres_and_rejects_unknown_fields(self):
        serializer = MovieWriteSerializer(data=valid_movie(genres=[" Drama ", "Mystery"]))
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["genres"], ["drama", "mystery"])
        invalid = MovieWriteSerializer(data=valid_movie(role="admin"))
        self.assertFalse(invalid.is_valid())
        self.assertIn("role", invalid.errors)

    def test_movie_write_serializer_rejects_invalid_duration_and_duplicate_genres(self):
        for overrides in ({"duration_minutes": 0}, {"genres": ["drama", "Drama"]}, {"content_rating": "unrated"}):
            serializer = MovieWriteSerializer(data=valid_movie(**overrides))
            self.assertFalse(serializer.is_valid())

    def test_query_serializer_bounds_page_size_and_whitelists_sort_fields(self):
        valid = MovieListQuerySerializer(data={"search": "moon", "page": "2", "sort": "-release_year"})
        self.assertTrue(valid.is_valid(), valid.errors)
        invalid = MovieListQuerySerializer(data={"page_size": "1000", "sort": "title;drop"})
        self.assertFalse(invalid.is_valid())


class ChapterSerializerTests(SimpleTestCase):
    def test_chapter_serializer_validates_duration_status_and_unknown_fields(self):
        valid = ChapterWriteSerializer(data={"title": "Arrival", "duration": 42, "status": "draft", "is_free": True})
        self.assertTrue(valid.is_valid(), valid.errors)
        for invalid_data in (
            {"title": "Arrival", "duration": 0},
            {"title": "Arrival", "duration": 42, "status": "scheduled"},
            {"title": "Arrival", "duration": 42, "role": "admin"},
        ):
            self.assertFalse(ChapterWriteSerializer(data=invalid_data).is_valid())

    def test_reorder_serializer_only_accepts_a_list_of_ids(self):
        valid = ChapterReorderSerializer(data={"chapter_ids": [str(ObjectId())]})
        self.assertTrue(valid.is_valid(), valid.errors)
        self.assertFalse(ChapterReorderSerializer(data={"chapter_ids": ["x" * 25]}).is_valid())


class MovieMongoServiceTests(SimpleTestCase):
    @patch("movies.services.get_movie_collection")
    def test_create_generates_a_unique_slug_and_records_creator_and_timestamps(self, get_collection):
        collection = MagicMock()
        collection.find_one.side_effect = [{"_id": ObjectId()}, None]
        inserted_id = ObjectId()
        collection.insert_one.return_value.inserted_id = inserted_id
        get_collection.return_value = collection

        result = create_movie(valid_movie(), "admin-id")

        self.assertEqual(result["slug"], "the-long-night-2")
        self.assertEqual(result["id"], str(inserted_id))
        inserted = collection.insert_one.call_args.args[0]
        self.assertEqual(inserted["created_by"], "admin-id")
        self.assertEqual(inserted["created_at"], inserted["updated_at"])

    @patch("movies.services.get_movie_collection")
    def test_duplicate_key_race_becomes_movie_conflict(self, get_collection):
        collection = MagicMock()
        collection.find_one.return_value = None
        collection.insert_one.side_effect = DuplicateKeyError("duplicate")
        get_collection.return_value = collection
        with self.assertRaises(MovieConflict):
            create_movie(valid_movie(), "admin-id")

    @patch("movies.services.get_movie_collection")
    def test_partial_update_sets_only_requested_field_and_timestamp(self, get_collection):
        movie_id = ObjectId()
        existing = {"_id": movie_id, "title": "The Long Night", "slug": "the-long-night", "is_featured": False}
        updated = {**existing, "is_featured": True, "updated_at": datetime.now(timezone.utc)}
        collection = MagicMock()
        collection.find_one.return_value = existing
        collection.find_one_and_update.return_value = updated
        get_collection.return_value = collection

        result = update_movie(str(movie_id), {"is_featured": True})

        update = collection.find_one_and_update.call_args.args[1]["$set"]
        self.assertEqual(update["is_featured"], True)
        self.assertEqual(set(update), {"is_featured", "updated_at"})
        self.assertTrue(result["is_featured"])

    @patch("movies.services.get_movie_collection")
    def test_duplicate_slug_on_update_is_rejected(self, get_collection):
        movie_id, other_id = ObjectId(), ObjectId()
        collection = MagicMock()
        collection.find_one.return_value = {"_id": movie_id, "title": "Film", "slug": "film"}
        collection.find_one.side_effect = [
            {"_id": movie_id, "title": "Film", "slug": "film"},
            {"_id": other_id},
        ]
        get_collection.return_value = collection
        with self.assertRaises(MovieConflict):
            update_movie(str(movie_id), {"slug": "other-film"})
        collection.find_one_and_update.assert_not_called()

    @patch("movies.services.get_database")
    @patch("movies.services.get_chapter_collection")
    @patch("movies.services.get_movie_collection")
    def test_delete_requires_matching_slug_confirmation_and_preserves_movies_with_chapters(self, get_collection, get_chapters, get_database):
        movie_id = ObjectId()
        collection = MagicMock()
        collection.find_one.return_value = {"_id": movie_id, "slug": "the-long-night"}
        collection.update_one.return_value.matched_count = 1
        collection.delete_one.return_value.deleted_count = 1
        get_collection.return_value = collection
        chapters = MagicMock()
        chapters.count_documents.return_value = 0
        get_chapters.return_value = chapters
        session = MagicMock()
        session.with_transaction.side_effect = lambda callback: callback(session)
        get_database.return_value.client.start_session.return_value.__enter__.return_value = session

        self.assertFalse(delete_movie(str(movie_id), "wrong-slug"))
        collection.delete_one.assert_not_called()
        self.assertTrue(delete_movie(str(movie_id), "the-long-night"))
        collection.delete_one.assert_called_once()
        chapters.count_documents.return_value = 1
        with self.assertRaises(MovieHasChapters):
            delete_movie(str(movie_id), "the-long-night")

    @patch("movies.services.get_movie_collection")
    def test_malformed_object_id_is_rejected_without_a_database_lookup(self, get_collection):
        with self.assertRaises(InvalidMovieId):
            get_movie_by_id("not-an-object-id")
        get_collection.assert_not_called()

    @patch("movies.services.get_movie_collection")
    def test_public_query_is_filtered_to_published_and_uses_bounded_pagination(self, get_collection):
        movie = {"_id": ObjectId(), "slug": "film", "title": "Film"}
        cursor = MagicMock()
        cursor.sort.return_value = cursor
        cursor.skip.return_value = cursor
        cursor.limit.return_value = [movie]
        collection = MagicMock()
        collection.count_documents.return_value = 41
        collection.find.return_value = cursor
        get_collection.return_value = collection

        result = list_movies({"search": "night", "genre": "drama", "release_year": 2024, "status": "draft", "page": 2, "page_size": 20}, published_only=True)

        query = collection.count_documents.call_args.args[0]
        self.assertEqual(query["status"], "published")
        self.assertEqual(query["$text"], {"$search": "night"})
        self.assertEqual(query["genres"], "drama")
        self.assertEqual(query["release_year"], 2024)
        cursor.skip.assert_called_once_with(20)
        cursor.limit.assert_called_once_with(20)
        self.assertEqual(result["pages"], 3)
        self.assertEqual(result["results"][0]["id"], str(movie["_id"]))

    def test_indexes_cover_slug_title_genres_release_language_status_and_featured(self):
        collection = MagicMock()
        ensure_indexes(collection)
        indexes = {call.kwargs["name"]: call for call in collection.create_index.call_args_list}
        self.assertEqual(set(indexes), {
            "movies_slug_unique", "movies_title_text", "movies_genres", "movies_release_year",
            "movies_language", "movies_content_rating", "movies_status", "movies_featured",
        })
        self.assertTrue(indexes["movies_slug_unique"].kwargs["unique"])


class ChapterMongoServiceTests(SimpleTestCase):
    def test_chapter_indexes_enforce_unique_movie_number_and_slug(self):
        collection = MagicMock()
        ensure_chapter_indexes(collection)
        indexes = {call.kwargs["name"]: call for call in collection.create_index.call_args_list}
        self.assertEqual(set(indexes), {
            "movie_chapters_movie_number_unique", "movie_chapters_movie_slug_unique", "movie_chapters_movie_status_order"
        })
        self.assertTrue(indexes["movie_chapters_movie_number_unique"].kwargs["unique"])
        self.assertTrue(indexes["movie_chapters_movie_slug_unique"].kwargs["unique"])

    @patch("movies.chapter_services.get_chapter_collection")
    @patch("movies.chapter_services.get_movie_collection")
    def test_public_chapter_query_requires_published_movie_and_published_chapter(self, get_movies, get_chapters):
        movie_id = ObjectId()
        get_movies.return_value.find_one.return_value = {"_id": movie_id}
        cursor = MagicMock()
        cursor.sort.return_value = [{"_id": ObjectId(), "movie_id": movie_id, "chapter_number": 1, "slug": "arrival"}]
        get_chapters.return_value.find.return_value = cursor
        result = list_public_chapters("published-film")
        get_movies.return_value.find_one.assert_called_once_with({"slug": "published-film", "status": "published"}, {"_id": 1})
        get_chapters.return_value.find.assert_called_once_with({"movie_id": movie_id, "status": "published"})
        cursor.sort.assert_called_once_with("chapter_number", 1)
        self.assertEqual(result[0]["movie_id"], str(movie_id))

    def test_public_chapter_query_returns_no_results_for_unpublished_movie(self):
        with patch("movies.chapter_services.get_movie_collection") as get_movies, patch("movies.chapter_services.get_chapter_collection") as get_chapters:
            get_movies.return_value.find_one.return_value = None
            self.assertEqual(list_public_chapters("draft-film"), [])
            get_chapters.assert_not_called()


class MovieViewAuthorizationTests(SimpleTestCase):
    def test_public_list_always_requests_published_movies(self):
        request = APIRequestFactory().get("/api/movies/")
        with patch("movies.views.list_movies", return_value={"results": [], "page": 1, "page_size": 20, "total": 0, "pages": 0}) as list_call:
            response = MovieListView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(list_call.call_args.kwargs["published_only"])

    def test_public_detail_does_not_query_drafts_as_public(self):
        request = APIRequestFactory().get("/api/movies/a-film/")
        with patch("movies.views.get_movie_by_slug", return_value=None) as get_movie:
            response = PublicMovieDetailView.as_view()(request, slug="a-film")
        self.assertEqual(response.status_code, 404)
        self.assertTrue(get_movie.call_args.kwargs["published_only"])

    def test_regular_user_cannot_access_admin_movie_list(self):
        request = APIRequestFactory().get("/api/admin/movies/")
        force_authenticate(request, user=SimpleNamespace(id="user-id", role="user", is_authenticated=True))
        response = AdminMovieCollectionView.as_view()(request)
        self.assertEqual(response.status_code, 403)

    def test_regular_user_cannot_access_admin_chapters(self):
        request = APIRequestFactory().get("/api/admin/movies/movie-id/chapters/")
        force_authenticate(request, user=SimpleNamespace(id="user-id", role="user", is_authenticated=True))
        response = AdminChapterCollectionView.as_view()(request, movie_id=str(ObjectId()))
        self.assertEqual(response.status_code, 403)

    def test_public_chapter_list_never_queries_drafts(self):
        request = APIRequestFactory().get("/api/movies/public-film/chapters/")
        with patch("movies.chapter_views.get_movie_by_slug", return_value={"id": str(ObjectId())}) as movie_lookup, patch("movies.chapter_views.list_public_chapters", return_value=[]) as chapter_lookup:
            response = PublicChapterListView.as_view()(request, movie_slug="public-film")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(movie_lookup.call_args.kwargs["published_only"])
        chapter_lookup.assert_called_once_with("public-film")

    def test_public_chapter_detail_hides_unpublished_content(self):
        request = APIRequestFactory().get("/api/movies/film/chapters/secret/")
        with patch("movies.chapter_views.get_public_chapter", return_value=None) as lookup:
            response = PublicChapterDetailView.as_view()(request, movie_slug="film", chapter_slug="secret")
        self.assertEqual(response.status_code, 404)
        lookup.assert_called_once_with("film", "secret")


class MovieURLTests(SimpleTestCase):
    def test_public_and_admin_movie_routes_are_registered(self):
        self.assertEqual(reverse("movies-list"), "/api/movies/")
        self.assertEqual(reverse("movies-featured"), "/api/movies/featured/")
        self.assertEqual(reverse("movies-genres"), "/api/movies/genres/")
        self.assertEqual(reverse("movies-detail", kwargs={"slug": "moon-river"}), "/api/movies/moon-river/")
        self.assertEqual(reverse("admin-movies-list"), "/api/admin/movies/")
        self.assertEqual(reverse("admin-movies-detail", kwargs={"movie_id": "65f000000000000000000001"}), "/api/admin/movies/65f000000000000000000001/")
        self.assertEqual(reverse("public-movie-chapters", kwargs={"movie_slug": "moon-river"}), "/api/movies/moon-river/chapters/")
        self.assertEqual(reverse("public-movie-chapter-detail", kwargs={"movie_slug": "moon-river", "chapter_slug": "arrival"}), "/api/movies/moon-river/chapters/arrival/")
        self.assertEqual(reverse("admin-movie-chapters", kwargs={"movie_id": "65f000000000000000000001"}), "/api/admin/movies/65f000000000000000000001/chapters/")
        self.assertEqual(reverse("admin-movie-chapters-reorder", kwargs={"movie_id": "65f000000000000000000001"}), "/api/admin/movies/65f000000000000000000001/chapters/reorder/")
