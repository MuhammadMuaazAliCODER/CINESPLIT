from drf_spectacular.utils import extend_schema
from pymongo.errors import DuplicateKeyError
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.api_serializers import ErrorSerializer
from accounts.permissions import IsAdministrator, IsAuthenticatedUser
from .chapter_services import (
    ChapterConflict, ChapterNotFound, InvalidChapterId, create_chapter, delete_chapter,
    get_chapter, get_public_chapter, list_chapters, list_public_chapters, parse_chapter_id, reorder_chapters, update_chapter,
)
from .serializers import AdminChapterSerializer, ChapterReorderSerializer, ChapterSerializer, ChapterWriteSerializer
from .services import InvalidMovieId, MovieNotFound, get_movie_by_slug, parse_movie_id


def _error(code, detail, status_code, errors=None):
    body = {"code": code, "detail": detail}
    if errors is not None:
        body["errors"] = errors
    return Response(body, status=status_code)


def _bad_id(movie_id):
    try:
        parse_movie_id(movie_id)
    except InvalidMovieId:
        return _error("invalid_movie_id", "Movie id is invalid.", status.HTTP_400_BAD_REQUEST)
    return None


class PublicChapterListView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(operation_id="public_movie_chapters", summary="List published chapters for a published movie", responses={200: ChapterSerializer(many=True), 404: ErrorSerializer})
    def get(self, request, movie_slug):
        if not get_movie_by_slug(movie_slug, published_only=True):
            return _error("movie_not_found", "Movie not found.", status.HTTP_404_NOT_FOUND)
        return Response(ChapterSerializer(list_public_chapters(movie_slug), many=True).data)


class PublicChapterDetailView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(operation_id="public_movie_chapter_detail", summary="Get a published chapter by movie and chapter slug", responses={200: ChapterSerializer, 404: ErrorSerializer})
    def get(self, request, movie_slug, chapter_slug):
        chapter = get_public_chapter(movie_slug, chapter_slug)
        if not chapter:
            return _error("chapter_not_found", "Chapter not found.", status.HTTP_404_NOT_FOUND)
        return Response(ChapterSerializer(chapter).data)


class AdminChapterCollectionView(APIView):
    permission_classes = [IsAuthenticatedUser, IsAdministrator]

    @extend_schema(operation_id="admin_movie_chapters", summary="List all chapters for a movie", responses={200: AdminChapterSerializer(many=True), 400: ErrorSerializer, 404: ErrorSerializer})
    def get(self, request, movie_id):
        error = _bad_id(movie_id)
        if error:
            return error
        try:
            if not get_movie_by_id_safe(movie_id):
                return _error("movie_not_found", "Movie not found.", status.HTTP_404_NOT_FOUND)
            return Response(AdminChapterSerializer(list_chapters(movie_id), many=True).data)
        except InvalidMovieId:
            return _error("invalid_movie_id", "Movie id is invalid.", status.HTTP_400_BAD_REQUEST)

    @extend_schema(operation_id="admin_movie_chapter_create", summary="Create a chapter", request=ChapterWriteSerializer, responses={201: AdminChapterSerializer, 400: ErrorSerializer, 404: ErrorSerializer, 409: ErrorSerializer})
    def post(self, request, movie_id):
        error = _bad_id(movie_id)
        if error:
            return error
        serializer = ChapterWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return _error("validation_error", "Chapter data is invalid.", status.HTTP_400_BAD_REQUEST, serializer.errors)
        try:
            result = create_chapter(movie_id, serializer.validated_data, request.user.id)
        except MovieNotFound:
            return _error("movie_not_found", "Movie not found.", status.HTTP_404_NOT_FOUND)
        except (ChapterConflict, DuplicateKeyError) as exc:
            return _error("chapter_conflict", str(exc) if isinstance(exc, ChapterConflict) else "Chapter number or slug already exists.", status.HTTP_409_CONFLICT)
        return Response(AdminChapterSerializer(result).data, status=status.HTTP_201_CREATED)


def get_movie_by_id_safe(movie_id):
    from .services import get_movie_by_id
    return get_movie_by_id(movie_id)


class AdminChapterDetailView(APIView):
    permission_classes = [IsAuthenticatedUser, IsAdministrator]

    @extend_schema(operation_id="admin_movie_chapter_detail", summary="Get a chapter for administrators", responses={200: AdminChapterSerializer, 400: ErrorSerializer, 404: ErrorSerializer})
    def get(self, request, movie_id, chapter_id):
        error = _bad_id(movie_id)
        if error:
            return error
        try:
            chapter = get_chapter(movie_id, chapter_id)
        except InvalidChapterId:
            return _error("invalid_chapter_id", "Chapter id is invalid.", status.HTTP_400_BAD_REQUEST)
        except InvalidMovieId:
            return _error("invalid_movie_id", "Movie id is invalid.", status.HTTP_400_BAD_REQUEST)
        if not chapter:
            return _error("chapter_not_found", "Chapter not found.", status.HTTP_404_NOT_FOUND)
        return Response(AdminChapterSerializer(chapter).data)

    @extend_schema(operation_id="admin_movie_chapter_update", summary="Update a chapter", request=ChapterWriteSerializer, responses={200: AdminChapterSerializer, 400: ErrorSerializer, 404: ErrorSerializer, 409: ErrorSerializer})
    def patch(self, request, movie_id, chapter_id):
        return self._update(request, movie_id, chapter_id, partial=True)

    @extend_schema(operation_id="admin_movie_chapter_replace", summary="Replace a chapter", request=ChapterWriteSerializer, responses={200: AdminChapterSerializer, 400: ErrorSerializer, 404: ErrorSerializer, 409: ErrorSerializer})
    def put(self, request, movie_id, chapter_id):
        return self._update(request, movie_id, chapter_id, partial=False)

    def _update(self, request, movie_id, chapter_id, partial):
        error = _bad_id(movie_id)
        if error:
            return error
        try:
            parse_chapter_id(chapter_id)
        except InvalidChapterId:
            return _error("invalid_chapter_id", "Chapter id is invalid.", status.HTTP_400_BAD_REQUEST)
        serializer = ChapterWriteSerializer(data=request.data, partial=partial)
        if not serializer.is_valid():
            return _error("validation_error", "Chapter data is invalid.", status.HTTP_400_BAD_REQUEST, serializer.errors)
        if "chapter_number" in serializer.validated_data:
            return _error("validation_error", "Use the reorder endpoint to change chapter numbers.", status.HTTP_400_BAD_REQUEST,
                          {"chapter_number": ["Chapter numbers can only be changed by reordering the full chapter list."]})
        try:
            chapter = update_chapter(movie_id, chapter_id, serializer.validated_data)
        except ChapterNotFound:
            return _error("chapter_not_found", "Chapter not found.", status.HTTP_404_NOT_FOUND)
        except MovieNotFound:
            return _error("movie_not_found", "Movie not found.", status.HTTP_404_NOT_FOUND)
        except (ChapterConflict, DuplicateKeyError) as exc:
            return _error("chapter_conflict", str(exc) if isinstance(exc, ChapterConflict) else "Chapter slug already exists.", status.HTTP_409_CONFLICT)
        return Response(AdminChapterSerializer(chapter).data)

    @extend_schema(operation_id="admin_movie_chapter_delete", summary="Delete a chapter and compact remaining chapter numbers", responses={200: None, 400: ErrorSerializer, 404: ErrorSerializer})
    def delete(self, request, movie_id, chapter_id):
        error = _bad_id(movie_id)
        if error:
            return error
        try:
            parse_chapter_id(chapter_id)
            result = delete_chapter(movie_id, chapter_id)
        except InvalidChapterId:
            return _error("invalid_chapter_id", "Chapter id is invalid.", status.HTTP_400_BAD_REQUEST)
        except InvalidMovieId:
            return _error("invalid_movie_id", "Movie id is invalid.", status.HTTP_400_BAD_REQUEST)
        except ChapterNotFound:
            return _error("chapter_not_found", "Chapter not found.", status.HTTP_404_NOT_FOUND)
        except MovieNotFound:
            return _error("movie_not_found", "Movie not found.", status.HTTP_404_NOT_FOUND)
        return Response(result)


class AdminChapterReorderView(APIView):
    permission_classes = [IsAuthenticatedUser, IsAdministrator]

    @extend_schema(operation_id="admin_movie_chapters_reorder", summary="Atomically reorder every chapter for a movie", request=ChapterReorderSerializer, responses={200: AdminChapterSerializer(many=True), 400: ErrorSerializer, 404: ErrorSerializer, 409: ErrorSerializer})
    def post(self, request, movie_id):
        error = _bad_id(movie_id)
        if error:
            return error
        serializer = ChapterReorderSerializer(data=request.data)
        if not serializer.is_valid():
            return _error("validation_error", "Reorder data is invalid.", status.HTTP_400_BAD_REQUEST, serializer.errors)
        try:
            chapters = reorder_chapters(movie_id, serializer.validated_data["chapter_ids"])
        except InvalidChapterId:
            return _error("invalid_chapter_id", "A chapter id is invalid.", status.HTTP_400_BAD_REQUEST)
        except MovieNotFound:
            return _error("movie_not_found", "Movie not found.", status.HTTP_404_NOT_FOUND)
        except ChapterConflict as exc:
            return _error("invalid_chapter_order", str(exc), status.HTTP_400_BAD_REQUEST)
        except DuplicateKeyError:
            return _error("chapter_conflict", "Chapter order conflicted with another update; reload and try again.", status.HTTP_409_CONFLICT)
        return Response(AdminChapterSerializer(chapters, many=True).data)
