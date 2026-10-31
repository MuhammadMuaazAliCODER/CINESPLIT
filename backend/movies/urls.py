from django.urls import path

from .views import (
    AdminMovieCollectionView, AdminMovieDetailView, FeaturedMovieListView,
    MovieListView, PublicGenreListView, PublicMovieDetailView,
)
from .chapter_views import PublicChapterDetailView, PublicChapterListView

urlpatterns = [
    path("", MovieListView.as_view(), name="movies-list"),
    path("featured/", FeaturedMovieListView.as_view(), name="movies-featured"),
    path("genres/", PublicGenreListView.as_view(), name="movies-genres"),
    path("<slug:movie_slug>/chapters/", PublicChapterListView.as_view(), name="public-movie-chapters"),
    path("<slug:movie_slug>/chapters/<slug:chapter_slug>/", PublicChapterDetailView.as_view(), name="public-movie-chapter-detail"),
    path("<slug:slug>/", PublicMovieDetailView.as_view(), name="movies-detail"),
]
