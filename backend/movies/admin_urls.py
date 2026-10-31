from django.urls import path

from .views import AdminMovieCollectionView, AdminMovieDetailView
from .chapter_views import AdminChapterCollectionView, AdminChapterDetailView, AdminChapterReorderView

urlpatterns = [
    path("", AdminMovieCollectionView.as_view(), name="admin-movies-list"),
    path("<str:movie_id>/chapters/", AdminChapterCollectionView.as_view(), name="admin-movie-chapters"),
    path("<str:movie_id>/chapters/reorder/", AdminChapterReorderView.as_view(), name="admin-movie-chapters-reorder"),
    path("<str:movie_id>/chapters/<str:chapter_id>/", AdminChapterDetailView.as_view(), name="admin-movie-chapter-detail"),
    path("<str:movie_id>/", AdminMovieDetailView.as_view(), name="admin-movies-detail"),
]
