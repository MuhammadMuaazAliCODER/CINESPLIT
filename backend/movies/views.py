from drf_spectacular.utils import extend_schema
from pymongo.errors import DuplicateKeyError
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.api_serializers import ErrorSerializer
from accounts.permissions import IsAdministrator, IsAuthenticatedUser

from .serializers import (
    AdminMovieListResponseSerializer, AdminMovieSerializer, MovieDeleteSerializer, MovieGenresResponseSerializer,
    MovieListQuerySerializer, MovieListResponseSerializer, MovieSerializer, MovieWriteSerializer,
)
from .services import (
    InvalidMovieId, MovieConflict, MovieHasChapters, MovieNotFound, create_movie, delete_movie,
    get_movie_by_id, get_movie_by_slug, list_movies, list_public_genres, parse_movie_id, update_movie,
)


def _error(code, detail, status_code, errors=None):
    data = {"code": code, "detail": detail}
    if errors is not None:
        data["errors"] = errors
    return Response(data, status=status_code)


def _query_data(request):
    serializer = MovieListQuerySerializer(data=request.query_params)
    if not serializer.is_valid():
        return None, _error("validation_error", "Movie query parameters are invalid.", status.HTTP_400_BAD_REQUEST, serializer.errors)
    return serializer.validated_data, None


class MovieListView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(operation_id="movies_list", summary="Browse published movies", parameters=[MovieListQuerySerializer], responses={200: MovieListResponseSerializer})
    def get(self, request):
        filters, error = _query_data(request)
        if error:
            return error
        return Response(MovieListResponseSerializer(list_movies(filters, published_only=True)).data)


class FeaturedMovieListView(MovieListView):
    @extend_schema(operation_id="movies_featured", summary="Browse featured published movies", parameters=[MovieListQuerySerializer], responses={200: MovieListResponseSerializer})
    def get(self, request):
        filters, error = _query_data(request)
        if error:
            return error
        return Response(MovieListResponseSerializer(list_movies(filters, published_only=True, featured_only=True)).data)


class PublicMovieDetailView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(operation_id="movies_detail", summary="Get a published movie by slug", responses={200: MovieSerializer, 404: ErrorSerializer})
    def get(self, request, slug):
        movie = get_movie_by_slug(slug, published_only=True)
        if not movie:
            return _error("movie_not_found", "Movie not found.", status.HTTP_404_NOT_FOUND)
        return Response(MovieSerializer(movie).data)


class PublicGenreListView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(operation_id="movies_genres", summary="List genres used by published movies", responses={200: MovieGenresResponseSerializer})
    def get(self, request):
        return Response({"genres": list_public_genres()})


class AdminMovieCollectionView(APIView):
    permission_classes = [IsAuthenticatedUser, IsAdministrator]

    @extend_schema(operation_id="admin_movies_list", summary="List movies for administrators", parameters=[MovieListQuerySerializer], responses={200: AdminMovieListResponseSerializer})
    def get(self, request):
        filters, error = _query_data(request)
        if error:
            return error
        result = list_movies(filters)
        return Response(AdminMovieListResponseSerializer(result).data)

    @extend_schema(operation_id="admin_movies_create", summary="Create a movie", request=MovieWriteSerializer, responses={201: AdminMovieSerializer, 400: ErrorSerializer, 409: ErrorSerializer})
    def post(self, request):
        serializer = MovieWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return _error("validation_error", "Movie data is invalid.", status.HTTP_400_BAD_REQUEST, serializer.errors)
        try:
            movie = create_movie(serializer.validated_data, request.user.id)
        except (MovieConflict, DuplicateKeyError):
            return _error("movie_conflict", "A movie with that slug already exists.", status.HTTP_409_CONFLICT)
        return Response(AdminMovieSerializer(movie).data, status=status.HTTP_201_CREATED)


class AdminMovieDetailView(APIView):
    permission_classes = [IsAuthenticatedUser, IsAdministrator]

    @extend_schema(operation_id="admin_movies_detail", summary="Get a movie for administrators", responses={200: AdminMovieSerializer, 404: ErrorSerializer})
    def get(self, request, movie_id):
        try:
            movie = get_movie_by_id(movie_id)
        except InvalidMovieId:
            return _error("invalid_movie_id", "Movie id is invalid.", status.HTTP_400_BAD_REQUEST)
        if not movie:
            return _error("movie_not_found", "Movie not found.", status.HTTP_404_NOT_FOUND)
        return Response(AdminMovieSerializer(movie).data)

    @extend_schema(operation_id="admin_movies_replace", summary="Replace a movie", request=MovieWriteSerializer, responses={200: AdminMovieSerializer, 400: ErrorSerializer, 404: ErrorSerializer, 409: ErrorSerializer})
    def put(self, request, movie_id):
        return self._update(request, movie_id, partial=False)

    @extend_schema(operation_id="admin_movies_update", summary="Update movie fields", request=MovieWriteSerializer, responses={200: AdminMovieSerializer, 400: ErrorSerializer, 404: ErrorSerializer, 409: ErrorSerializer})
    def patch(self, request, movie_id):
        return self._update(request, movie_id, partial=True)

    def _update(self, request, movie_id, partial):
        try:
            parse_movie_id(movie_id)
        except InvalidMovieId:
            return _error("invalid_movie_id", "Movie id is invalid.", status.HTTP_400_BAD_REQUEST)
        serializer = MovieWriteSerializer(data=request.data, partial=partial)
        if not serializer.is_valid():
            return _error("validation_error", "Movie data is invalid.", status.HTTP_400_BAD_REQUEST, serializer.errors)
        try:
            movie = update_movie(movie_id, serializer.validated_data)
        except MovieNotFound:
            return _error("movie_not_found", "Movie not found.", status.HTTP_404_NOT_FOUND)
        except (MovieConflict, DuplicateKeyError):
            return _error("movie_conflict", "A movie with that slug already exists.", status.HTTP_409_CONFLICT)
        except InvalidMovieId:
            return _error("invalid_movie_id", "Movie id is invalid.", status.HTTP_400_BAD_REQUEST)
        return Response(AdminMovieSerializer(movie).data)

    @extend_schema(operation_id="admin_movies_delete", summary="Delete a movie by confirming its slug", request=MovieDeleteSerializer, responses={204: None, 400: ErrorSerializer, 404: ErrorSerializer})
    def delete(self, request, movie_id):
        try:
            parse_movie_id(movie_id)
        except InvalidMovieId:
            return _error("invalid_movie_id", "Movie id is invalid.", status.HTTP_400_BAD_REQUEST)
        serializer = MovieDeleteSerializer(data=request.data)
        if not serializer.is_valid():
            return _error("validation_error", "Confirm deletion by providing the movie slug.", status.HTTP_400_BAD_REQUEST, serializer.errors)
        try:
            deleted = delete_movie(movie_id, serializer.validated_data["confirmation"])
        except MovieNotFound:
            return _error("movie_not_found", "Movie not found.", status.HTTP_404_NOT_FOUND)
        except MovieHasChapters:
            return _error("movie_has_chapters", "Delete the movie's chapters before deleting the movie.", status.HTTP_409_CONFLICT)
        except InvalidMovieId:
            return _error("invalid_movie_id", "Movie id is invalid.", status.HTTP_400_BAD_REQUEST)
        if not deleted:
            return _error("deletion_not_confirmed", "The confirmation must match the movie slug.", status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)
